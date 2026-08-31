# TrueForm — Product Requirements (living doc)

## Original problem statement
Mobile-first, medically-constrained physique app built in phases. Phase 1 (MVP) only for now;
stop for review before Phase 2. TypeScript everywhere, secrets in env, no silent mocking. Dark,
clinical, data-forward "lab instrument" design. Provider-agnostic AI behind one backend interface
(generatePlan, coachChat, renderFutureSelf). Non-negotiable safety rules 1–7.

## Architecture (as built)
- Frontend: Expo Router (React Native + TS), StyleSheet design tokens (dark-first, light derived),
  5 tabs (Today/Plan/Coach/Progress/Profile), react-native-keyboard-controller, expo-image,
  react-native-svg charts, gesture-handler/reanimated comparison viewer.
- Backend: FastAPI + Motor (MongoDB), JWT (HTTPBearer, uuid ids), background render jobs + polling.
  Modules: security, target_engine, ai_provider (Claude Sonnet 4.6 + Gemini Nano Banana via
  Emergent key), media_provider (wger CC-BY-SA), plan_builder, coach_filter, object_storage,
  seed_data, server.
- Storage: Emergent Managed Object Storage (private photos + renders), backend-only.

## User personas
- Weight-loss adult with a metabolic condition (e.g. hypothyroid/T2D) tired of fantasy promises.
- Muscle-gain adult (incl. women) wanting an honest, age-appropriate ceiling.
- Home/gym/traveling user who needs the plan to adapt to their environment.

## Core requirements (static)
- 18+ age gate + explicit consent; block pregnancy / ED-history / <18 from plan generation w/ resources.
- 3 identity-preserving renders; kcal floors 1200/1500; ≤1%/wk loss, ≤0.5%/wk gain; condition modifiers.
- Coach never gives surgical/cosmetic/lab-diagnosis advice (output filter + tests).
- Photos private, encrypted, deletable; full account+data delete; export.

## Implemented (2026-06 / this session)
- Auth: signup (18+ + consent), login, me — JWT. [done]
- Onboarding 5-step wizard (basics, activity+environment+equipment+limitations, conditions+diet
  history, goal+timeline slider, motivation); environmentSchedule per weekday. [done]
- Photo capture (camera + silhouette overlay + gallery) with permission flow. [done]
- Generate: background job, concurrent 3-render pipeline w/ retries, polling, error+retry. [done]
- Targets: 3 renders carousel, per-render weight/body-fat, engine reasoning, exceeds-stretch warning,
  blur toggle, choose target. [done]
- Plan: weekly day chips, environment toggle (gym/home+/home-none) with movement-pattern swap,
  meals (full-bleed cards + recipes), workouts (wger media), recovery, lifestyle habits. [done]
- Today: streak, next milestone, workout/meal checkboxes, quick log (energy/pain), recovery trigger,
  coach nudge. [done]
- Coach: Claude chat + safety filter. [done]
- Progress: draggable comparison viewer (base vs render/latest), weight log, SVG trend chart w/
  filter chips. [done]
- Settings: units, daily reminder (local notif), export (Share), logout, delete account. [done]
- Tests: 16 unit (TargetEngine + coach_filter) + 30 e2e backend — all passing.

## Corrective pass (post-MVP review)
- [DONE 2026-06] Item 1 (theme) COMPLETE: `src/theme/theme.ts` is the single source of truth
  (every hex/rgba declared once) incl. a THEME-INDEPENDENT `overlay` group (scrim, onImage,
  cameraBg, silhouette derived from accent teal) + radius.pill. `tokens.ts` maps it with zero
  literals. **Grep across all src/ + app/ (excl. theme.ts) = ZERO hardcoded hex/rgba.** App launches
  **dark by default**; **light mode is a persisted Settings toggle** (Profile → Appearance,
  AsyncStorage key tf_theme). Verified by testing_agent iteration_2 (Today/Plan) + iteration_3
  (toggle live-switch, persistence across reload, targets/photo overlay theme-independent) — all green.
  metro.config.js untouched (StyleSheet token system, Option 1).
