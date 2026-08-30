"""End-to-end TrueForm backend regression suite (pytest).

Uses the public EXPO_PUBLIC_BACKEND_URL. Covers auth (18+ consent), onboarding,
photo upload + file ownership, generate + polling, targets/plan (incl. env swap),
logs (recovery trigger), coach (surgical-advice filter), progress, account
export/delete.
"""
import io
import os
import time
import uuid
from datetime import date

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://attainable-body.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"


def _rand_email(prefix="test"):
    # Server lowercases emails; keep prefix lower-case for equality checks.
    return f"test_{prefix}_{uuid.uuid4().hex[:10]}@trueform.app"


def _signup_payload(email, dob="1990-05-10", pregnant=False, ed=False):
    return {
        "email": email, "password": "Test1234!", "dob": dob, "sex": "male",
        "height_cm": 180.0, "unit_preference": "metric",
        "consent": {
            "age_confirmed_18": True, "physician_ack": True, "privacy_ack": True,
            "is_pregnant": pregnant, "eating_disorder_history": ed,
        },
    }


def _profile_payload():
    return {
        "weight_kg": 90.0, "body_frame": "medium", "activity_level": "moderate",
        "training_environment": "gym", "home_equipment": [],
        "conditions": [], "medications_text": "", "injuries_text": "",
        "diet_history": [], "motivation": "health", "direction": "lose_fat",
        "desired_weight_kg": 82.0, "timeline_weeks": 16,
        "same_place_every_workout": True, "environment_schedule": {},
    }


@pytest.fixture(scope="module")
def user():
    """Signup a fresh user, upload photo, complete onboarding, run generate."""
    email = _rand_email("primary")
    r = requests.post(f"{API}/auth/signup", json=_signup_payload(email))
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    return {"email": email, "token": token, "headers": h, "id": r.json()["user"]["id"]}


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class TestAuth:
    def test_health(self):
        r = requests.get(f"{API}/health")
        assert r.status_code == 200 and r.json()["ok"] is True

    def test_signup_underage_rejected(self):
        r = requests.post(f"{API}/auth/signup", json=_signup_payload(_rand_email("minor"), dob="2020-01-01"))
        assert r.status_code == 400

    def test_signup_missing_consent_rejected(self):
        payload = _signup_payload(_rand_email("noconsent"))
        payload["consent"]["physician_ack"] = False
        r = requests.post(f"{API}/auth/signup", json=payload)
        assert r.status_code == 400

    def test_signup_duplicate_email(self):
        email = _rand_email("dup")
        r1 = requests.post(f"{API}/auth/signup", json=_signup_payload(email))
        assert r1.status_code == 200
        r2 = requests.post(f"{API}/auth/signup", json=_signup_payload(email))
        assert r2.status_code == 409

    def test_login_success(self):
        email = _rand_email("login")
        requests.post(f"{API}/auth/signup", json=_signup_payload(email))
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "Test1234!"})
        assert r.status_code == 200 and "access_token" in r.json()

    def test_login_wrong_password(self):
        email = _rand_email("wrongpw")
        requests.post(f"{API}/auth/signup", json=_signup_payload(email))
        r = requests.post(f"{API}/auth/login", json={"email": email, "password": "wrong"})
        assert r.status_code == 401

    def test_me_requires_token(self, user):
        r = requests.get(f"{API}/auth/me", headers=user["headers"])
        assert r.status_code == 200 and r.json()["email"] == user["email"]
        r2 = requests.get(f"{API}/auth/me")
        assert r2.status_code in (401, 403)


# --------------------------------------------------------------------------- #
# Onboarding + blocking
# --------------------------------------------------------------------------- #
class TestOnboarding:
    def test_profile_healthy_user_not_blocked(self, user):
        r = requests.post(f"{API}/onboarding/profile", json=_profile_payload(), headers=user["headers"])
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["blocked"] in (None, False)

    def test_generate_blocked_for_pregnant_user(self):
        email = _rand_email("preg")
        r = requests.post(f"{API}/auth/signup", json=_signup_payload(email, pregnant=True))
        assert r.status_code == 200
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        requests.post(f"{API}/onboarding/profile", json=_profile_payload(), headers=h)
        # Even without base photo, blocked path returns 403 first per handler order?
        # Handler checks blocked BEFORE base_photo_path — verify 403.
        r2 = requests.post(f"{API}/generate", headers=h)
        assert r2.status_code == 403, r2.text
        detail = r2.json()["detail"]
        assert detail["blocked"] is True
        assert "resources" in detail
        assert "pregnancy" in detail["reasons"]

    def test_generate_blocked_for_ed_history(self):
        email = _rand_email("ed")
        r = requests.post(f"{API}/auth/signup", json=_signup_payload(email, ed=True))
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        requests.post(f"{API}/onboarding/profile", json=_profile_payload(), headers=h)
        r2 = requests.post(f"{API}/generate", headers=h)
        assert r2.status_code == 403
        assert "eating_disorder_history" in r2.json()["detail"]["reasons"]


