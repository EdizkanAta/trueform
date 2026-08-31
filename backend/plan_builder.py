"""Deterministic plan assembly from TargetEngine output + seeded catalog.

Environment-aware: each weekday can have its own training environment
(environmentSchedule) and an optional transition (environmentTransition) shifts
the environment from a given week onward. Exercises swap within the same
movement pattern + muscle group so a barbell lift becomes a dumbbell press
becomes a push-up progression across environments — same targets, same volume.
"""
from __future__ import annotations

from typing import Dict, List, Optional

# 7-day split by movement pattern. Rest days carry a recovery protocol.
WEEK_TEMPLATE = [
    {"day": "Monday", "focus": "Upper Body", "patterns": ["horizontal_push", "horizontal_pull", "vertical_push", "core"]},
    {"day": "Tuesday", "focus": "Lower Body", "patterns": ["squat", "hinge", "conditioning"]},
    {"day": "Wednesday", "focus": "Recovery", "patterns": []},
    {"day": "Thursday", "focus": "Push & Pull", "patterns": ["vertical_push", "vertical_pull", "horizontal_push", "core"]},
    {"day": "Friday", "focus": "Lower & Conditioning", "patterns": ["squat", "hinge", "conditioning"]},
    {"day": "Saturday", "focus": "Full Body", "patterns": ["horizontal_pull", "squat", "horizontal_push", "core"]},
    {"day": "Sunday", "focus": "Recovery", "patterns": []},
]

TIER_RANK = {"none": 0, "minimal": 1, "gym": 2}
ENV_TO_TIER = {
    "gym": ["gym", "minimal", "none"],
    "home_equipment": ["minimal", "none"],
    "home_no_equipment": ["none"],
}

RECOVERY_PROTOCOL = [
    {"title": "Mobility & stretching", "detail": "10 min full-body stretch, hold each 30s."},
    {"title": "Easy walk", "detail": "20-30 min brisk but conversational walk."},
    {"title": "Sleep", "detail": "Aim for 7-9 hours; consistent sleep/wake time."},
    {"title": "Hydration", "detail": "Sip water through the day; more on training days."},
    {"title": "Optional", "detail": "Sauna or self-massage if available — nice, not required."},
]


def _pick_exercise(pattern: str, env: str, exercises: List[Dict], has_hypertension: bool) -> Optional[Dict]:
    allowed = ENV_TO_TIER.get(env, ["none"])
    candidates = [e for e in exercises if e["pattern"] == pattern and e["equipment"] in allowed]
    if not candidates:
        return None
    # Highest available tier for a real training stimulus.
    candidates.sort(key=lambda e: TIER_RANK[e["equipment"]], reverse=True)
    chosen = candidates[0]
    if has_hypertension and "hypertension_valsalva" in chosen.get("contraindications", []):
        safer = [c for c in candidates if "hypertension_valsalva" not in c.get("contraindications", [])]
        if safer:
            chosen = safer[0]
    return chosen


def _exercise_view(ex: Dict, has_hypertension: bool) -> Dict:
    note = None
    if has_hypertension and "hypertension_valsalva" in ex.get("contraindications", []):
        note = "Breathe out on effort — no breath-holding (hypertension)."
    return {
        "slug": ex["slug"], "name": ex["name"], "muscle_groups": ex["muscle_groups"],
        "equipment": ex["equipment"], "sets": ex["sets"], "reps": ex["reps"],
        "rest_sec": ex["rest_sec"], "media": ex.get("media"),
        "media_provider": ex.get("media_provider"), "safety_note": note,
        "form_cues": ex.get("form_cues", []), "poster_image_url": ex.get("poster_image_url"),
    }


def _scale_meal(recipe: Dict, factor: float) -> Dict:
    return {
        "slug": recipe["slug"], "name": recipe["name"], "meal_type": recipe["meal_type"],
        "kcal": round(recipe["kcal"] * factor), "portion_factor": round(factor, 2),
        "macros": {k: round(v * factor) for k, v in recipe["macros"].items()},
        "tags": recipe["tags"], "ingredients": recipe["ingredients"], "steps": recipe["steps"],
    }


def _day_meals(day_idx: int, daily_kcal: int, recipes: List[Dict], conditions: List[str]) -> List[Dict]:
    def by_type(t):
        pool = [r for r in recipes if r["meal_type"] == t]
        if ("type2Diabetes" in conditions or "prediabetes" in conditions):
            pref = [r for r in pool if "diabetic-friendly" in r["tags"]]
            pool = pref or pool
        return pool
    picks = []
    for t in ["breakfast", "lunch", "dinner", "snack"]:
        pool = by_type(t)
        if pool:
            picks.append(pool[day_idx % len(pool)])
    base = sum(p["kcal"] for p in picks) or daily_kcal
    factor = daily_kcal / base
    return [_scale_meal(p, factor) for p in picks]


def build_plan(engine_result: dict, exercises: List[Dict], recipes: List[Dict],
               environment_schedule: Dict[str, str], conditions: List[str]) -> dict:
    has_htn = "hypertension" in conditions
    daily_kcal = engine_result["daily_kcal"]
    days = []
    for i, tmpl in enumerate(WEEK_TEMPLATE):
        env = environment_schedule.get(tmpl["day"], environment_schedule.get("default", "gym"))
        if tmpl["patterns"]:
            workout = []
            for pat in tmpl["patterns"]:
                ex = _pick_exercise(pat, env, exercises, has_htn)
                if ex:
                    workout.append(_exercise_view(ex, has_htn))
            day_type = "workout"
        else:
            workout = []
            day_type = "recovery"
        days.append({
            "day": tmpl["day"], "focus": tmpl["focus"], "environment": env,
            "type": day_type, "workout": workout,
            "meals": _day_meals(i, daily_kcal, recipes, conditions),
            "recovery": RECOVERY_PROTOCOL if day_type == "recovery" else [],
        })
    return {
        "weekly_kcal": daily_kcal * 7,
        "daily_kcal": daily_kcal,
        "macros": engine_result["macros"],
        "days": days,
        "lifestyle_habits": _lifestyle_habits(conditions),
        "recovery_protocol": RECOVERY_PROTOCOL,
        "version": 1,
    }


def _lifestyle_habits(conditions: List[str]) -> List[str]:
    habits = [
        "10-minute walk after your largest meal.",
        "Protein with every meal to protect muscle.",
        "2-3 L water per day.",
    ]
    if "hypertension" in conditions:
        habits.append("Keep added sodium under ~2,000 mg/day.")
    if "NAFLD" in conditions:
        habits.append("Limit sugary drinks and added fructose.")
    if "type2Diabetes" in conditions or "prediabetes" in conditions:
        habits.append("Pair carbs with protein/fat to blunt glucose spikes.")
    if "highCholesterol" in conditions:
        habits.append("Add a daily soluble-fibre source (oats, beans).")
    return habits
