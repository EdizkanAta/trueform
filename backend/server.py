"""TrueForm backend — FastAPI + MongoDB (Motor), JWT auth, REST.

All AI calls live behind AIProvider (config-driven). Photos go through Emergent
Managed Object Storage. Background jobs generate the future-self renders; the
client polls for completion. Token/image costs are logged per request.
"""
import asyncio
import base64
import hashlib
import logging
import os
import uuid
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from dotenv import load_dotenv
from fastapi import (APIRouter, Depends, FastAPI, File, HTTPException, Query,
                     UploadFile, status)
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

load_dotenv()

from db import db, ensure_indexes  # noqa: E402
from security import (calculate_age, create_access_token, get_current_user,  # noqa: E402
                      hash_password, verify_password, JWT_SECRET, JWT_ALGORITHM)
import jwt as _jwt  # noqa: E402
import target_engine as te  # noqa: E402
import coach_filter  # noqa: E402
import plan_builder  # noqa: E402
import object_storage as objstore  # noqa: E402
from ai_provider import get_provider, build_render_prompt, render_with_magnitude_gate  # noqa: E402
from seed_data import seed_if_empty  # noqa: E402

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("trueform")

app = FastAPI(title="TrueForm API")
api = APIRouter(prefix="/api")


async def _cost_logger(entry: dict) -> None:
    entry["created_at"] = datetime.now(timezone.utc).isoformat()
    entry["id"] = str(uuid.uuid4())
    await db.ai_cost_log.insert_one(entry)
    logger.info("AI cost: %s %s %s", entry.get("kind"), entry.get("model"),
                {k: v for k, v in entry.items() if k in ("chars_out", "images")})

ai = get_provider(cost_logger=_cost_logger)

# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class ConsentFlags(BaseModel):
    age_confirmed_18: bool = False
    physician_ack: bool = False
    privacy_ack: bool = False
    is_pregnant: bool = False
    eating_disorder_history: bool = False


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    dob: date
    sex: str
    height_cm: float
    unit_preference: str = "metric"
    consent: ConsentFlags


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    weight_kg: float
    body_frame: str
    activity_level: str
    training_environment: str
    home_equipment: List[str] = []
    conditions: List[str] = []
    medications_text: str = ""
    injuries_text: str = ""
    diet_history: List[Dict] = []
    motivation: str = "health"
    # goal
    direction: str
    desired_weight_kg: Optional[float] = None
    timeline_weeks: int = 16
    same_place_every_workout: bool = True
    environment_schedule: Dict[str, str] = {}
    environment_transition: Optional[Dict] = None


class ChooseTargetIn(BaseModel):
    label: str


class LogIn(BaseModel):
    date: str
    weight_kg: Optional[float] = None
    energy: Optional[int] = None
    pain: Optional[int] = None
    sleep_hours: Optional[float] = None
    meals_completed: List[str] = []
    workout_completed: bool = False
    notes: str = ""


class CoachIn(BaseModel):
    text: str


class SettingsIn(BaseModel):
    unit_preference: Optional[str] = None
    notification_time: Optional[str] = None
    notifications_enabled: Optional[bool] = None


def _clean(doc: dict) -> dict:
    if doc:
        doc.pop("_id", None)
    return doc


def public_user(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "dob": u["dob"], "sex": u["sex"],
            "height_cm": u["height_cm"], "unit_preference": u.get("unit_preference", "metric"),
            "consent": u.get("consent", {}),
            "onboarded": u.get("onboarded", False),
            "has_targets": u.get("has_targets", False),
            "has_plan": u.get("has_plan", False),
            "chosen_target": u.get("chosen_target"),
            "base_photo_path": u.get("base_photo_path"),
            "notification_time": u.get("notification_time", "08:00"),
            "notifications_enabled": u.get("notifications_enabled", True)}


