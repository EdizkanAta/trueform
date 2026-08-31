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


FLY_CANDIDATE = {
    "id": "0025", "name": "cable fly", "target": "pectorals",
    "bodyPart": "chest", "equipment": "cable",
}
UNRELATED_CANDIDATE = {
    "id": "9999", "name": "seated leg curl", "target": "hamstrings",
    "bodyPart": "upper legs", "equipment": "leg curl machine",
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
    assert "RAPIDAPI_KEY" in result["attribution"]


def test_alias_takes_precedence_and_makes_no_network_call():
    """Curated alias exercises resolve to their verified id without any live lookup."""
    with patch("media_provider.requests.get") as mock_get:
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Bench Press")
    mock_get.assert_not_called()
    assert result["demo_url"] == "/api/exercise-media/0025"
    assert result["exercisedb_id"] == "0025"
    assert result["match_kind"] == "alias"
    assert result["media_kind"] == "gif"


def test_alias_approx_is_flagged():
    with patch("media_provider.requests.get") as mock_get:
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Band Lat Pulldown")
    mock_get.assert_not_called()
    assert result["match_kind"] == "alias_approx"
    assert result["demo_url"] == "/api/exercise-media/0198"


def test_cardio_is_static_no_gif():
    with patch("media_provider.requests.get") as mock_get:
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Incline Treadmill Walk")
    mock_get.assert_not_called()
    assert result["demo_url"] is None
    assert result["media_kind"] == "cardio_static"
    assert result["match_kind"] == "cardio"


def test_poster_only_is_static_no_gif():
    with patch("media_provider.requests.get") as mock_get:
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Plank")
    mock_get.assert_not_called()
    assert result["demo_url"] is None
    assert result["media_kind"] == "poster"
    assert result["match_kind"] == "poster_reviewed"


def test_fuzzy_name_match_for_uncurated_exercise(monkeypatch):
    """An exercise not in the alias/poster/cardio sets falls through to fuzzy."""
    monkeypatch.setitem(mp._SEARCH_HINTS, "Cable Fly", {"query": "cable fly", "targets": ["pectorals"]})
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[FLY_CANDIDATE])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Cable Fly")
    assert result["demo_url"] == "/api/exercise-media/0025"
    assert result["match_kind"] == "fuzzy"
    assert result["match_score"] > provider.MATCH_THRESHOLD
    assert mock_get.call_count == 1
    assert "/exercises/name/" in mock_get.call_args.args[0]


def test_falls_back_to_target_search_when_name_search_is_empty(monkeypatch):
    monkeypatch.setitem(mp._SEARCH_HINTS, "Cable Fly", {"query": "cable fly", "targets": ["pectorals"]})

    def _side_effect(url, headers=None, timeout=None):
        if "/exercises/name/" in url:
            return _resp(json_body=[])
        if "/exercises/target/" in url:
            return _resp(json_body=[FLY_CANDIDATE])
        raise AssertionError(f"unexpected url: {url}")

    with patch("media_provider.requests.get", side_effect=_side_effect) as mock_get:
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Cable Fly")

    assert result["demo_url"] == "/api/exercise-media/0025"
    urls = [c.args[0] for c in mock_get.call_args_list]
    assert any("/exercises/target/" in u for u in urls)


def test_low_similarity_candidate_falls_back_to_poster(monkeypatch):
    monkeypatch.setitem(mp._SEARCH_HINTS, "Cable Fly", {"query": "cable fly", "targets": ["pectorals"]})
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[UNRELATED_CANDIDATE])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Cable Fly")
    assert result["demo_url"] is None
    assert result["match_kind"] == "none"


def test_fuzzy_wrong_target_falls_back_to_poster(monkeypatch):
    """Even a high name-similarity candidate is rejected if its target disagrees."""
    monkeypatch.setitem(mp._SEARCH_HINTS, "Cable Fly", {"query": "cable fly", "targets": ["pectorals"]})
    wrong_target = {"id": "0025", "name": "cable fly", "target": "quads", "equipment": "cable"}
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[wrong_target])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Cable Fly")
    assert result["demo_url"] is None
    assert result["match_kind"] == "none"


def test_unmapped_exercise_never_crashes():
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Some Brand New Exercise Nobody Mapped")
    assert result["demo_url"] is None


def test_http_error_status_never_crashes(monkeypatch):
    monkeypatch.setitem(mp._SEARCH_HINTS, "Cable Fly", {"query": "cable fly", "targets": []})
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(status_ok=False, json_body=None)
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Cable Fly")
    assert result["demo_url"] is None


def test_network_exception_never_crashes(monkeypatch):
    monkeypatch.setitem(mp._SEARCH_HINTS, "Cable Fly", {"query": "cable fly", "targets": []})
    with patch("media_provider.requests.get", side_effect=mp.requests.ConnectionError("boom")):
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Cable Fly")
    assert result["demo_url"] is None


def test_malformed_json_never_crashes(monkeypatch):
    monkeypatch.setitem(mp._SEARCH_HINTS, "Cable Fly", {"query": "cable fly", "targets": []})
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=None, raise_json=True)
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Cable Fly")
    assert result["demo_url"] is None


def test_non_list_json_body_is_treated_as_no_candidates(monkeypatch):
    monkeypatch.setitem(mp._SEARCH_HINTS, "Cable Fly", {"query": "cable fly", "targets": []})
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body={"error": "not found"})
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Cable Fly")
    assert result["demo_url"] is None


def test_unexpected_exception_in_matching_is_swallowed(monkeypatch):
    monkeypatch.setitem(mp._SEARCH_HINTS, "Cable Fly", {"query": "cable fly", "targets": []})
    provider = mp.ExerciseDBMediaProvider()
    monkeypatch.setattr(provider, "_best_match", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    result = provider.enrich("Cable Fly")
    assert result["demo_url"] is None
    assert "lookup failed" in result["attribution"]


def test_equipment_mismatch_does_not_beat_correct_equipment_variant(monkeypatch):
    """Fuzzy path: equipment-keyword bonus/penalty must pick the barbell variant."""
    monkeypatch.setitem(mp._SEARCH_HINTS, "Barbell Pullover", {"query": "barbell pullover", "targets": ["lats"]})
    dumbbell = {"id": "0652", "name": "dumbbell pullover", "target": "lats", "equipment": "dumbbell"}
    barbell = {"id": "0651", "name": "barbell pullover", "target": "lats", "equipment": "barbell"}
    with patch("media_provider.requests.get") as mock_get:
        mock_get.return_value = _resp(json_body=[dumbbell, barbell])
        provider = mp.ExerciseDBMediaProvider()
        result = provider.enrich("Barbell Pullover")
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
