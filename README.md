# TrueForm — Phase 1 (MVP)

TrueForm helps adults 18+ set a **realistic, medically-constrained** physique target and reach
it. Upload a full-body photo + vitals/conditions/timeline → the backend `TargetEngine` computes
safe targets → **Gemini Nano Banana** renders three future-self images (conservative / expected /
stretch, image-to-image, identity-preserving) → a diet + training plan is built → a daily
**Claude** coach and progress-photo comparison keep you on track.

Positioning: the opposite of a fantasy filter — *your* attainable body and the honest path to it.

---

## Architecture

```
┌──────────────────────────┐        REST / JWT        ┌──────────────────────────────┐
│  Expo (React Native, TS)  │  ───────────────────▶   │  FastAPI (Python)              │
│  Expo Router, 5 tabs      │                          │  ├─ security.py  (JWT, 18+)    │
│  StyleSheet design tokens │  ◀───────────────────    │  ├─ target_engine.py (core IP) │
└──────────────────────────┘        JSON / images      │  ├─ ai_provider.py (AIProvider)│
        │  base photo (multipart)                       │  ├─ media_provider.py (wger)  │
        ▼                                                │  ├─ plan_builder.py           │
  Emergent Object Storage  ◀── backend only ───────────│  ├─ coach_filter.py (safety)  │
  (private photos + renders)                            │  └─ server.py (routes+jobs)   │
                                                         └───────────────┬───────────────┘
   Claude Sonnet 4.6 (text) ◀── Emergent Universal Key ─┤   MongoDB (Motor, uuid ids)
   Gemini Nano Banana (image) ◀──────────────────────── ┘
```

- **All AI calls are backend-only**, behind a single provider-agnostic `AIProvider` interface with
  three capabilities: `generate_plan`, `coach_chat`, `render_future_self`. Swap providers/models by
  editing env vars only — no app-code changes.
- **Background render job**: `POST /api/generate` creates a job; the client polls
  `GET /api/generate/{job_id}`. The three renders run concurrently, each with internal retries, and
  always return three images or a clear error with retry.
- **Cost logging**: every AI call writes a row to `ai_cost_log` (kind, model, chars/images) so you
  can see unit economics.

### Models chosen (and why)
| Capability | Provider / model | Why |
|---|---|---|
| Plans, coach, reasoning | **Anthropic Claude Sonnet 4.6** | Best instruction-following + safety for medical-adjacent text; your stated preference. |
| Future-self renders | **Gemini "Nano Banana" `gemini-3.1-flash-image-preview`** | True image-to-image; preserves face/pose/skin/hair/clothing, edits only body composition. |

Both run on the **Emergent Universal Key** (`EMERGENT_LLM_KEY`) — no third-party keys needed. To
swap, change `AI_TEXT_PROVIDER/MODEL` or `AI_IMAGE_PROVIDER/MODEL` in `backend/.env`.

### Exercise demo media — license
`MEDIA_PROVIDER=wger` (default) → the free **wger** open exercise database (`wger.de`, content
**CC-BY-SA 4.0**), enriched at seed time and stored per-exercise with `source` + `license` +
`attribution`. `MEDIA_PROVIDER=exercisedb` → the **ExerciseDB** API on RapidAPI
(`exercisedb.p.rapidapi.com`, requires `RAPIDAPI_KEY` — see `backend/.env.example`); it maps each
of our exercise names to an ExerciseDB exercise id by fuzzy name + target-muscle matching and uses
the demo GIF as `demo_url`/`poster_image_url`, recording the ExerciseDB id, source and license per
exercise. Both sit behind the same `MediaProvider` interface (`media_provider.py`) so you can drop
in your own filmed videos later (`MEDIA_PROVIDER=custom`) with **no code changes**. An exercise a
provider can't confidently map falls back to the in-app "Demo coming soon" placeholder — it's never
left half-populated or wrong. No YouTube hotlinking, no scraping. Attribution is shown in-app
(Profile screen). See `backend/reports/exercisedb_mapping_report.md` (regenerate with
`python backend/scripts/generate_exercisedb_mapping_report.py`) for which of our 22 catalog
exercises the ExerciseDB provider matches.

---

## Environment variables

`backend/.env`
```
MONGO_URL=...              # provided by platform (do not edit)
DB_NAME=trueform_database
EMERGENT_LLM_KEY=...        # Universal key: Claude + Nano Banana + Object Storage
JWT_SECRET=...             # openssl rand -hex 32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_MINUTES=43200
AI_TEXT_PROVIDER=anthropic
AI_TEXT_MODEL=claude-sonnet-4-6
AI_IMAGE_PROVIDER=gemini
AI_IMAGE_MODEL=gemini-3.1-flash-image-preview
MEDIA_PROVIDER=wger
```

`frontend/.env` (managed by platform)
```
EXPO_PUBLIC_BACKEND_URL=...   # backend base URL; app calls it + "/api"
```

> If `EMERGENT_LLM_KEY` is missing, coach/render calls fail with a clear error surfaced in the app
> (retry screen on the render step). No third-party services are silently mocked.

---

## Run

Both services run under supervisor in this environment.
```
sudo supervisorctl restart backend
sudo supervisorctl restart expo
```
Open the app via Expo Go (QR) or the web preview. Health check: `GET /api/health`.

## Tests
```
cd backend
python -m pytest tests/test_target_engine.py tests/test_coach_filter.py -q   # unit (rules + filter)
python -m pytest tests/backend_test.py -n 0                                   # e2e regression
```
- `TargetEngine`: BMI/body-fat, 1%/wk loss & 0.5%/wk gain caps, 1200/1500 kcal floors, condition
  modifiers (hypothyroid slower, T2D carb shift), age/sex muscle ceilings, exceeds-stretch flagging.
- `coach_filter`: strips surgical/cosmetic advice and lab-diagnosis, appends physician redirect.

---

## Suggestions (NOT implemented — awaiting your approval)

1. **Streaming coach over SSE.** Backend `coach_chat` already streams internally; the mobile client
   currently awaits the full reply for Expo Go reliability. I can wire true token streaming.
2. **Text model writes the render prompt.** Today `build_render_prompt()` is a deterministic
   template from `TargetEngine` stats (fast, reliable). Optionally have Claude author each render
   prompt for richer, more individualized edits.
3. **Server-side image encryption-at-rest key** + signed short-TTL file tokens (currently the JWT is
   reused as the `?token=` for web image reads).
4. **Onboarding date-of-birth picker** (native wheel) instead of `YYYY-MM-DD` text entry.
5. **Deurenberg → Navy method** body-fat when tape measurements (waist/neck/hip) are collected.
6. **Rate limiting + account lockout** on auth, and email verification / password reset.
7. **Blur-by-default privacy** persisted per user (currently a one-tap toggle on the Targets screen).
8. **Split `server.py`** into routers (auth / plan / coach / progress) — it's ~680 lines.
