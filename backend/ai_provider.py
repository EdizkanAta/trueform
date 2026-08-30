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
    """Image-to-image prompt: change body composition AND facial soft tissue
    PROPORTIONALLY to the computed body-fat change, while strictly preserving
    identity (bone structure, eyes, nose, ears, hairline, hair/beard, skin tone,
    expression). Magnitude scales with |current_bf - target_bf|: subtle at ~5%,
    obvious at ~10%+."""
    current_bf = stats.get("current_body_fat_pct")
    target_bf = stats.get("target_body_fat_pct")
    try:
        delta = float(current_bf) - float(target_bf)
    except (TypeError, ValueError):
        delta = 0.0
    leaner = delta >= 0
    mag = abs(delta)

    if mag < 3:
        body_change = "a subtle, realistic change in body composition"
        face_change = ("a very subtle change to facial soft tissue — cheeks marginally slimmer, "
                       "jawline only slightly more defined")
    elif mag < 6:
        body_change = "a modest, realistic reduction in body fat"
        face_change = ("a subtle change to facial soft tissue — slightly slimmer cheeks, a "
                       "marginally more defined jawline, and a small reduction in under-chin fullness")
    elif mag < 10:
        body_change = "a clear, realistic reduction in body fat"
        face_change = ("a noticeable change to facial soft tissue — visibly slimmer cheeks, a more "
                       "defined jawline, and reduced under-chin (submental) fullness")
    else:
        body_change = "a substantial but still realistic reduction in body fat"
        face_change = ("an obvious change to facial soft tissue — clearly slimmer cheeks, a sharply "
                       "defined jawline, and minimal under-chin (submental) fullness")

    if not leaner:
        # muscle gain / recomp: the face fills out slightly rather than slimming
        body_change = "a realistic increase in muscle with a slightly fuller, healthier face"
        face_change = ("a subtle change to facial soft tissue — a slightly fuller, firmer face "
                       "appropriate to gaining lean mass")

    return (
        f"Edit this full-body photo of the SAME person to show {body_change}, moving from about "
        f"{current_bf}% to about {target_bf}% body fat. The FACE must change proportionally with the "
        f"body-fat change: {face_change}. "
        "STRICT — DO NOT change any of the following: the underlying bone structure or skull/face "
        "shape and proportions, the eyes, nose, ears, hairline, hair style, beard or facial-hair "
        "style, skin tone, or facial expression. Also keep the exact same identity, pose, camera "
        "angle, lighting, background, and clothing style and fit. Change ONLY body composition and "
        "the soft-tissue fullness of the face that naturally follows it. Photorealistic, natural, "
        "attainable, non-sexualized, true-to-life — do not idealize, beautify, or exaggerate beyond "
        "the stated body-fat change."
    )
