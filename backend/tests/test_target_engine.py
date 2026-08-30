"""Unit tests for TargetEngine — rule 4 caps, kcal floors, condition modifiers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import target_engine as te  # noqa: E402


def _base(**kw):
    d = dict(sex="male", age=30, height_cm=180, weight_kg=90, body_frame="medium",
             activity_level="moderate", conditions=[], direction="lose", timeline_weeks=16)
    d.update(kw)
    return te.EngineInput(**d)


def test_bmi_and_bodyfat_reasonable():
    r = te.compute(_base())
    assert 27 < r.bmi < 28
    assert 15 < r.body_fat_pct < 35
    assert r.lean_mass_kg < 90


def test_kcal_floor_male():
    # Very aggressive: short timeline, high activity clamp still respects floor.
    r = te.compute(_base(weight_kg=60, activity_level="sedentary", timeline_weeks=8))
    assert r.daily_kcal >= 1500


def test_kcal_floor_female():
    r = te.compute(_base(sex="female", weight_kg=50, activity_level="sedentary", timeline_weeks=8))
    assert r.daily_kcal >= 1200


def test_loss_rate_cap_1pct():
    r = te.compute(_base(weight_kg=100, direction="lose", timeline_weeks=10))
    # stretch weekly rate must not exceed 1% of bodyweight (1.0 kg here).
    assert r.weekly_rate_kg <= 1.0 + 1e-6
    stretch = next(t for t in r.targets if t.label == "stretch")
    assert (100 - stretch.weight_kg) / 10 <= 1.0 + 1e-6


def test_gain_rate_cap_half_pct():
    r = te.compute(_base(direction="gain", weight_kg=80, timeline_weeks=12))
    stretch = next(t for t in r.targets if t.label == "stretch")
    weekly = (stretch.weight_kg - 80) / 12
    assert weekly <= 80 * 0.005 + 1e-6


def test_hypothyroid_slows_loss():
    healthy = te.compute(_base(conditions=[]))
    thyroid = te.compute(_base(conditions=["hypothyroid"]))
    assert thyroid.weekly_rate_kg < healthy.weekly_rate_kg
    assert "hypothyroid" in " ".join(thyroid.condition_notes).lower() or \
        "hypothyroid" in thyroid.reasoning.lower()


def test_female_muscle_gain_half_of_male():
    male = te.compute(_base(sex="male", direction="gain", age=25))
    female = te.compute(_base(sex="female", direction="gain", age=25))
    m_stretch = next(t for t in male.targets if t.label == "stretch")
    f_stretch = next(t for t in female.targets if t.label == "stretch")
    m_rate = (m_stretch.weight_kg - 90) / 16
    f_rate = (f_stretch.weight_kg - 90) / 16
    assert f_rate < m_rate


def test_muscle_gain_declines_with_age():
    young = te.compute(_base(sex="male", direction="gain", age=22))
    old = te.compute(_base(sex="male", direction="gain", age=55))
    y = (next(t for t in young.targets if t.label == "stretch").weight_kg - 90) / 16
    o = (next(t for t in old.targets if t.label == "stretch").weight_kg - 90) / 16
    assert o < y


def test_exceeds_stretch_flagged():
    # Wants to lose 40 kg in 8 weeks — impossible safely.
    r = te.compute(_base(weight_kg=100, desired_weight_kg=60, timeline_weeks=8))
    assert r.exceeds_stretch is True
    assert r.realistic_timeline_weeks and r.realistic_timeline_weeks > 8


def test_conservative_lt_expected_lt_stretch():
    r = te.compute(_base(weight_kg=100, direction="lose"))
    c = next(t for t in r.targets if t.label == "conservative").weight_kg
    e = next(t for t in r.targets if t.label == "expected").weight_kg
    s = next(t for t in r.targets if t.label == "stretch").weight_kg
    assert c > e > s  # more loss = lower weight


def test_diabetes_reduces_carbs():
    plain = te.compute(_base(conditions=[]))
    t2d = te.compute(_base(conditions=["type2Diabetes"]))
    assert t2d.macros["carbs_g"] < plain.macros["carbs_g"]