- [PARTIAL 2026-06] Item 2 render realism: prompt logic now scales FACIAL soft-tissue change to the
  computed body-fat delta (subtle ~−5%, obvious ~−10%+) with strict identity lock (bone structure,
  eyes, nose, ears, hairline, hair/beard, skin tone, expression). Only `build_render_prompt` in
  ai_provider.py changed; TargetEngine math untouched. STILL TODO: magnitude + identity QA gates and
  the −5/−10/−15% calibration test.
- [TODO] Item 3: show target weight + est. body-fat% + "what it takes" on Targets AND Progress.
- [TODO] Item 4: env toggle binds day's environmentSchedule; swap every exercise (no barbell under home).
- [TODO] Item 5: MediaProvider real GIF/video thumbnails per exercise (wger, CC-BY-SA).
- [TODO] Item 6: one-tap blur on all body photos, blurred by default except Progress comparison.

## Corrective pass — CONSOLIDATED COMPLETE (2026-06, testing iteration_6: 13/13 BE + FE all green)
- Item 1 theme: dark default + light toggle (persisted) + zero hardcoded hex/rgba (grep clean). DONE.
- Item 2 exercise media/detail: form_cues + poster_image_url per exercise; tap row → detail sheet
  (sets/reps/rest + cues + poster/placeholder); renderExercisePose stub (interface only). Media
  source = wger.de (CC-BY-SA 4.0); real GIF/video pending a dedicated licensed provider. DONE (media asset is a poster fallback).
- Item 3 personalized header: workout day header uses chosen future-self render. DONE.
- Item 4 environment toggle: 3 settings, per-day binding, bodyweight swap (no barbell under home). DONE.
- Item 5 render stats: weight + body-fat% + "what it takes" on Targets AND Progress. DONE.
- Item 6 privacy: renders/photos blurred by default (Targets + Plan header) w/ one-tap reveal;
  Progress comparison exempt. DONE.
- Item 7 close-out: grep zero; MVP acceptance checklist reported to user.

## Exercise media — ExerciseDB (2026-06)
- MEDIA_PROVIDER=exercisedb (backend/.env). RAPIDAPI_KEY set (RapidAPI acct subscribed to ExerciseDB).
- Live ExerciseDB API no longer returns `gifUrl`; GIFs come from an authenticated /image
  endpoint. ExerciseDBMediaProvider.enrich now stores demo_url=`/api/exercise-media/{id}`.
- New backend proxy `GET /api/exercise-media/{id}` fetches the GIF server-side with the key and
  streams it (Cache-Control 1d) so the key never reaches the client. Frontend `mediaUrl()` in
  api/client.ts prefixes relative media paths with the backend base; plan.tsx uses it.
- Re-seeded: 20/22 exercises mapped to ExerciseDB ids; verified GIFs render live on Plan tab.
- Pulled from GitHub EdizkanAta/trueform main (merged origin ExerciseDBMediaProvider + tests/reports).

## Backlog / remaining (P-levels)
- P0 (Phase 2 gate): none blocking MVP.
- P1: SSE streaming coach; text-model-authored render prompts; DOB native picker; auth rate limiting.
- P2: Navy-method body fat; per-user persisted blur; split server.py into routers.

## Phase 2 (NOT started — after sign-off)
RevenueCat paywall, HealthKit/Health Connect sync, milestone interpolation renders, adaptive plan
regeneration, grocery/recipe swaps, ghost-overlay photo alignment, share card, maintenance plan.

## Phase 3 (NOT started)
Lab OCR + reference-range flags, condition modules with citations, clinician read-only portal,
multilingual.

## Next tasks
- Await user review of MVP; push to GitHub `phase-1-mvp` branch via Save-to-GitHub.
- Then pick from P1 backlog or begin Phase 2 on approval.