# --------------------------------------------------------------------------- #
# Photo upload + file authz
# --------------------------------------------------------------------------- #
# 1x1 PNG
_PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff"
        b"?\x00\x05\xfe\x02\xfe\xa74\x8fJ\x00\x00\x00\x00IEND\xaeB`\x82")


class TestPhoto:
    def test_upload_photo(self, user):
        files = {"file": ("t.png", io.BytesIO(_PNG), "image/png")}
        r = requests.post(f"{API}/photo/upload", files=files, headers=user["headers"])
        assert r.status_code == 200, r.text
        path = r.json()["path"]
        assert path and user["id"] in path
        user["photo_path"] = path

    def test_file_requires_token(self, user):
        assert "photo_path" in user
        r = requests.get(f"{BASE_URL}/api/files/{user['photo_path']}")
        assert r.status_code == 401

    def test_file_owner_can_fetch(self, user):
        r = requests.get(f"{BASE_URL}/api/files/{user['photo_path']}?token={user['token']}")
        assert r.status_code == 200
        assert r.content[:4] == b"\x89PNG"

    def test_file_other_user_forbidden(self, user):
        # Signup a second user, ensure they cannot fetch first user's photo
        other = _rand_email("other")
        r = requests.post(f"{API}/auth/signup", json=_signup_payload(other))
        other_token = r.json()["access_token"]
        r2 = requests.get(f"{BASE_URL}/api/files/{user['photo_path']}?token={other_token}")
        assert r2.status_code == 403


# --------------------------------------------------------------------------- #
# Generate future-self renders (background job)
# --------------------------------------------------------------------------- #
_REAL_PHOTO_URL = "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=600&q=80"


def _real_photo_bytes():
    """A realistic full-body photo for image-to-image (the render model cannot
    edit a 1x1 placeholder). Falls back to the tiny PNG if the network is down."""
    try:
        r = requests.get(_REAL_PHOTO_URL, timeout=20)
        if r.ok and len(r.content) > 5000:
            return r.content, "body.jpg", "image/jpeg"
    except requests.RequestException:
        pass
    return _PNG, "t.png", "image/png"


class TestGenerate:
    def test_generate_full_flow(self, user):
        # Upload a realistic base photo first (real product input, not a 1x1 px).
        content, name, ctype = _real_photo_bytes()
        up = requests.post(f"{API}/photo/upload",
                           files={"file": (name, io.BytesIO(content), ctype)},
                           headers=user["headers"])
        assert up.status_code == 200, up.text

        r = requests.post(f"{API}/generate", headers=user["headers"])
        assert r.status_code == 200, r.text
        job_id = r.json()["job_id"]
        # Poll up to ~120s
        final = None
        for _ in range(60):
            s = requests.get(f"{API}/generate/{job_id}", headers=user["headers"])
            assert s.status_code == 200
            body = s.json()
            if body["status"] in ("done", "error"):
                final = body
                break
            time.sleep(2)
        assert final is not None, "Job never completed"
        if final["status"] == "error":
            pytest.fail(f"Generate errored: {final.get('error')}")
        assert final["status"] == "done"
        fss = final["future_self_set"]
        for label in ("conservative", "expected", "stretch"):
            assert label in fss["renders"]
            rn = fss["renders"][label]
            assert rn["path"] and rn["weight_kg"] and rn["what_it_takes"]


# --------------------------------------------------------------------------- #
# Targets + plan (also verifies env swap swap-to-bodyweight)
# --------------------------------------------------------------------------- #
class TestTargetsAndPlan:
    def test_targets_endpoint(self, user):
        r = requests.get(f"{API}/targets", headers=user["headers"])
        assert r.status_code == 200
        body = r.json()
        assert "renders" in body and "engine" in body
        assert "reasoning" in body["engine"]

    def test_choose_target_builds_plan(self, user):
        r = requests.post(f"{API}/target/choose", json={"label": "expected"}, headers=user["headers"])
        assert r.status_code == 200 and r.json()["chosen_target"] == "expected"

    def test_choose_invalid_label(self, user):
        r = requests.post(f"{API}/target/choose", json={"label": "bogus"}, headers=user["headers"])
        assert r.status_code == 400

    def test_get_plan(self, user):
        r = requests.get(f"{API}/plan", headers=user["headers"])
        assert r.status_code == 200
        p = r.json()
        assert "days" in p and len(p["days"]) == 7
        assert p.get("daily_kcal") and p.get("macros")
        d0 = p["days"][0]
        assert "workout" in d0 and "meals" in d0

    def test_plan_env_swap_bodyweight(self, user):
        r = requests.get(f"{API}/plan?environment=home_no_equipment", headers=user["headers"])
        assert r.status_code == 200
        p = r.json()
        # Verify at least one training day exists and its exercises are bodyweight
        workout_days = [d for d in p["days"] if d.get("workout")]
        assert workout_days, "no workout days in rebuilt plan"
        equipment_seen = set()
        for d in workout_days:
            for ex in d["workout"]:
                equipment_seen.add(str(ex.get("equipment", "")).lower())
        # All equipment should be 'none' or empty for bodyweight
        non_bw = equipment_seen - {"none", "", "bodyweight"}
        assert not non_bw, f"Non-bodyweight equipment found after swap: {non_bw}"


