"""Identity (face-embedding) gate + calibration background-job pattern.

Covers iteration 5 review request:
- POST /api/calibration returns 200 quickly with {job_id, status:'running'}
- GET /api/calibration/job/{job_id} polls to done with identity fields
- Route ordering: /calibration/view?token=... not shadowed by /calibration/job/{id}
- POST /api/generate flow still works and carries identity_* qa fields
- GET /api/files/{path}?token= returns real PNG/JPEG bytes for owner
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("EXPO_PUBLIC_BACKEND_URL", "https://attainable-body.preview.emergentagent.com").rstrip("/")
EMAIL = "e2e1788128321@trueform.app"
PASSWORD = "Test1234!"

CAL_POLL_TIMEOUT = 240
GEN_POLL_TIMEOUT = 240
POLL_INTERVAL = 5


@pytest.fixture(scope="module")
def token() -> str:
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": EMAIL, "password": PASSWORD}, timeout=15)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("access_token")
    assert tok, "no access_token"
    return tok


@pytest.fixture(scope="module")
def auth_headers(token) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# --------------------------------------------------------------------------- #
# Calibration background-job pattern
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def calibration_job(auth_headers) -> dict:
    """POST /api/calibration must return quickly (well under 60s CF cap)
    with {job_id, status:'running'}. Then poll to done."""
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/calibration", headers=auth_headers, timeout=30)
    elapsed = time.time() - t0
    assert r.status_code == 200, f"POST /api/calibration failed: {r.status_code} {r.text[:300]}"
    assert elapsed < 15, f"POST should be near-instant, took {elapsed:.1f}s"
    body = r.json()
    assert "job_id" in body and body.get("status") == "running", f"unexpected body {body}"
    job_id = body["job_id"]

    # Poll until done
    deadline = time.time() + CAL_POLL_TIMEOUT
    last = None
    while time.time() < deadline:
        pr = requests.get(f"{BASE_URL}/api/calibration/job/{job_id}",
                          headers=auth_headers, timeout=20)
        assert pr.status_code == 200, f"poll failed: {pr.status_code} {pr.text[:300]}"
        last = pr.json()
        st = last.get("status")
        if st == "done":
            return last
        if st == "error":
            pytest.fail(f"calibration job errored: {last.get('error')}")
        time.sleep(POLL_INTERVAL)
    pytest.fail(f"calibration timed out after {CAL_POLL_TIMEOUT}s, last={last}")


def test_calibration_post_fast_and_returns_job(auth_headers):
    """POST /api/calibration returns 200 with job_id quickly (background pattern)."""
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/api/calibration", headers=auth_headers, timeout=30)
    elapsed = time.time() - t0
    assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
    assert elapsed < 15, f"expected <15s, got {elapsed:.1f}s"
    b = r.json()
    assert b.get("status") == "running"
    assert isinstance(b.get("job_id"), str) and len(b["job_id"]) >= 8


def test_calibration_job_done_shape(calibration_job):
    """Done payload has current_body_fat_pct, identity_all_pass, renders[3], pairwise_distinctness."""
    j = calibration_job
    assert j.get("status") == "done"
    assert isinstance(j.get("current_body_fat_pct"), (int, float))
    assert isinstance(j.get("identity_all_pass"), bool), f"identity_all_pass missing/wrong type: {j.get('identity_all_pass')}"
    renders = j.get("renders")
    assert isinstance(renders, list) and len(renders) == 3, f"renders shape: {renders}"
    drops = sorted(r["drop_pct"] for r in renders)
    assert drops == [5, 10, 15]
    pw = j.get("pairwise_distinctness")
    assert isinstance(pw, dict)
    for k in ("5vs10", "5vs15", "10vs15"):
        assert k in pw, f"missing key {k} in pairwise_distinctness={pw}"


def test_calibration_renders_have_identity_fields(calibration_job):
    """Each of the 3 renders' qa must include identity_checked/similarity/pass/mode."""
    for r in calibration_job["renders"]:
        qa = r.get("qa")
        assert isinstance(qa, dict), f"missing qa in render {r}"
        assert "identity_checked" in qa
        assert "identity_similarity" in qa
        assert "identity_pass" in qa
        assert "identity_mode" in qa
        assert isinstance(qa["identity_checked"], bool)
        assert isinstance(qa["identity_pass"], bool)
        assert qa["identity_mode"] in ("ok", "retry_low_face", "kept_original")


def test_calibration_identity_detected_and_passes(calibration_job):
    """For this user's base, face IS detectable: identity_checked=true,
    identity_similarity is a real number, identity_pass=true, identity_all_pass=true."""
    for r in calibration_job["renders"]:
        qa = r["qa"]
        assert qa["identity_checked"] is True, f"face not detected on drop {r['drop_pct']}: {qa}"
        sim = qa["identity_similarity"]
        assert isinstance(sim, (int, float)), f"identity_similarity not numeric: {sim}"
        assert -1.0 <= sim <= 1.0, f"identity_similarity out of range: {sim}"
        assert qa["identity_pass"] is True, f"identity_pass false on drop {r['drop_pct']}: {qa}"
    assert calibration_job["identity_all_pass"] is True