def _is_blocked(user: dict) -> Optional[dict]:
    c = user.get("consent", {})
    reasons = []
    if calculate_age(date.fromisoformat(user["dob"])) < 18:
        reasons.append("under_18")
    if c.get("is_pregnant"):
        reasons.append("pregnancy")
    if c.get("eating_disorder_history"):
        reasons.append("eating_disorder_history")
    if reasons:
        return {
            "blocked": True, "reasons": reasons,
            "message": "For your safety, we can't generate a diet/exercise plan for you here.",
            "resources": [
                {"name": "NEDA Helpline (eating disorders)", "contact": "1-800-931-2237"},
                {"name": "Talk to your physician or OB-GYN", "contact": "Book an appointment"},
            ],
        }
    return None


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
@api.get("/")
async def root():
    return {"message": "TrueForm API", "status": "ok"}


@api.get("/health")
async def health():
    return {"ok": True, "service": "trueform", "time": datetime.now(timezone.utc).isoformat()}


@api.post("/auth/signup")
async def signup(data: SignupIn):
    if data.dob > date.today():
        raise HTTPException(400, "Date of birth cannot be in the future")
    if calculate_age(data.dob) < 18:
        raise HTTPException(400, "You must be at least 18 years old to use TrueForm")
    if not (data.consent.age_confirmed_18 and data.consent.physician_ack and data.consent.privacy_ack):
        raise HTTPException(400, "All consent acknowledgments are required")
    email = str(data.email).lower().strip()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "An account with this email already exists")
    now = datetime.now(timezone.utc).isoformat()
    user = {
        "id": str(uuid.uuid4()), "email": email, "dob": data.dob.isoformat(),
        "sex": data.sex, "height_cm": data.height_cm,
        "unit_preference": data.unit_preference,
        "password_hash": hash_password(data.password),
        "consent": data.consent.model_dump(),
        "onboarded": False, "has_targets": False, "has_plan": False,
        "chosen_target": None, "base_photo_path": None,
        "notification_time": "08:00", "notifications_enabled": True,
        "created_at": now, "deleted_at": None,
    }
    await db.users.insert_one(user)
    token = create_access_token(user["id"])
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}


@api.post("/auth/login")
async def login(data: LoginIn):
    email = str(data.email).lower().strip()
    user = await db.users.find_one({"email": email, "deleted_at": None})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    token = create_access_token(user["id"])
    return {"access_token": token, "token_type": "bearer", "user": public_user(user)}


@api.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return public_user(user)