# --------------------------------------------------------------------------- #
# Logs / Today
# --------------------------------------------------------------------------- #
class TestLogs:
    def test_upsert_log_normal(self, user):
        payload = {"date": date.today().isoformat(), "weight_kg": 89.5,
                   "energy": 4, "pain": 1, "meals_completed": ["breakfast"],
                   "workout_completed": True}
        r = requests.post(f"{API}/logs", json=payload, headers=user["headers"])
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True and body["recovery_triggered"] is False

    def test_upsert_log_recovery(self, user):
        payload = {"date": date.today().isoformat(), "weight_kg": 89.5,
                   "energy": 2, "pain": 4}
        r = requests.post(f"{API}/logs", json=payload, headers=user["headers"])
        assert r.status_code == 200
        body = r.json()
        assert body["recovery_triggered"] is True
        assert "recovery_protocol" in body

    def test_list_logs(self, user):
        r = requests.get(f"{API}/logs", headers=user["headers"])
        assert r.status_code == 200
        assert isinstance(r.json()["logs"], list)

    def test_today(self, user):
        r = requests.get(f"{API}/today", headers=user["headers"])
        assert r.status_code == 200
        t = r.json()
        assert "day_plan" in t and "streak" in t and "next_milestone" in t
        assert t["has_plan"] is True


# --------------------------------------------------------------------------- #
# Coach — surgical advice filter
# --------------------------------------------------------------------------- #
class TestCoach:
    def test_coach_surgical_filter(self, user):
        payload = {"text": "should I get liposuction or a tummy tuck to remove fat?"}
        r = requests.post(f"{API}/coach/message", json=payload, headers=user["headers"])
        assert r.status_code == 200, r.text
        content = r.json()["message"]["content"].lower()
        # Filter must strip surgical/cosmetic procedure suggestions
        for term in ("liposuction", "tummy tuck", "cosmetic surgery", "bariatric surgery"):
            assert term not in content, f"Surgical term '{term}' leaked into coach reply"
        # Must include physician/professional redirect
        assert any(w in content for w in ("physician", "doctor", "medical professional", "healthcare"))

    def test_coach_messages_history(self, user):
        r = requests.get(f"{API}/coach/messages", headers=user["headers"])
        assert r.status_code == 200
        msgs = r.json()["messages"]
        assert len(msgs) >= 2
        roles = {m["role"] for m in msgs}
        assert "user" in roles and "assistant" in roles


# --------------------------------------------------------------------------- #
# Progress + account
# --------------------------------------------------------------------------- #
class TestProgressAndAccount:
    def test_progress(self, user):
        r = requests.get(f"{API}/progress", headers=user["headers"])
        assert r.status_code == 200
        p = r.json()
        assert "base_photo_path" in p and "progress_photos" in p and "weight_series" in p
        assert p["chosen_render"] is not None

    def test_progress_photo_upload(self, user):
        files = {"file": ("p.png", io.BytesIO(_PNG), "image/png")}
        r = requests.post(f"{API}/progress/photo", files=files, headers=user["headers"])
        assert r.status_code == 200
        assert r.json()["photo"]["path"]

    def test_export(self, user):
        r = requests.get(f"{API}/account/export", headers=user["headers"])
        assert r.status_code == 200
        d = r.json()
        for key in ("user", "profile", "goal", "plan", "logs", "coach_messages"):
            assert key in d

    def test_delete_account_last(self, user):
        # Use a separate user so it doesn't disrupt other tests order-wise.
        email = _rand_email("todelete")
        r = requests.post(f"{API}/auth/signup", json=_signup_payload(email))
        h = {"Authorization": f"Bearer {r.json()['access_token']}"}
        d = requests.delete(f"{API}/account", headers=h)
        assert d.status_code == 200
        m = requests.get(f"{API}/auth/me", headers=h)
        assert m.status_code == 401
