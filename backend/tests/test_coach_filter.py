"""Unit tests for the coach output safety filter (rules 1-3)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import coach_filter  # noqa: E402


def test_blocks_liposuction():
    text = "You could get liposuction to remove that fat quickly."
    safe, reasons = coach_filter.filter_output(text)
    assert "surgical_or_cosmetic" in reasons
    assert "liposuction" not in safe.lower()
    assert "physician" in safe.lower()


def test_blocks_surgery_generic():
    text = "Honestly, plastic surgery is the fastest way. Also eat more protein."
    safe, reasons = coach_filter.filter_output(text)
    assert "surgical_or_cosmetic" in reasons
    assert "protein" in safe.lower()  # non-offending advice preserved


def test_blocks_lab_interpretation():
    text = "Your labs show you have a thyroid condition, so stop taking your medication."
    safe, reasons = coach_filter.filter_output(text)
    assert "lab_interpretation" in reasons
    assert "physician" in safe.lower()


def test_loose_skin_gets_hint():
    text = "For loose skin, you might consider a tummy tuck."
    safe, reasons = coach_filter.filter_output(text)
    assert "surgical_or_cosmetic" in reasons
    assert "tummy tuck" not in safe.lower()
    assert "normal" in safe.lower()


def test_clean_text_passes_through():
    text = "Great work this week. Let's add a 10-minute walk after dinner."
    safe, reasons = coach_filter.filter_output(text)
    assert reasons == []
    assert safe == text
