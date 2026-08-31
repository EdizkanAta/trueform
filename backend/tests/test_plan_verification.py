"""
Consolidated corrective pass — Backend verification for /api/plan.

Items covered:
- ITEM 3: chosen_render_path returned for personalized workout header.
- ITEM 4: environment=home_no_equipment → all workout exercises equipment=='none'.
- ITEM 2: workout exercises include non-empty form_cues, poster_image_url field present.
- BACKEND stub: renderExercisePose is interface-only (no HTTP route).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "").rstrip("/")
EMAIL = "e2e1788128321@trueform.app"
PASSWORD = "Test1234!"


@pytest.fixture(scope="module")
def auth_headers():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
    body = r.json()
    token = body.get("access_token") or body.get("token")
    assert token, f"no token in login response: {body}"
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def plan_default(auth_headers):
    r = requests.get(f"{BASE_URL}/api/plan", headers=auth_headers, timeout=60)
    assert r.status_code == 200, f"/api/plan default failed: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def plan_home_no_eq(auth_headers):
    r = requests.get(f"{BASE_URL}/api/plan?environment=home_no_equipment",
                     headers=auth_headers, timeout=60)
    assert r.status_code == 200, f"/api/plan?env=home_no_equipment: {r.status_code} {r.text}"
    return r.json()


@pytest.fixture(scope="module")
def plan_gym(auth_headers):
    r = requests.get(f"{BASE_URL}/api/plan?environment=gym",
                     headers=auth_headers, timeout=60)
    assert r.status_code == 200, f"/api/plan?env=gym: {r.status_code} {r.text}"
    return r.json()


# ITEM 3 - chosen_render_path present + non-null (personalized workout header)
class TestChosenRenderPath:
    def test_chosen_render_path_field_present(self, plan_default):
        assert "chosen_render_path" in plan_default

    def test_chosen_render_path_non_empty(self, plan_default):
        v = plan_default.get("chosen_render_path")
        assert v, f"chosen_render_path is empty/None: {v!r}"

    def test_chosen_render_path_preserved_on_env_override(self, plan_home_no_eq):
        # Even when environment= is passed and plan is rebuilt, backend must
        # still expose the chosen future-self render path.
        assert plan_home_no_eq.get("chosen_render_path")


# ITEM 4 - environment toggle to home_no_equipment strips all equipment
def _workout_exercises(plan):
    xs = []
    for d in plan["days"]:
        if d.get("type") != "recovery":
            xs.extend(d.get("workout", []))
    return xs


class TestEnvironmentToggle:
    def test_home_no_equipment_all_bodyweight(self, plan_home_no_eq):
        xs = _workout_exercises(plan_home_no_eq)
        assert xs, "no workout exercises returned for home_no_equipment"
        bad = [(e.get("name"), e.get("equipment")) for e in xs
               if e.get("equipment") != "none"]
        assert not bad, f"non-bodyweight exercises leaked: {bad}"

    def test_home_no_equipment_no_barbell(self, plan_home_no_eq):
        xs = _workout_exercises(plan_home_no_eq)
        names = [e.get("name", "").lower() for e in xs]
        offenders = [n for n in names if "barbell" in n]
        assert not offenders, f"barbell exercises present: {offenders}"

    def test_gym_has_barbell(self, plan_gym):
        xs = _workout_exercises(plan_gym)
        assert xs
        # In gym the seed catalog uses named barbell/dumbbell lifts.
        names = " ".join(e.get("name", "").lower() for e in xs)
        assert "barbell" in names or "dumbbell" in names, \
            f"gym environment returned no barbell/dumbbell lifts: " \
            f"{[e.get('name') for e in xs]}"

    def test_environment_label_reflected(self, plan_home_no_eq):
        # Any workout day should carry the requested environment on override
        for d in plan_home_no_eq["days"]:
            if d.get("type") != "recovery":
                assert d.get("environment") == "home_no_equipment", \
                    f"day.environment={d.get('environment')}"


# ITEM 2 - form_cues + poster_image_url present on every exercise
class TestExerciseMedia:
    def test_form_cues_non_empty_default(self, plan_default):
        xs = _workout_exercises(plan_default)
        assert xs
        missing = [e.get("name") for e in xs
                   if not (isinstance(e.get("form_cues"), list) and e["form_cues"])]
        assert not missing, f"exercises missing form_cues: {missing}"

    def test_form_cues_non_empty_home_no_eq(self, plan_home_no_eq):
        xs = _workout_exercises(plan_home_no_eq)
        assert xs
        missing = [e.get("name") for e in xs
                   if not (isinstance(e.get("form_cues"), list) and e["form_cues"])]
        assert not missing, f"home_no_eq missing form_cues: {missing}"

    def test_poster_image_url_field_present(self, plan_default):
        xs = _workout_exercises(plan_default)
        # Field must be present (value may be null when wger returned no demo).
        missing = [e.get("name") for e in xs if "poster_image_url" not in e]
        assert not missing, f"exercises missing poster_image_url key: {missing}"

    def test_exercise_slugs_and_stats(self, plan_default):
        xs = _workout_exercises(plan_default)
        for e in xs:
            assert e.get("slug"), f"missing slug: {e}"
            assert e.get("sets"), f"missing sets: {e}"
            assert e.get("reps"), f"missing reps: {e}"
            assert e.get("rest_sec") is not None, f"missing rest_sec: {e}"


# ITEM 4/5 supporting - engine data available for chosen render on progress endpoint
class TestProgressRenderStats:
    def test_progress_has_chosen_render(self, auth_headers):
        r = requests.get(f"{BASE_URL}/api/progress",
                         headers=auth_headers, timeout=30)
        assert r.status_code == 200, f"/api/progress failed: {r.text}"
        p = r.json()
        cr = p.get("chosen_render")
        assert cr, "progress.chosen_render missing"
        assert cr.get("weight_kg") is not None
        assert cr.get("body_fat_pct") is not None
        assert cr.get("what_it_takes")


# renderExercisePose stub — no HTTP route should exist
class TestRenderExercisePoseStub:
    def test_no_render_exercise_pose_route(self, auth_headers):
        # These are the reasonable candidate paths a route would take.
        for path in [
            "/api/render_exercise_pose",
            "/api/renderExercisePose",
            "/api/exercises/render",
            "/api/plan/exercise/render",
        ]:
            r = requests.post(f"{BASE_URL}{path}", headers=auth_headers,
                              json={"exercise_name": "Push-Up", "cues": []},
                              timeout=15)
            # Must not be a 200 success. 404/405/401 all acceptable.
            assert r.status_code != 200, \
                f"unexpected route {path} returned 200: {r.text[:200]}"
