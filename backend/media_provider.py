"""MediaProvider interface for exercise demo media.

Exercises are stored in MongoDB; each carries its own media attribution so
you can swap in your own filmed videos later by changing config only. The
default provider enriches exercises from the wger open exercise database
(wger.de, content under CC-BY-SA 4.0) with best-effort live lookup at seed
time. If lookup fails, media is left null and the app shows a neutral
placeholder — attribution/license are always recorded.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional

import requests


class MediaProvider(ABC):
    name: str
    license: str

    @abstractmethod
    def enrich(self, exercise_name: str) -> dict:
        """Return {demo_url, source, license, attribution}."""


class WgerMediaProvider(MediaProvider):
    name = "wger"
    license = "CC-BY-SA 4.0"
    BASE = "https://wger.de"

    def enrich(self, exercise_name: str) -> dict:
        demo_url: Optional[str] = None
        attribution = "wger.de community (CC-BY-SA 4.0)"
        try:
            r = requests.get(
                f"{self.BASE}/api/v2/exercise/search/",
                params={"term": exercise_name, "language": "english"},
                headers={"Accept": "application/json"},
                timeout=6,
            )
            if r.ok:
                suggestions = r.json().get("suggestions", [])
                if suggestions:
                    data = suggestions[0].get("data", {})
                    img = data.get("image")
                    if img:
                        demo_url = img if img.startswith("http") else f"{self.BASE}{img}"
        except requests.RequestException:
            pass
        return {
            "demo_url": demo_url,
            "source": "wger.de",
            "license": self.license,
            "attribution": attribution,
        }


class NullMediaProvider(MediaProvider):
    """Placeholder provider — for swapping in your own filmed videos later."""
    name = "custom"
    license = "proprietary"

    def enrich(self, exercise_name: str) -> dict:
        return {"demo_url": None, "source": "custom", "license": self.license,
                "attribution": "Your own media library"}


def get_media_provider() -> MediaProvider:
    which = os.environ.get("MEDIA_PROVIDER", "wger")
    if which == "wger":
        return WgerMediaProvider()
    return NullMediaProvider()