# --------------------------------------------------------------------------- #
# Route ordering: /calibration/view NOT shadowed by /calibration/job/{id}
# --------------------------------------------------------------------------- #
def test_calibration_view_route_not_shadowed(token):
    """GET /api/calibration/view?token=<jwt> returns 200 text/html."""
    r = requests.get(f"{BASE_URL}/api/calibration/view",
                     params={"token": token}, timeout=20)
    assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text[:200]}"
    ct = r.headers.get("content-type", "")
    assert "text/html" in ct, f"expected text/html, got {ct}"
    assert "<html" in r.text.lower()


def test_calibration_view_requires_valid_token():
    r = requests.get(f"{BASE_URL}/api/calibration/view",
                     params={"token": "not-a-jwt"}, timeout=15)
    assert r.status_code == 401, f"expected 401 for garbage token, got {r.status_code}"


def test_calibration_job_requires_auth():
    """GET /api/calibration/job/xxx must require auth (not shadowed by /view)."""
    r = requests.get(f"{BASE_URL}/api/calibration/job/nonexistent", timeout=15)
    # Should be 401 (no auth), not confused with /view
    assert r.status_code in (401, 403), f"expected 401/403, got {r.status_code}: {r.text[:150]}"


# --------------------------------------------------------------------------- #
# /api/files serves real image bytes for calibration renders
# --------------------------------------------------------------------------- #
def _is_image(b: bytes) -> bool:
    return b.startswith(b"\x89PNG\r\n\x1a\n") or b.startswith(b"\xff\xd8\xff")


def test_calibration_files_return_image_bytes(calibration_job, token):
    """GET /api/files/{path}?token= returns real PNG/JPEG bytes for each render."""
    for r in calibration_job["renders"]:
        path = r["path"]
        resp = requests.get(f"{BASE_URL}/api/files/{path}", params={"token": token}, timeout=30)
        assert resp.status_code == 200, f"files fetch failed for {path}: {resp.status_code}"
        assert len(resp.content) > 1000, f"suspiciously small image: {len(resp.content)} bytes"
        assert _is_image(resp.content), f"not PNG/JPEG magic: {resp.content[:8]!r}"


def test_calibration_files_require_token(calibration_job):
    path = calibration_job["renders"][0]["path"]
    r = requests.get(f"{BASE_URL}/api/files/{path}", timeout=15)
    assert r.status_code in (401, 403), f"expected 401/403 without token, got {r.status_code}"


# --------------------------------------------------------------------------- #
# Main render job also carries identity_* fields
# --------------------------------------------------------------------------- #
@pytest.fixture(scope="module")
def generate_job(auth_headers) -> dict:
    r = requests.post(f"{BASE_URL}/api/generate", headers=auth_headers, timeout=30)
    assert r.status_code == 200, f"POST /api/generate: {r.status_code} {r.text[:300]}"
    b = r.json()
    job_id = b.get("job_id")
    assert job_id, f"no job_id: {b}"

    deadline = time.time() + GEN_POLL_TIMEOUT
    last = None
    while time.time() < deadline:
        pr = requests.get(f"{BASE_URL}/api/generate/{job_id}",
                          headers=auth_headers, timeout=20)
        assert pr.status_code == 200, f"{pr.status_code}: {pr.text[:200]}"
        last = pr.json()
        st = last.get("status")
        if st == "done":
            return last
        if st == "error":
            pytest.fail(f"generate errored: {last.get('error')}")
        time.sleep(POLL_INTERVAL)
    pytest.fail(f"generate timed out, last={last}")


def test_generate_renders_have_identity_fields(generate_job):
    """Each future_self_set render (conservative/expected/stretch) must have
    path/weight_kg/body_fat_pct/what_it_takes and qa with identity_* fields."""
    fss = generate_job.get("future_self_set") or generate_job.get("result", {}).get("future_self_set")
    assert fss, f"no future_self_set in job: keys={list(generate_job.keys())}"
    renders = fss.get("renders")
    assert isinstance(renders, dict), f"renders not dict: {renders}"
    for label in ("conservative", "expected", "stretch"):
        rr = renders.get(label)
        assert rr, f"missing {label}"
        for k in ("path", "weight_kg", "body_fat_pct", "what_it_takes"):
            assert k in rr, f"{label} missing {k}: keys={list(rr.keys())}"
        qa = rr.get("qa")
        assert isinstance(qa, dict), f"{label} qa missing/wrong: {qa}"
        for k in ("identity_checked", "identity_similarity", "identity_pass"):
            assert k in qa, f"{label} qa missing {k}: {qa}"
        assert isinstance(qa["identity_checked"], bool)
        assert isinstance(qa["identity_pass"], bool)
