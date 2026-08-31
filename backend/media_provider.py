"""MediaProvider interface for exercise demo media.

Exercises are stored in MongoDB; each carries its own media attribution so
you can swap in your own filmed videos later by changing config only. The
default provider enriches exercises from the wger open exercise database
(wger.de, content under CC-BY-SA 4.0) with best-effort live lookup at seed
time. If lookup fails, media is left null and the app shows a neutral
placeholder — attribution/license are always recorded.
"""
from __future__ import annotations

import logging
import os
import re
from abc import ABC, abstractmethod
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote

import requests

logger = logging.getLogger("trueform.media_provider")


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


def _normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace for fuzzy comparison."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# Equipment words that matter for picking the *right* variant of an exercise:
# plain fuzzy-string similarity alone favors a short wrong-equipment name (e.g.
# "dumbbell row") over a longer correct-equipment one ("barbell bent over row"),
# because SequenceMatcher's ratio is length-sensitive. Rewarding/penalizing an
# equipment-word match/mismatch corrects for that.
_EQUIPMENT_KEYWORDS = ["barbell", "dumbbell", "kettlebell", "band", "cable",
                       "machine", "smith", "bodyweight"]


def _equipment_keyword(normalized_text: str) -> Optional[str]:
    for kw in _EQUIPMENT_KEYWORDS:
        if kw in normalized_text:
            return kw
    return None


# Our catalog's `muscle_groups` vocabulary (seed_data.py) mapped onto
# ExerciseDB's `target` vocabulary, used only to score/disambiguate candidates
# returned by a name search — never to filter it out entirely.
_MUSCLE_TO_TARGET = {
    "chest": "pectorals",
    "triceps": "triceps",
    "shoulders": "delts",
    "back": "lats",
    "biceps": "biceps",
    "quads": "quads",
    "glutes": "glutes",
    "hamstrings": "hamstrings",
    "core": "abs",
    "cardio": "cardiovascular system",
}

# Per-exercise search hints for our exact catalog (backend/seed_data.py::EXERCISES).
# ExerciseDB's own naming doesn't always line up 1:1 with ours (e.g. "military
# press" vs. our "Overhead Barbell Press"), so each of our exercise names gets a
# search query + expected target(s) to match against. This table is duplicated
# from seed_data.py's muscle_groups rather than imported from it: seed_data.py
# already imports get_media_provider() from this module, so importing seed_data
# back would create a circular import. The MediaProvider interface only passes
# `exercise_name`, so this table is how a name-only lookup still gets muscle-group
# context to disambiguate ExerciseDB candidates.
_SEARCH_HINTS: Dict[str, dict] = {
    "Barbell Bench Press": {"query": "barbell bench press", "targets": ["pectorals"]},
    "Dumbbell Bench Press": {"query": "dumbbell bench press", "targets": ["pectorals"]},
    "Push-Up": {"query": "push up", "targets": ["pectorals"]},
    "Overhead Barbell Press": {"query": "barbell shoulder press", "targets": ["delts"]},
    "Dumbbell Shoulder Press": {"query": "dumbbell shoulder press", "targets": ["delts"]},
    "Pike Push-Up": {"query": "pike push up", "targets": ["delts"]},
    "Barbell Row": {"query": "barbell row", "targets": ["lats", "back"]},
    "One-Arm Dumbbell Row": {"query": "dumbbell row", "targets": ["lats", "back"]},
    "Band / Table Inverted Row": {"query": "inverted row", "targets": ["lats", "back"]},
    "Lat Pulldown": {"query": "lat pulldown", "targets": ["lats"]},
    "Pull-Up": {"query": "pull up", "targets": ["lats"]},
    "Band Lat Pulldown": {"query": "band lat pulldown", "targets": ["lats"]},
    "Barbell Back Squat": {"query": "barbell squat", "targets": ["quads"]},
    "Goblet Squat": {"query": "goblet squat", "targets": ["quads"]},
    "Bodyweight Squat": {"query": "squat", "targets": ["quads"]},
    "Romanian Deadlift": {"query": "romanian deadlift", "targets": ["hamstrings"]},
    "Dumbbell Romanian Deadlift": {"query": "dumbbell romanian deadlift", "targets": ["hamstrings"]},
    "Glute Bridge": {"query": "glute bridge", "targets": ["glutes"]},
    "Incline Treadmill Walk": {"query": "treadmill walk", "targets": ["cardiovascular system"]},
    "Brisk Outdoor Walk": {"query": "walk", "targets": ["cardiovascular system"]},
    "Plank": {"query": "plank", "targets": ["abs"]},
    "Dead Bug": {"query": "dead bug", "targets": ["abs"]},
}


