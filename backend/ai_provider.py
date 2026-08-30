"""Provider-agnostic AI layer.

A single AIProvider interface exposes three capabilities:
  * generate_plan(...)      -> structured JSON plan (validated by caller)
  * coach_chat(...)         -> assistant reply (uses streaming internally)
  * render_future_self(...) -> image-to-image edited photo (base64)

Concrete providers are selected purely from environment variables, so the app
can swap Anthropic/Gemini/OpenAI by editing backend/.env only — no app code
changes. All model calls happen here, on the backend, never on the client.
Token/image usage is logged per request via the `cost_logger` callback.
"""
from __future__ import annotations

import base64
import json
import os
import uuid
from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Dict, List, Optional

from emergentintegrations.llm.chat import (
    LlmChat,
    UserMessage,
    ImageContent,
    TextDelta,
    StreamDone,
)

EMERGENT_LLM_KEY = os.environ["EMERGENT_LLM_KEY"]

CostLogger = Callable[[dict], Awaitable[None]]


def _clean_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```", 2)[1] if "```" in t else t
        t = t.replace("json", "", 1) if t.lstrip().startswith("json") else t
    # Extract the outermost JSON object.
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1:
        t = t[start : end + 1]
    return t.strip()


class AIProvider(ABC):
    @abstractmethod
    async def generate_plan(self, system: str, user_prompt: str, session_id: str) -> dict: ...

    @abstractmethod
    async def coach_chat(self, system: str, history: List[Dict], user_text: str, session_id: str) -> str: ...

    @abstractmethod
    async def render_future_self(self, prompt: str, base_image_b64: str, session_id: str) -> str: ...


class EmergentAIProvider(AIProvider):
    """Uses Emergent Universal Key. Text = Anthropic Claude, Image = Gemini Nano Banana
    (configurable via AI_TEXT_* / AI_IMAGE_* env vars)."""

    def __init__(self, cost_logger: Optional[CostLogger] = None):
        self.text_provider = os.environ["AI_TEXT_PROVIDER"]
        self.text_model = os.environ["AI_TEXT_MODEL"]
        self.image_provider = os.environ["AI_IMAGE_PROVIDER"]
        self.image_model = os.environ["AI_IMAGE_MODEL"]
        self.cost_logger = cost_logger

    def _text_chat(self, system: str, session_id: str) -> LlmChat:
        return LlmChat(
            api_key=EMERGENT_LLM_KEY, session_id=session_id, system_message=system
        ).with_model(self.text_provider, self.text_model)

    async def _log(self, kind: str, session_id: str, extra: dict) -> None:
        if self.cost_logger:
            await self.cost_logger(
                {"kind": kind, "session_id": session_id,
                 "provider": extra.get("provider"), "model": extra.get("model"), **extra}
            )

    async def generate_plan(self, system: str, user_prompt: str, session_id: str) -> dict:
        chat = self._text_chat(system, session_id)
        full = ""
        async for ev in chat.stream_message(UserMessage(text=user_prompt)):
            if isinstance(ev, TextDelta):
                full += ev.content
            elif isinstance(ev, StreamDone):
                break
        await self._log("generate_plan", session_id,
                        {"provider": self.text_provider, "model": self.text_model,
                         "chars_out": len(full)})
        return json.loads(_clean_json(full))

    async def coach_chat(self, system: str, history: List[Dict], user_text: str, session_id: str) -> str:
        chat = self._text_chat(system, session_id)
        # Prime prior turns into the session context.
        context = ""
        for m in history[-14:]:
            role = "Coach" if m["role"] == "assistant" else "User"
            context += f"{role}: {m['content']}\n"
        prompt = (context + f"User: {user_text}\nCoach:") if context else user_text
        full = ""
        async for ev in chat.stream_message(UserMessage(text=prompt)):
            if isinstance(ev, TextDelta):
                full += ev.content
            elif isinstance(ev, StreamDone):
                break
        await self._log("coach_chat", session_id,
                        {"provider": self.text_provider, "model": self.text_model,
                         "chars_out": len(full)})
        return full.strip()

    async def render_future_self(self, prompt: str, base_image_b64: str, session_id: str) -> str:
        # Image models occasionally return a text-only refusal or an empty
        # response; retry a few times before surfacing an error to the caller.
        last_text = ""
        for attempt in range(3):
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY, session_id=f"{session_id}-{attempt}",
                system_message="You are a photorealistic image editor. Always return an edited image.",
            ).with_model(self.image_provider, self.image_model).with_params(modalities=["image", "text"])
            msg = UserMessage(text=prompt, file_contents=[ImageContent(base_image_b64)])
            text, images = await chat.send_message_multimodal_response(msg)
            await self._log("render_future_self", session_id,
                            {"provider": self.image_provider, "model": self.image_model,
                             "images": len(images) if images else 0, "attempt": attempt})
            if images:
                return images[0]["data"]  # base64 string
            last_text = (text or "")[:120]
        raise RuntimeError(f"Image model returned no image after retries. {last_text}")


def get_provider(cost_logger: Optional[CostLogger] = None) -> AIProvider:
    return EmergentAIProvider(cost_logger=cost_logger)


# --- Prompt builders --------------------------------------------------------

def build_render_prompt(stats: dict, label: str) -> str:
    """Image-to-image prompt: change ONLY body composition, preserve identity."""
    if label == "conservative":
        change = "a modest, realistic reduction in body fat"
    elif label == "stretch":
        change = "a noticeable but still realistic improvement in body composition (leaner, more muscle tone)"
    else:
        change = "a realistic, healthy improvement in body composition"
    return (
        f"Edit this full-body photo to show the SAME person after {change}, "
        f"targeting about {stats.get('target_body_fat_pct')}% body fat. "
        "STRICT RULES: keep the exact same face, identity, skin tone, hair, pose, "
        "camera angle, lighting, background, and clothing style and fit. Change ONLY "
        "the body composition to look natural and attainable. Photorealistic, "
        "non-sexualized, respectful, true-to-life. Do not idealize or exaggerate."
    )