# --------------------------------------------------------------------------- #
# Onboarding
# --------------------------------------------------------------------------- #
@api.post("/onboarding/profile")
async def save_profile(data: ProfileIn, user: dict = Depends(get_current_user)):
    profile = {
        "user_id": user["id"], "weight_kg": data.weight_kg, "body_frame": data.body_frame,
        "activity_level": data.activity_level, "training_environment": data.training_environment,
        "home_equipment": data.home_equipment, "conditions": data.conditions,
        "medications_text": data.medications_text, "injuries_text": data.injuries_text,
        "diet_history": data.diet_history, "motivation": data.motivation,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.health_profiles.update_one({"user_id": user["id"]}, {"$set": profile}, upsert=True)

    # environment schedule (per-weekday) — default same env every day
    schedule = data.environment_schedule or {}
    if data.same_place_every_workout or not schedule:
        schedule = {"default": data.training_environment}
    else:
        schedule.setdefault("default", data.training_environment)

    goal = {
        "user_id": user["id"], "direction": data.direction,
        "desired_weight_kg": data.desired_weight_kg, "timeline_weeks": data.timeline_weeks,
        "environment_schedule": schedule, "environment_transition": data.environment_transition,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.goals.update_one({"user_id": user["id"]}, {"$set": goal}, upsert=True)
    await db.users.update_one({"id": user["id"]}, {"$set": {"onboarded": True}})
    blocked = _is_blocked(user)
    return {"ok": True, "blocked": blocked}


# --------------------------------------------------------------------------- #
# Photos / object storage
# --------------------------------------------------------------------------- #
def _ext_from_filename(name: str) -> str:
    return (name.rsplit(".", 1)[-1].lower() if "." in name else "jpg")[:5]


@api.post("/photo/upload")
async def upload_base_photo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    sha = hashlib.sha256(data).hexdigest()
    ext = _ext_from_filename(file.filename or "photo.jpg")
    uid = str(uuid.uuid4())
    path = objstore.object_path(user["id"], ext, uid)
    await objstore.put_object(path, data, file.content_type or "image/jpeg")
    await db.users.update_one({"id": user["id"]},
                              {"$set": {"base_photo_path": path, "base_photo_sha256": sha}})
    logger.info("UPLOAD base photo user=%s path=%s sha256=%s bytes=%d",
                user["id"], path, sha, len(data))
    return {"path": path, "sha256": sha}


async def _resolve_user_from_token(token: str) -> Optional[dict]:
    try:
        payload = _jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return await db.users.find_one({"id": payload.get("sub"), "deleted_at": None})
    except Exception:
        return None


@api.get("/files/{path:path}")
async def serve_file(path: str, token: Optional[str] = Query(None)):
    # Auth: bearer header OR ?token= (web <img> cannot send headers).
    user = None
    if token:
        user = await _resolve_user_from_token(token)
    if not user:
        raise HTTPException(401, "Unauthorized")
    # Ownership: path must belong to this user.
    if f"/uploads/{user['id']}/" not in f"/{path}":
        raise HTTPException(403, "Forbidden")
    try:
        content, ctype = await objstore.get_object(path)
    except Exception:
        raise HTTPException(404, "Not found")
    return Response(content=content, media_type=ctype)


# --------------------------------------------------------------------------- #
# Generate future-self renders (background job + polling)
# --------------------------------------------------------------------------- #
def _engine_input(user: dict, profile: dict, goal: dict) -> te.EngineInput:
    return te.EngineInput(
        sex=user["sex"], age=calculate_age(date.fromisoformat(user["dob"])),
        height_cm=user["height_cm"], weight_kg=profile["weight_kg"],
        body_frame=profile["body_frame"], activity_level=profile["activity_level"],
        conditions=profile["conditions"], direction=goal["direction"],
        timeline_weeks=goal["timeline_weeks"], desired_weight_kg=goal.get("desired_weight_kg"),
    )


def _engine_result_dict(r: te.EngineResult) -> dict:
    return {
        "bmi": r.bmi, "body_fat_pct": r.body_fat_pct, "lean_mass_kg": r.lean_mass_kg,
        "tdee": r.tdee, "daily_kcal": r.daily_kcal, "macros": r.macros,
        "weekly_rate_kg": r.weekly_rate_kg, "reasoning": r.reasoning,
        "exceeds_stretch": r.exceeds_stretch,
        "realistic_timeline_weeks": r.realistic_timeline_weeks,
        "condition_notes": r.condition_notes,
        "targets": [t.__dict__ for t in r.targets],
    }


async def _run_generation(job_id: str, user: dict, profile: dict, goal: dict):
    try:
        result = te.compute(_engine_input(user, profile, goal))
        result_d = _engine_result_dict(result)
        await db.jobs.update_one({"id": job_id},
                                 {"$set": {"progress": 20, "engine": result_d}})
        # Base photo -> base64 for image-to-image. NEVER substitute a stock image.
        content, _ = await objstore.get_object(user["base_photo_path"])
        if not content:
            raise RuntimeError("Base photo bytes empty — refusing to substitute a stock image")
        render_sha = hashlib.sha256(content).hexdigest()
        logger.info("RENDER base photo user=%s path=%s sha256=%s bytes=%d stored_sha=%s match=%s",
                    user["id"], user["base_photo_path"], render_sha, len(content),
                    user.get("base_photo_sha256"), render_sha == user.get("base_photo_sha256"))
        base_b64 = base64.b64encode(content).decode("utf-8")

        renders = {}
        labels = ["conservative", "expected", "stretch"]

        async def render_one(label: str):
            target = next(t for t in result.targets if t.label == label)
            img_b64, qa = await render_with_magnitude_gate(
                ai, current_bf=result.body_fat_pct, target_bf=target.body_fat_pct,
                base_b64=base_b64, base_bytes=content, session_id=f"{job_id}-{label}",
            )
            img_bytes = base64.b64decode(img_b64)
            uid = str(uuid.uuid4())
            path = objstore.object_path(user["id"], "png", uid)
            await objstore.put_object(path, img_bytes, "image/png")
            logger.info("render %s qa=%s", label, qa)
            return label, {
                "path": path, "weight_kg": target.weight_kg, "weight_lb": target.weight_lb,
                "body_fat_pct": target.body_fat_pct, "what_it_takes": target.what_it_takes,
                "qa": qa,
            }

        # Render the three targets concurrently (each retries internally).
        results = await asyncio.gather(*[render_one(l) for l in labels])
        for label, data in results:
            renders[label] = data
        await db.jobs.update_one({"id": job_id}, {"$set": {"progress": 95}})

        fss = {
            "id": str(uuid.uuid4()), "user_id": user["id"], "goal_id": goal["user_id"],
            "base_photo_path": user["base_photo_path"], "renders": renders,
            "engine": result_d, "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.future_self_sets.update_one({"user_id": user["id"]}, {"$set": fss}, upsert=True)
        await db.users.update_one({"id": user["id"]}, {"$set": {"has_targets": True}})
        await db.jobs.update_one({"id": job_id},
                                 {"$set": {"status": "done", "progress": 100}})
    except Exception as e:  # clear error + retry on client
        logger.exception("Generation failed")
        await db.jobs.update_one({"id": job_id},
                                 {"$set": {"status": "error", "error": str(e)[:300]}})


@api.post("/generate")
async def generate(user: dict = Depends(get_current_user)):
    blocked = _is_blocked(user)
    if blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail=blocked)
    if not user.get("base_photo_path"):
        raise HTTPException(400, "Upload a base photo first")
    profile = await db.health_profiles.find_one({"user_id": user["id"]})
    goal = await db.goals.find_one({"user_id": user["id"]})
    if not profile or not goal:
        raise HTTPException(400, "Complete onboarding first")
    job = {"id": str(uuid.uuid4()), "user_id": user["id"], "status": "running",
           "progress": 5, "error": None, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.jobs.insert_one(job)
    asyncio.create_task(_run_generation(job["id"], user, _clean(profile), _clean(goal)))
    return {"job_id": job["id"], "status": "running"}


@api.get("/generate/{job_id}")
async def generate_status(job_id: str, user: dict = Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id, "user_id": user["id"]})
    if not job:
        raise HTTPException(404, "Job not found")
    out = {"job_id": job_id, "status": job["status"], "progress": job.get("progress", 0),
           "error": job.get("error")}
    if job["status"] == "done":
        fss = await db.future_self_sets.find_one({"user_id": user["id"]})
        out["future_self_set"] = _clean(fss) if fss else None
    return out


# --------------------------------------------------------------------------- #
# Calibration (magnitude-gate demonstration)
# --------------------------------------------------------------------------- #
@api.post("/calibration")
async def calibration(user: dict = Depends(get_current_user)):
    if not user.get("base_photo_path"):
        raise HTTPException(400, "Upload a base photo first")
    profile = await db.health_profiles.find_one({"user_id": user["id"]})
    goal = await db.goals.find_one({"user_id": user["id"]})
    if not profile or not goal:
        raise HTTPException(400, "Complete onboarding first")
    job = {"id": str(uuid.uuid4()), "user_id": user["id"], "status": "running",
           "progress": 5, "error": None, "created_at": datetime.now(timezone.utc).isoformat()}
    await db.calibration_jobs.insert_one(job)
    asyncio.create_task(_run_calibration(job["id"], user, _clean(profile), _clean(goal)))
    return {"job_id": job["id"], "status": "running"}


async def _run_calibration(job_id: str, user: dict, profile: dict, goal: dict):
    try:
        result = te.compute(_engine_input(user, profile, goal))
        content, _ = await objstore.get_object(user["base_photo_path"])
        base_b64 = base64.b64encode(content).decode("utf-8")
        current_bf = result.body_fat_pct

        async def one(drop: int):
            target_bf = round(max(3.0, current_bf - drop), 1)
            img_b64, qa = await render_with_magnitude_gate(
                ai, current_bf, target_bf, base_b64, content, f"calib-{user['id']}-{drop}")
            img_bytes = base64.b64decode(img_b64)
            path = objstore.object_path(user["id"], "png", str(uuid.uuid4()))
            await objstore.put_object(path, img_bytes, "image/png")
            return drop, img_bytes, {"drop_pct": drop, "target_body_fat_pct": target_bf,
                                     "path": path, "qa": qa}

        results = await asyncio.gather(*[one(d) for d in (5, 10, 15)])
        results.sort(key=lambda r: r[0])
        renders = [r[2] for r in results]
        out_bytes = [(r[0], r[1]) for r in results]

        from image_qa import change_score
        pairs = {}
        for i in range(len(out_bytes)):
            for j in range(i + 1, len(out_bytes)):
                pairs[f"{out_bytes[i][0]}vs{out_bytes[j][0]}"] = round(
                    change_score(out_bytes[i][1], out_bytes[j][1]), 4)

        doc = {"user_id": user["id"], "current_body_fat_pct": current_bf, "renders": renders,
               "pairwise_distinctness": pairs, "created_at": datetime.now(timezone.utc).isoformat()}
        await db.calibrations.update_one({"user_id": user["id"]}, {"$set": doc}, upsert=True)
        all_pass = all(r["qa"].get("identity_pass") for r in renders)
        await db.calibration_jobs.update_one({"id": job_id}, {"$set": {
            "status": "done", "progress": 100, "current_body_fat_pct": current_bf,
            "renders": renders, "pairwise_distinctness": pairs, "identity_all_pass": all_pass}})
    except Exception as e:
        logger.exception("Calibration failed")
        await db.calibration_jobs.update_one({"id": job_id},
                                             {"$set": {"status": "error", "error": str(e)[:300]}})


@api.get("/calibration/job/{job_id}")
async def calibration_status(job_id: str, user: dict = Depends(get_current_user)):
    job = await db.calibration_jobs.find_one({"id": job_id, "user_id": user["id"]})
    if not job:
        raise HTTPException(404, "Job not found")
    return _clean(job)


@api.get("/calibration/view")
async def calibration_view(token: str = Query(...)):
    user = await _resolve_user_from_token(token)
    if not user:
        raise HTTPException(401, "Unauthorized")
    calib = await db.calibrations.find_one({"user_id": user["id"]})
    if not calib:
        raise HTTPException(404, "No calibration yet")

    def cell(r: dict) -> str:
        url = f"/api/files/{r['path']}?token={token}"
        return (
            '<div style="flex:1;text-align:center">'
            f'<div style="color:#9BA0A8;font:600 12px sans-serif;letter-spacing:1.5px">'
            f'&minus;{r["drop_pct"]}% BF &middot; ~{r["target_body_fat_pct"]}%</div>'
            f'<img src="{url}" style="width:100%;border-radius:12px;margin-top:8px"/></div>'
        )

    cells = "".join(cell(r) for r in calib["renders"])
    html = (
        '<html><body style="margin:0;background:#0E0F12;padding:16px">'
        f'<div style="color:#F2F3F5;font:200 22px sans-serif">Calibration &middot; base at '
        f'~{calib["current_body_fat_pct"]}% body fat</div>'
        f'<div style="display:flex;gap:12px;margin-top:16px">{cells}</div>'
        '</body></html>'
    )
    return Response(content=html, media_type="text/html")


# --------------------------------------------------------------------------- #
# Targets + plan
# --------------------------------------------------------------------------- #
@api.get("/targets")
async def get_targets(user: dict = Depends(get_current_user)):
    fss = await db.future_self_sets.find_one({"user_id": user["id"]})
    if not fss:
        raise HTTPException(404, "No targets yet")
    return _clean(fss)


async def _build_and_save_plan(user: dict, env_schedule_override: Optional[Dict[str, str]] = None):
    profile = _clean(await db.health_profiles.find_one({"user_id": user["id"]}))
    goal = _clean(await db.goals.find_one({"user_id": user["id"]}))
    result = te.compute(_engine_input(user, profile, goal))
    exercises = [_clean(e) async for e in db.exercises.find({})]
    recipes = [_clean(r) async for r in db.recipes.find({})]
    schedule = env_schedule_override or goal.get("environment_schedule", {"default": "gym"})
    plan = plan_builder.build_plan(_engine_result_dict(result), exercises, recipes,
                                   schedule, profile["conditions"])
    return plan, profile, goal


@api.post("/target/choose")
async def choose_target(data: ChooseTargetIn, user: dict = Depends(get_current_user)):
    if data.label not in ("conservative", "expected", "stretch"):
        raise HTTPException(400, "Invalid target label")
    plan, profile, goal = await _build_and_save_plan(user)
    plan_doc = {"id": str(uuid.uuid4()), "user_id": user["id"], "goal_id": user["id"],
                "chosen_target": data.label, **plan,
                "environment_schedule": goal.get("environment_schedule"),
                "environment_transition": goal.get("environment_transition"),
                "created_at": datetime.now(timezone.utc).isoformat()}
    await db.plans.update_one({"user_id": user["id"]}, {"$set": plan_doc}, upsert=True)
    await db.users.update_one({"id": user["id"]},
                              {"$set": {"chosen_target": data.label, "has_plan": True}})
    return {"ok": True, "chosen_target": data.label}


@api.get("/plan")
async def get_plan(environment: Optional[str] = Query(None),
                   user: dict = Depends(get_current_user)):
    plan = await db.plans.find_one({"user_id": user["id"]})
    if not plan:
        raise HTTPException(404, "No plan yet")
    # chosen future-self render (for the workout day header cards)
    chosen_render_path = None
    fss = await db.future_self_sets.find_one({"user_id": user["id"]})
    if fss and user.get("chosen_target"):
        chosen_render_path = (fss.get("renders", {}).get(user["chosen_target"]) or {}).get("path")
    if environment:  # context switch (e.g. traveling) — rebuild, don't persist
        override = {"default": environment}
        rebuilt, _, _ = await _build_and_save_plan(user, override)
        rebuilt["chosen_target"] = plan.get("chosen_target")
        rebuilt["environment_override"] = environment
        rebuilt["chosen_render_path"] = chosen_render_path
        return rebuilt
    out = _clean(plan)
    out["chosen_render_path"] = chosen_render_path
    # enrich persisted workout entries with form cues / poster (plan is a snapshot)
    cue_map = {e["slug"]: e async for e in db.exercises.find({})}
    for day in out.get("days", []):
        for ex in day.get("workout", []):
            src = cue_map.get(ex.get("slug"), {})
            ex.setdefault("form_cues", src.get("form_cues", []))
            if not ex.get("form_cues"):
                ex["form_cues"] = src.get("form_cues", [])
            ex.setdefault("poster_image_url", src.get("poster_image_url"))
    return out


# --------------------------------------------------------------------------- #
# Daily logs + Today
# --------------------------------------------------------------------------- #
def _today_str() -> str:
    return date.today().isoformat()


def _streak(logs: List[dict]) -> int:
    done_dates = {l["date"] for l in logs
                  if l.get("workout_completed") or l.get("meals_completed")}
    streak = 0
    cur = date.today()
    while cur.isoformat() in done_dates:
        streak += 1
        cur = date.fromordinal(cur.toordinal() - 1)
    return streak


@api.post("/logs")
async def upsert_log(data: LogIn, user: dict = Depends(get_current_user)):
    doc = data.model_dump()
    doc["user_id"] = user["id"]
    doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.daily_logs.update_one({"user_id": user["id"], "date": data.date},
                                   {"$set": doc}, upsert=True)
    recovery_triggered = (data.pain is not None and data.pain >= 3) or \
                         (data.energy is not None and data.energy <= 2)
    resp = {"ok": True, "recovery_triggered": recovery_triggered}
    if recovery_triggered:
        resp["recovery_protocol"] = plan_builder.RECOVERY_PROTOCOL
    return resp


@api.get("/logs")
async def list_logs(user: dict = Depends(get_current_user)):
    logs = [_clean(l) async for l in db.daily_logs.find({"user_id": user["id"]}).sort("date", 1)]
    return {"logs": logs}


@api.get("/today")
async def today(user: dict = Depends(get_current_user)):
    plan = await db.plans.find_one({"user_id": user["id"]})
    logs = [_clean(l) async for l in db.daily_logs.find({"user_id": user["id"]})]
    weekday = date.today().strftime("%A")
    day_plan = None
    if plan:
        day_plan = next((d for d in plan["days"] if d["day"] == weekday), plan["days"][0])
    log_today = next((l for l in logs if l["date"] == _today_str()), None)
    goal = await db.goals.find_one({"user_id": user["id"]})
    next_milestone = None
    if goal:
        created = datetime.fromisoformat(goal["created_at"]).date()
        weeks_in = (date.today() - created).days // 7
        for m in (4, 8, 12, 16, 20, 24, 52):
            if m > weeks_in:
                next_milestone = {"week": m, "weeks_away": m - weeks_in}
                break
    return {
        "date": _today_str(), "weekday": weekday, "day_plan": day_plan,
        "log": log_today, "streak": _streak(logs), "next_milestone": next_milestone,
        "chosen_target": user.get("chosen_target"),
        "has_plan": bool(plan),
    }


# --------------------------------------------------------------------------- #
# Coach
# --------------------------------------------------------------------------- #
async def _coach_system_prompt(user: dict) -> str:
    profile = _clean(await db.health_profiles.find_one({"user_id": user["id"]})) or {}
    goal = _clean(await db.goals.find_one({"user_id": user["id"]})) or {}
    plan = await db.plans.find_one({"user_id": user["id"]})
    logs = [_clean(l) async for l in db.daily_logs.find({"user_id": user["id"]}).sort("date", -1).limit(7)]
    plan_summary = ""
    if plan:
        plan_summary = f"Daily kcal target ~{plan.get('daily_kcal')}, macros {plan.get('macros')}, chosen target {plan.get('chosen_target')}."
    return (
        "You are TrueForm's coach: direct, warm, and never shaming. Speak plainly. "
        "The user set a realistic, medically constrained physique goal.\n"
        f"User: {user['sex']}, age {calculate_age(date.fromisoformat(user['dob']))}. "
        f"Conditions: {profile.get('conditions', [])}. Injuries: {profile.get('injuries_text','none')}. "
        f"Goal: {goal.get('direction')} over {goal.get('timeline_weeks')} weeks. {plan_summary}\n"
        f"Recent logs (newest first): {logs}\n\n"
        "HARD RULES you must never break:\n"
        "1. Never describe or imply a shaming 'if you fail' scenario.\n"
        "2. Never give surgical or cosmetic-procedure advice. Loose skin = normal, natural management + 'discuss with a physician'.\n"
        "3. Never interpret lab results as a diagnosis or tell them to change medication.\n"
        "4. Never suggest going below 1200 kcal (female) / 1500 kcal (male) or losing >1%/gaining >0.5% bodyweight per week.\n"
        "When the user says they skipped, are hurt, exhausted, or cheated: adjust the plan supportively, never guilt them."
    )


@api.get("/coach/messages")
async def coach_messages(user: dict = Depends(get_current_user)):
    msgs = [_clean(m) async for m in db.coach_messages.find({"user_id": user["id"]}).sort("created_at", 1)]
    return {"messages": msgs}


@api.post("/coach/message")
async def coach_message(data: CoachIn, user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    user_msg = {"id": str(uuid.uuid4()), "user_id": user["id"], "role": "user",
                "content": data.text, "created_at": now}
    await db.coach_messages.insert_one(dict(user_msg))
    history = [_clean(m) async for m in db.coach_messages.find({"user_id": user["id"]}).sort("created_at", 1)]
    system = await _coach_system_prompt(user)
    try:
        raw = await ai.coach_chat(system, history, data.text, session_id=f"coach-{user['id']}")
    except Exception as e:
        logger.exception("Coach chat failed")
        raise HTTPException(502, f"Coach is unavailable: {str(e)[:120]}")
    safe, reasons = coach_filter.filter_output(raw)
    if reasons:
        logger.info("Coach filter triggered: %s", reasons)
    assistant_msg = {"id": str(uuid.uuid4()), "user_id": user["id"], "role": "assistant",
                     "content": safe, "filtered": reasons,
                     "created_at": datetime.now(timezone.utc).isoformat()}
    await db.coach_messages.insert_one(dict(assistant_msg))
    return {"message": _clean(assistant_msg)}


# --------------------------------------------------------------------------- #
# Progress
# --------------------------------------------------------------------------- #
@api.post("/progress/photo")
async def upload_progress_photo(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    data = await file.read()
    ext = _ext_from_filename(file.filename or "photo.jpg")
    uid = str(uuid.uuid4())
    path = objstore.object_path(user["id"], ext, uid)
    await objstore.put_object(path, data, file.content_type or "image/jpeg")
    doc = {"id": str(uuid.uuid4()), "user_id": user["id"], "date": _today_str(),
           "path": path, "aligned_to_base": False,
           "created_at": datetime.now(timezone.utc).isoformat(), "deleted_at": None}
    await db.progress_photos.insert_one(dict(doc))
    return {"photo": _clean(doc)}


@api.get("/progress")
async def progress(user: dict = Depends(get_current_user)):
    photos = [_clean(p) async for p in
              db.progress_photos.find({"user_id": user["id"], "deleted_at": None}).sort("created_at", 1)]
    logs = [_clean(l) async for l in db.daily_logs.find({"user_id": user["id"]}).sort("date", 1)]
    weight_series = [{"date": l["date"], "weight_kg": l["weight_kg"]}
                     for l in logs if l.get("weight_kg") is not None]
    fss = await db.future_self_sets.find_one({"user_id": user["id"]})
    chosen = user.get("chosen_target")
    chosen_render = None
    if fss and chosen:
        chosen_render = fss.get("renders", {}).get(chosen)
    return {
        "base_photo_path": user.get("base_photo_path"),
        "chosen_render": chosen_render, "progress_photos": photos,
        "weight_series": weight_series,
    }


# --------------------------------------------------------------------------- #
# Settings / account
# --------------------------------------------------------------------------- #
@api.patch("/settings")
async def update_settings(data: SettingsIn, user: dict = Depends(get_current_user)):
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    if updates:
        await db.users.update_one({"id": user["id"]}, {"$set": updates})
    fresh = await db.users.find_one({"id": user["id"]})
    return public_user(fresh)


@api.get("/account/export")
async def export_data(user: dict = Depends(get_current_user)):
    profile = _clean(await db.health_profiles.find_one({"user_id": user["id"]}))
    goal = _clean(await db.goals.find_one({"user_id": user["id"]}))
    plan = _clean(await db.plans.find_one({"user_id": user["id"]}))
    logs = [_clean(l) async for l in db.daily_logs.find({"user_id": user["id"]})]
    coach = [_clean(m) async for m in db.coach_messages.find({"user_id": user["id"]})]
    return {"user": public_user(user), "profile": profile, "goal": goal,
            "plan": plan, "logs": logs, "coach_messages": coach,
            "exported_at": datetime.now(timezone.utc).isoformat()}


@api.delete("/account")
async def delete_account(user: dict = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    await db.users.update_one({"id": user["id"]}, {"$set": {"deleted_at": now}})
    await db.progress_photos.update_many({"user_id": user["id"]}, {"$set": {"deleted_at": now}})
    # Purge personal data (photos remain in storage but are orphaned + inaccessible).
    await db.health_profiles.delete_many({"user_id": user["id"]})
    await db.goals.delete_many({"user_id": user["id"]})
    await db.plans.delete_many({"user_id": user["id"]})
    await db.daily_logs.delete_many({"user_id": user["id"]})
    await db.coach_messages.delete_many({"user_id": user["id"]})
    await db.future_self_sets.delete_many({"user_id": user["id"]})
    return {"ok": True}


app.include_router(api)
app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await ensure_indexes()
    try:
        await objstore.init_storage()
    except Exception as e:
        logger.warning("Object storage init deferred: %s", e)
    try:
        await seed_if_empty()
    except Exception as e:
        logger.warning("Seed skipped: %s", e)


@app.on_event("shutdown")
async def shutdown():
    pass
