"""Generate the ExerciseDB mapping report for our exercise catalog.

Runs ExerciseDBMediaProvider.enrich() against every exercise in
seed_data.EXERCISES and writes a Markdown report of what matched and what
didn't, to backend/reports/exercisedb_mapping_report.md.

Usage:
    cd backend
    RAPIDAPI_KEY=... python scripts/generate_exercisedb_mapping_report.py

Without a real RAPIDAPI_KEY (e.g. this dev sandbox), every exercise reports
as unmapped ("RAPIDAPI_KEY not configured") — that's expected, not a bug in
the matcher. Re-run with a real key (see backend/.env.example) to get the
real match results; this script does not call any live seed/DB code, it
only reads the in-memory catalog and calls the provider.

Add --offline-demo to instead score the matcher against a small hand-picked
sample of real ExerciseDB entries (recalled from public documentation, not
fetched live) purely to sanity-check the matching *logic* end-to-end when
you have no key handy. That mode is clearly marked in its own report
section and is not a substitute for a real run.
"""
from __future__ import annotations

import argparse
import sys
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# seed_data.py does `from db import db`, which needs motor + MONGO_URL/DB_NAME
# at import time. We only need its EXERCISES list (pure data), so stub the
# `db` module out rather than pulling in a real Mongo connection for a report.
if "db" not in sys.modules:
    _db_stub = types.ModuleType("db")
    _db_stub.db = None

    async def _noop_ensure_indexes():
        return None

    _db_stub.ensure_indexes = _noop_ensure_indexes
    sys.modules["db"] = _db_stub

import media_provider as mp  # noqa: E402
from seed_data import EXERCISES  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parents[1] / "reports"
LIVE_REPORT_PATH = REPORTS_DIR / "exercisedb_mapping_report.md"
OFFLINE_DEMO_REPORT_PATH = REPORTS_DIR / "exercisedb_mapping_report.offline_demo.md"

# Small hand-picked sample of ExerciseDB-shaped entries for --offline-demo.
# Recalled from public ExerciseDB documentation/screenshots, NOT fetched from
# the live API — ids/gifUrls here are illustrative, not verified current data.
_OFFLINE_FIXTURE = [
    {"id": "0025", "name": "barbell bench press", "target": "pectorals", "gifUrl": "https://v2.exercisedb.io/image/0025"},
    {"id": "0287", "name": "dumbbell bench press", "target": "pectorals", "gifUrl": "https://v2.exercisedb.io/image/0287"},
    {"id": "0662", "name": "push-up", "target": "pectorals", "gifUrl": "https://v2.exercisedb.io/image/0662"},
    {"id": "0398", "name": "barbell shoulder press", "target": "delts", "gifUrl": "https://v2.exercisedb.io/image/0398"},
    {"id": "0399", "name": "dumbbell shoulder press", "target": "delts", "gifUrl": "https://v2.exercisedb.io/image/0399"},
    {"id": "0651", "name": "barbell bent over row", "target": "lats", "gifUrl": "https://v2.exercisedb.io/image/0651"},
    {"id": "0652", "name": "dumbbell row", "target": "lats", "gifUrl": "https://v2.exercisedb.io/image/0652"},
    {"id": "0032", "name": "lat pulldown", "target": "lats", "gifUrl": "https://v2.exercisedb.io/image/0032"},
    {"id": "0648", "name": "pull-up", "target": "lats", "gifUrl": "https://v2.exercisedb.io/image/0648"},
    {"id": "1454", "name": "barbell squat", "target": "quads", "gifUrl": "https://v2.exercisedb.io/image/1454"},
    {"id": "0794", "name": "goblet squat", "target": "quads", "gifUrl": "https://v2.exercisedb.io/image/0794"},
    {"id": "1467", "name": "barbell romanian deadlift", "target": "hamstrings", "gifUrl": "https://v2.exercisedb.io/image/1467"},
    {"id": "0705", "name": "glute bridge", "target": "glutes", "gifUrl": "https://v2.exercisedb.io/image/0705"},
    {"id": "0002", "name": "plank", "target": "abs", "gifUrl": "https://v2.exercisedb.io/image/0002"},
    # Deliberately no entries for: bodyweight squat variant naming, band-based
    # exercises, treadmill/outdoor walk, dead bug, pike push-up — this is what
    # a genuine "unmapped, falls back to placeholder" result looks like.
]


def _row(ex: dict, media: dict) -> str:
    matched = media.get("demo_url") is not None
    status = "✅ matched" if matched else "❌ unmapped"
    detail = media.get("attribution", "")
    score = media.get("match_score", "")
    return f"| {ex['slug']} | {ex['name']} | {', '.join(ex['muscle_groups'])} | {status} | {score} | {detail} |"


def _table_header() -> list[str]:
    return [
        "| slug | name | muscle_groups | status | score | detail |",
        "|---|---|---|---|---|---|",
    ]


def run_live() -> tuple[list[str], int, int]:
    provider = mp.ExerciseDBMediaProvider()
    lines = _table_header()
    matched_count = 0
    for ex in EXERCISES:
        media = provider.enrich(ex["name"])
        if media.get("demo_url"):
            matched_count += 1
        lines.append(_row(ex, media))
    return lines, matched_count, len(EXERCISES)


def run_offline_demo() -> tuple[list[str], int, int]:
    """Same matcher, same catalog, but candidates come from _OFFLINE_FIXTURE
    instead of the network — demonstrates the matching logic without a key."""
    provider = mp.ExerciseDBMediaProvider()
    provider._api_key = "offline-demo"  # bypass the "no key" short-circuit

    def _fake_candidates(hint: dict):
        norm_query = mp._normalize(hint["query"])
        # crude substring pre-filter, same as a real name-search endpoint would do
        return [c for c in _OFFLINE_FIXTURE if norm_query.split(" ")[0] in c["name"]
                or c.get("target") in hint.get("targets", [])]

    lines = _table_header()
    matched_count = 0
    with patch.object(provider, "_candidates", side_effect=_fake_candidates):
        for ex in EXERCISES:
            media = provider.enrich(ex["name"])
            if media.get("demo_url"):
                matched_count += 1
            lines.append(_row(ex, media))
    return lines, matched_count, len(EXERCISES)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-demo", action="store_true",
                         help="Score the matcher against a small offline fixture instead of the live API.")
    args = parser.parse_args()

    out = ["# ExerciseDB mapping report", ""]

    if args.offline_demo:
        lines, matched, total = run_offline_demo()
        out.append("> **OFFLINE DEMO MODE** — candidates came from a small hand-picked local fixture, "
                    "not the live ExerciseDB API. This checks the matching *logic*, not real coverage. "
                    "Run without `--offline-demo` and a real `RAPIDAPI_KEY` for the authoritative report.")
        report_path = OFFLINE_DEMO_REPORT_PATH
    else:
        lines, matched, total = run_live()
        if not (mp.os.environ.get("RAPIDAPI_KEY") or ""):
            out.append("> **No RAPIDAPI_KEY set** — every row below is unmapped because the provider "
                        "short-circuits without a key, not because of a real mismatch. Set `RAPIDAPI_KEY` "
                        "(see `backend/.env.example`) and re-run for real results.")
        report_path = LIVE_REPORT_PATH

    out.append("")
    out.append(f"**{matched}/{total} exercises matched.**")
    out.append("")
    out.extend(lines)
    out.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(out) + "\n")
    print(f"Wrote {report_path} ({matched}/{total} matched)")


if __name__ == "__main__":
    main()
