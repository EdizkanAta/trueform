"""TargetEngine — the core IP.

Given a user's vitals, conditions, activity and timeline, compute:
  * BMI, estimated body-fat % (Deurenberg), lean-mass estimate
  * safe-rate caps (rule 4) + condition modifiers + age/sex modifiers
  * three targets (conservative / expected / stretch) for the chosen timeline
  * plain-language reasoning
  * daily kcal + macros for the plan (respecting kcal floors)

Pure functions, no I/O — unit tested in tests/test_target_engine.py.
Units: internal math is metric (kg, cm). Weights returned in both kg and lb.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional

KG_PER_LB = 0.45359237
KCAL_PER_KG_FAT = 7700.0  # ~3500 kcal per lb

# --- Rule 4 floors / caps ---------------------------------------------------
KCAL_FLOOR = {"male": 1500, "female": 1200}
MAX_LOSS_FRACTION_PER_WEEK = 0.01   # 1% bodyweight / week
MAX_GAIN_FRACTION_PER_WEEK = 0.005  # 0.5% bodyweight / week

ACTIVITY_MULTIPLIER = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# Conditions that slow expected fat loss (multiplier on expected rate).
CONDITION_RATE_MODIFIER = {
    "hypothyroid": 0.70,
    "prediabetes": 0.90,
    "type2Diabetes": 0.85,
    "PCOS": 0.85,
    "NAFLD": 0.95,
    "hyperthyroid": 1.05,
}

Direction = Literal["lose", "gain", "recomp"]
Sex = Literal["male", "female"]


@dataclass
class EngineInput:
    sex: Sex
    age: int
    height_cm: float
    weight_kg: float
    body_frame: Literal["small", "medium", "large"]
    activity_level: str
    conditions: List[str]
    direction: Direction
    timeline_weeks: int
    desired_weight_kg: Optional[float] = None


@dataclass
class Target:
    label: str  # conservative | expected | stretch
    weight_kg: float
    weight_lb: float
    body_fat_pct: float
    what_it_takes: str


@dataclass
class EngineResult:
    bmi: float
    body_fat_pct: float
    lean_mass_kg: float
    tdee: int
    daily_kcal: int
    macros: Dict[str, int]
    weekly_rate_kg: float
    targets: List[Target]
    reasoning: str
    exceeds_stretch: bool
    realistic_timeline_weeks: Optional[int]
    condition_notes: List[str] = field(default_factory=list)


def _bmr_mifflin(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + (5 if sex == "male" else -161)


def estimate_body_fat(bmi: float, age: int, sex: str) -> float:
    """Deurenberg equation. Returns a % clamped to a sane range."""
    sex_factor = 1 if sex == "male" else 0
    bf = 1.20 * bmi + 0.23 * age - 10.8 * sex_factor - 5.4
    return round(max(3.0, min(60.0, bf)), 1)


def _condition_rate_factor(conditions: List[str]) -> float:
    factor = 1.0
    for c in conditions:
        factor *= CONDITION_RATE_MODIFIER.get(c, 1.0)
    return factor


def _muscle_gain_ceiling_kg_per_week(sex: str, age: int) -> float:
    """Novice male 20s ~1-2 lb muscle/month (use ~1.5 lb/mo), female ~half,
    both decline with age."""
    base_lb_per_month = 1.5 if sex == "male" else 0.75
    if age >= 60:
        decline = 0.4
    elif age >= 50:
        decline = 0.55
    elif age >= 40:
        decline = 0.7
    elif age >= 30:
        decline = 0.85
    else:
        decline = 1.0
    lb_per_month = base_lb_per_month * decline
    return (lb_per_month * KG_PER_LB) / 4.345  # weeks per month


def _condition_notes(conditions: List[str]) -> List[str]:
    notes = []
    if "NAFLD" in conditions:
        notes.append("NAFLD: prioritize fat loss and keep added fructose low.")
    if "type2Diabetes" in conditions:
        notes.append("Type 2 diabetes: even carb distribution and a short walk after meals.")
    if "prediabetes" in conditions:
        notes.append("Prediabetes: steady carbs and post-meal movement help blood sugar.")
    if "hypertension" in conditions:
        notes.append("Hypertension: sodium cap and no breath-holding (Valsalva) on lifts.")
    if "hypothyroid" in conditions:
        notes.append("Hypothyroidism: expected loss is slower — this is normal, not failure.")
    if "PCOS" in conditions:
        notes.append("PCOS: strength work and protein support insulin sensitivity.")
    if "highCholesterol" in conditions:
        notes.append("High cholesterol: emphasize soluble fibre and unsaturated fats.")
    return notes


def compute(inp: EngineInput) -> EngineResult:
    height_m = inp.height_cm / 100.0
    bmi = round(inp.weight_kg / (height_m * height_m), 1)
    bf = estimate_body_fat(bmi, inp.age, inp.sex)
    lean_mass = round(inp.weight_kg * (1 - bf / 100.0), 1)

    tdee = _bmr_mifflin(inp.sex, inp.weight_kg, inp.height_cm, inp.age) * \
        ACTIVITY_MULTIPLIER.get(inp.activity_level, 1.375)
    tdee = round(tdee)

    weeks = max(1, inp.timeline_weeks)

    if inp.direction == "gain":
        max_rate = inp.weight_kg * MAX_GAIN_FRACTION_PER_WEEK
        muscle_cap = _muscle_gain_ceiling_kg_per_week(inp.sex, inp.age)
        stretch_rate = min(max_rate, muscle_cap)
        expected_rate = stretch_rate * 0.7
        conservative_rate = expected_rate * 0.8
        direction_sign = 1
    elif inp.direction == "recomp":
        # Minimal weight change; focus on body composition.
        stretch_rate = inp.weight_kg * 0.0015
        expected_rate = stretch_rate * 0.6
        conservative_rate = expected_rate * 0.8
        direction_sign = -1
    else:  # lose
        max_rate = inp.weight_kg * MAX_LOSS_FRACTION_PER_WEEK
        cond_factor = _condition_rate_factor(inp.conditions)
        stretch_rate = max_rate * cond_factor
        expected_rate = stretch_rate * 0.75
        conservative_rate = expected_rate * 0.8
        direction_sign = -1

    def make_target(label: str, rate_kg: float) -> Target:
        delta = direction_sign * rate_kg * weeks
        new_weight = round(inp.weight_kg + delta, 1)
        new_bmi = new_weight / (height_m * height_m)
        new_bf = estimate_body_fat(round(new_bmi, 1), inp.age, inp.sex)
        if inp.direction == "gain":
            new_bf = round(max(3.0, bf - abs(delta) * 0.3), 1)
        rate_lb = round(rate_kg / KG_PER_LB, 2)
        verb = "gain" if inp.direction == "gain" else "lose"
        wit = (
            f"~{rate_lb} lb/week {verb} · {label} path over {weeks} weeks"
            if inp.direction != "recomp"
            else f"Hold weight, recomposition over {weeks} weeks"
        )
        return Target(
            label=label,
            weight_kg=new_weight,
            weight_lb=round(new_weight / KG_PER_LB, 1),
            body_fat_pct=new_bf,
            what_it_takes=wit,
        )

    targets = [
        make_target("conservative", conservative_rate),
        make_target("expected", expected_rate),
        make_target("stretch", stretch_rate),
    ]

    # Daily kcal driven by the EXPECTED rate, floored by rule 4.
    daily_delta = (expected_rate * KCAL_PER_KG_FAT) / 7.0
    if inp.direction == "gain":
        daily_kcal = round(tdee + max(150, daily_delta))
    elif inp.direction == "recomp":
        daily_kcal = tdee
    else:
        daily_kcal = round(tdee - daily_delta)
    floor = KCAL_FLOOR[inp.sex]
    kcal_floored = max(floor, daily_kcal)
    hit_floor = kcal_floored != daily_kcal
    daily_kcal = kcal_floored

    # Macros: protein 1.8 g/kg, fat 0.9 g/kg, carbs fill remainder.
    protein_g = round(1.8 * inp.weight_kg)
    fat_g = round(0.9 * inp.weight_kg)
    carbs_g = max(50, round((daily_kcal - (protein_g * 4 + fat_g * 9)) / 4))
    if "type2Diabetes" in inp.conditions or "prediabetes" in inp.conditions:
        # Shift a little from carbs toward protein/fat for glycemic control.
        carbs_g = max(50, round(carbs_g * 0.85))
    macros = {"protein_g": protein_g, "fat_g": fat_g, "carbs_g": carbs_g}

    # Does the user's desire exceed the stretch ceiling?
    exceeds = False
    realistic_weeks: Optional[int] = None
    if inp.desired_weight_kg is not None and inp.direction != "recomp":
        desired_delta = abs(inp.desired_weight_kg - inp.weight_kg)
        stretch_delta = abs(targets[2].weight_kg - inp.weight_kg)
        if desired_delta > stretch_delta + 0.05:
            exceeds = True
            if stretch_rate > 0:
                realistic_weeks = int(round(desired_delta / stretch_rate))

    cond_notes = _condition_notes(inp.conditions)
    reasoning = _build_reasoning(inp, expected_rate, cond_notes, hit_floor, floor)

    return EngineResult(
        bmi=bmi,
        body_fat_pct=bf,
        lean_mass_kg=lean_mass,
        tdee=tdee,
        daily_kcal=daily_kcal,
        macros=macros,
        weekly_rate_kg=round(expected_rate, 3),
        targets=targets,
        reasoning=reasoning,
        exceeds_stretch=exceeds,
        realistic_timeline_weeks=realistic_weeks,
        condition_notes=cond_notes,
    )


def _build_reasoning(inp, expected_rate, cond_notes, hit_floor, floor) -> str:
    rate_lb = round(expected_rate / KG_PER_LB, 2)
    verb = "gain" if inp.direction == "gain" else ("recomposition" if inp.direction == "recomp" else "loss")
    parts = [
        f"You're {inp.age} and {inp.sex}."
    ]
    slowers = [c for c in inp.conditions if c in CONDITION_RATE_MODIFIER and CONDITION_RATE_MODIFIER[c] < 1]
    if slowers and inp.direction == "lose":
        pretty = {
            "hypothyroid": "hypothyroidism", "type2Diabetes": "type 2 diabetes",
            "prediabetes": "prediabetes", "PCOS": "PCOS", "NAFLD": "NAFLD",
        }
        names = ", ".join(pretty.get(c, c) for c in slowers)
        parts.append(
            f"Because you have {names}, expected {verb} is about "
            f"{rate_lb} lb/week, not the 2 lb/week many apps promise."
        )
    else:
        parts.append(f"Expected {verb} is about {rate_lb} lb/week for your profile.")
    if inp.direction == "gain":
        parts.append(
            "Muscle-gain ceilings are set by your age and sex — real muscle is "
            "built slowly, so the stretch target is near the biological maximum."
        )
    if hit_floor:
        parts.append(
            f"Your plan is held at the {floor} kcal/day floor for safety rather "
            "than going lower."
        )
    parts.extend(cond_notes)
    return " ".join(parts)


def render_prompt_stats(result: EngineResult, chosen_label: str) -> Dict:
    """Structured stats handed to the text model to write the image prompt."""
    chosen = next(t for t in result.targets if t.label == chosen_label)
    return {
        "current_body_fat_pct": result.body_fat_pct,
        "target_body_fat_pct": chosen.body_fat_pct,
        "current_weight_kg": None,
        "target_weight_kg": chosen.weight_kg,
        "label": chosen_label,
    }