class ExerciseDBMediaProvider(MediaProvider):
    """ExerciseDB (RapidAPI) — maps our catalog to ExerciseDB exercise IDs and
    uses their demo GIF as both the poster image and the "video".

    API docs: https://rapidapi.com/justin-WFnsXH_t6/api/exercisedb (host
    exercisedb.p.rapidapi.com). Requires RAPIDAPI_KEY (see .env.example).

    Matching strategy, since the MediaProvider interface only passes an
    exercise name (no muscle_groups):
      1. Look up `exercise_name` in _SEARCH_HINTS for a search query + expected
         target muscle(s) (falls back to the raw name if the exercise isn't in
         our known catalog).
      2. Query GET /exercises/name/{query}; if that returns nothing, fall back
         to GET /exercises/target/{target} for each expected target.
      3. Score every candidate by fuzzy name similarity (difflib) against the
         search query, with a bonus when its `target` matches one of our
         expected targets, and a bonus/penalty when an equipment word
         (barbell/dumbbell/band/...) in the query matches/mismatches the
         candidate's name — otherwise a short wrong-equipment name can outscore
         a longer correct-equipment one on string similarity alone.
      4. Accept the best candidate only if its score clears MATCH_THRESHOLD.

    Never raises: any network error, bad response, or lookup miss returns the
    same "unmapped" shape the rest of the app already treats as "no media yet"
    (demo_url=None -> frontend shows the "Demo coming soon" placeholder).
    """
    name = "exercisedb"
    license = "ExerciseDB API (RapidAPI) — per your RapidAPI subscription terms"
    HOST = "exercisedb.p.rapidapi.com"
    BASE = f"https://{HOST}"
    MATCH_THRESHOLD = 0.55
    TARGET_MATCH_BONUS = 0.15
    EQUIPMENT_MATCH_BONUS = 0.2
    EQUIPMENT_MISMATCH_PENALTY = 0.2
    TIMEOUT = 6

    def __init__(self) -> None:
        self._api_key = os.environ.get("RAPIDAPI_KEY", "")

    def _unmapped(self, reason: str) -> dict:
        return {"demo_url": None, "source": self.name, "license": self.license,
                "attribution": reason}

    def _headers(self) -> dict:
        return {"X-RapidAPI-Key": self._api_key, "X-RapidAPI-Host": self.HOST}

    def _get(self, path: str) -> List[dict]:
        try:
            r = requests.get(f"{self.BASE}{path}", headers=self._headers(), timeout=self.TIMEOUT)
            if not r.ok:
                return []
            data = r.json()
            return data if isinstance(data, list) else []
        except (requests.RequestException, ValueError):
            return []

    def _candidates(self, hint: dict) -> List[dict]:
        candidates = self._get(f"/exercises/name/{quote(hint['query'])}")
        if candidates:
            return candidates
        merged: List[dict] = []
        for target in hint.get("targets", []):
            merged.extend(self._get(f"/exercises/target/{quote(target)}"))
        return merged

    def _best_match(self, exercise_name: str, hint: dict) -> Tuple[Optional[dict], float]:
        targets = set(hint.get("targets", []))
        # Compare against the search query (our canonical rendering of this
        # exercise for ExerciseDB), falling back to the raw name for exercises
        # outside our known catalog.
        norm_query = _normalize(hint.get("query") or exercise_name)
        query_equipment = _equipment_keyword(norm_query)
        best, best_score = None, 0.0
        for candidate in self._candidates(hint):
            cand_name = candidate.get("name") or ""
            norm_cand = _normalize(cand_name)
            score = SequenceMatcher(None, norm_query, norm_cand).ratio()
            if candidate.get("target") in targets:
                score += self.TARGET_MATCH_BONUS
            cand_equipment = _equipment_keyword(norm_cand)
            if query_equipment and cand_equipment:
                score += (self.EQUIPMENT_MATCH_BONUS if query_equipment == cand_equipment
                          else -self.EQUIPMENT_MISMATCH_PENALTY)
            if score > best_score:
                best, best_score = candidate, score
        return best, best_score

    def enrich(self, exercise_name: str) -> dict:
        if not self._api_key:
            return self._unmapped("RAPIDAPI_KEY not configured — showing placeholder.")

        hint = _SEARCH_HINTS.get(exercise_name, {"query": exercise_name, "targets": []})
        try:
            match, score = self._best_match(exercise_name, hint)
        except Exception:  # provider must never break exercise seeding
            logger.exception("ExerciseDB lookup failed for %r", exercise_name)
            return self._unmapped("ExerciseDB lookup failed — showing placeholder.")

        if not match or score < self.MATCH_THRESHOLD:
            return self._unmapped("No confident ExerciseDB match — showing placeholder.")

        gif_url = match.get("gifUrl")
        if not gif_url:
            return self._unmapped("ExerciseDB match had no demo GIF — showing placeholder.")

        return {
            "demo_url": gif_url,
            "source": "exercisedb.p.rapidapi.com",
            "license": self.license,
            "attribution": f"ExerciseDB id={match.get('id')} \"{match.get('name')}\" via RapidAPI",
            "exercisedb_id": match.get("id"),
            "exercisedb_target": match.get("target"),
            "match_score": round(score, 3),
        }


_PROVIDERS = {
    "wger": WgerMediaProvider,
    "exercisedb": ExerciseDBMediaProvider,
    "custom": NullMediaProvider,
}


def get_media_provider() -> MediaProvider:
    which = os.environ.get("MEDIA_PROVIDER", "wger")
    return _PROVIDERS.get(which, NullMediaProvider)()
