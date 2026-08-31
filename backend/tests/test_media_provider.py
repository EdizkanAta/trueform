"""Unit tests for ExerciseDBMediaProvider — mocked ExerciseDB (RapidAPI) responses.

No network calls are made: requests.get is patched per-test. Covers the
match / no-match / error paths that must never crash exercise seeding, plus
the MediaProvider registry wiring in get_media_provider().
"""
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import media_provider as mp  # noqa: E402


def _resp(status_ok=True, json_body=None, raise_json=False):
    """Build a fake requests.Response-like object."""
    class _R:
        ok = status_ok

        def json(self):
            if raise_json:
                raise ValueError("not json")
            return json_body

    return _R()


BENCH_PRESS_CANDIDATE = {
    "id": "0025", "name": "barbell bench press", "target": "pectorals",
    "bodyPart": "chest", "equipment": "barbell",
    "gifUrl": "https://v2.exercisedb.io/image/abc123",
}
UNRELATED_CANDIDATE = {
    "id": "9999", "name": "seated leg curl", "target": "hamstrings",
    "bodyPart": "upper legs", "equipment": "leg curl machine",
    "gifUrl": "https://v2.exercisedb.io/image/zzz999",
}


@pytest.fixture(autouse=True)
def _api_key(monkeypatch):
    monkeypatch.setenv("RAPIDAPI_KEY", "test-key-123")
    yield


def test_no_api_key_returns_unmapped_without_network_call(monkeypatch):
    monkeypatch.delenv("RAPIDAPI_KEY", raising=False)
    with patch("media_provider.requests.get") as mock_get:
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")
    mock_get.assert_not_called()
    assert result["demo_url"] is None
    assert result["source"] == "exercisedb"
    assert "RAPIDAPI_KEY" in result["attribution"]


def test_name_search_match_populates_demo_url_and_attribution():
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[BENCH_PRESS_CANDIDATE])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")

    assert result["demo_url"] == BENCH_PRESS_CANDIDATE["gifUrl"]
    assert result["source"] == "exercisedb.p.rapidapi.com"
    assert result["exercisedb_id"] == "0025"
    assert result["match_score"] > provider.MATCH_THRESHOLD
    assert "0025" in result["attribution"]
    assert "RapidAPI" in result["license"]
    # Only the name-search endpoint should have been hit.
    assert mock_get.call_count == 1
    called_url = mock_get.call_args.args[0]
    assert "/exercises/name/" in called_url


def test_falls_back_to_target_search_when_name_search_is_empty():
    def _side_effect(url, headers=None, timeout=None):
        if "/exercises/name/" in url:
            return _resp(json_body=[])
        if "/exercises/target/" in url:
            return _resp(json_body=[BENCH_PRESS_CANDIDATE])
        raise AssertionError(f"unexpected url: {url}")

    with patch("media_provider.requests.get", side_effect=_side_effect) as mock_get:
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")

    assert result["demo_url"] == BENCH_PRESS_CANDIDATE["gifUrl"]
    urls = [c.args[0] for c in mock_get.call_args_list]
    assert any("/exercises/name/" in u for u in urls)
    assert any("/exercises/target/" in u for u in urls)


def test_low_similarity_candidate_falls_back_to_placeholder():
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[UNRELATED_CANDIDATE])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")

    assert result["demo_url"] is None
    assert result["source"] == "exercisedb"
    assert "No confident" in result["attribution"]


def test_unmapped_exercise_never_crashes():
    """An exercise name outside our known catalog (no _SEARCH_HINTS entry)
    still works — it searches on the raw name and can miss cleanly."""
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Some Brand New Exercise Nobody Mapped")

    assert result["demo_url"] is None
    assert result["source"] == "exercisedb"


def test_candidate_missing_gif_url_falls_back_to_placeholder():
    no_gif = {**BENCH_PRESS_CANDIDATE, "gifUrl": None}
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[no_gif])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")

    assert result["demo_url"] is None
    assert "no demo GIF" in result["attribution"]


def test_http_error_status_never_crashes():
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(status_ok=False, json_body=None)
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")

    assert result["demo_url"] is None


def test_network_exception_never_crashes():
    with patch("media_provider.requests.get", side_effect=mp.requests.ConnectionError("boom")):
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")

    assert result["demo_url"] is None


def test_malformed_json_never_crashes():
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=None, raise_json=True)
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")

    assert result["demo_url"] is None


def test_non_list_json_body_is_treated_as_no_candidates():
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body={"error": "not found"})
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")

    assert result["demo_url"] is None


def test_unexpected_exception_in_matching_is_swallowed(monkeypatch):
    provider = mp.ExerciseDBMediaProvider()
    monkeypatch.setattr(provider, "_best_match", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    result = provider.enrich("Barbell Bench Press")
    assert result["demo_url"] is None
    assert "lookup failed" in result["attribution"]


def test_equipment_mismatch_does_not_beat_correct_equipment_variant():
    """Regression: plain fuzzy-string similarity favors a short wrong-equipment
    name ("dumbbell row") over a longer correct-equipment one ("barbell bent
    over row") because SequenceMatcher's ratio is length-sensitive. The
    equipment-keyword bonus/penalty must correct for that."""
    dumbbell_row = {
        "id": "0652", "name": "dumbbell row", "target": "lats",
        "gifUrl": "https://v2.exercisedb.io/image/0652",
    }
    barbell_row = {
        "id": "0651", "name": "barbell bent over row", "target": "lats",
        "gifUrl": "https://v2.exercisedb.io/image/0651",
    }
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[dumbbell_row, barbell_row])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Row")

    assert result["exercisedb_id"] == "0651"


def test_get_media_provider_selects_exercisedb(monkeypatch):
    monkeypatch.setenv("MEDIA_PROVIDER", "exercisedb")
    provider = mp.get_media_provider()
    assert isinstance(provider, mp.ExerciseDBMediaProvider)


def test_get_media_provider_still_defaults_to_wger(monkeypatch):
    monkeypatch.delenv("MEDIA_PROVIDER", raising=False)
    provider = mp.get_media_provider()
    assert isinstance(provider, mp.WgerMediaProvider)


def test_get_media_provider_unknown_value_falls_back_to_custom(monkeypatch):
    monkeypatch.setenv("MEDIA_PROVIDER", "not-a-real-provider")
    provider = mp.get_media_provider()
    assert isinstance(provider, mp.NullMediaProvider)
