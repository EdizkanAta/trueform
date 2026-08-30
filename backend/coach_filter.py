"""Coach output safety filter (rules 1-4).

Blocks surgical/cosmetic-procedure advice and lab-result *interpretation* from
the coach output, and appends a physician redirect when triggered. Unit tested.
"""
import re
from typing import Tuple, List

# Cosmetic / surgical procedures the coach must never advise.
_SURGICAL = [
    r"liposuction", r"\blipo\b", r"tummy tuck", r"abdominoplasty", r"bbl\b",
    r"brazilian butt", r"gastric (bypass|sleeve|band)", r"bariatric",
    r"coolsculpt", r"cryolipolysis", r"botox", r"filler[s]?", r"implant[s]?",
    r"cosmetic surgery", r"plastic surgery", r"skin removal surgery",
    r"surgical (removal|option|procedure)", r"nose job", r"rhinoplasty",
]

# Phrases that would constitute interpreting labs as a diagnosis / prescription.
_LAB_DIAGNOSIS = [
    r"you (are|'re) (pre)?diabetic", r"this means you have",
    r"your (labs?|results?|blood work) (show|indicate|mean|confirm)",
    r"you have (a|an)? ?(diagnos|deficiency|disease|condition)",
    r"(stop|start|increase|decrease|change) (taking )?your medication",
    r"adjust your (dose|medication|insulin)",
]

_SURGICAL_RE = re.compile("|".join(_SURGICAL), re.IGNORECASE)
_LAB_RE = re.compile("|".join(_LAB_DIAGNOSIS), re.IGNORECASE)

_REDIRECT = (
    "\n\nI can't give surgical, cosmetic-procedure, or medical-diagnosis advice — "
    "that's a conversation for your physician. I'm here for your diet, training, "
    "recovery and habits. Want me to adjust today's plan instead?"
)

_LOOSE_SKIN_HINT = (
    "Loose skin after weight loss is normal; it often improves over time with "
    "steady progress, hydration and strength work. Anything beyond that is worth "
    "discussing with a physician."
)


def scan(text: str) -> Tuple[bool, List[str]]:
    reasons: List[str] = []
    if _SURGICAL_RE.search(text):
        reasons.append("surgical_or_cosmetic")
    if _LAB_RE.search(text):
        reasons.append("lab_interpretation")
    return (len(reasons) > 0, reasons)


def filter_output(text: str) -> Tuple[str, List[str]]:
    """Return (safe_text, triggered_reasons).

    If a violation is detected, we redact the offending content and append a
    physician redirect rather than passing the raw model output through.
    """
    triggered, reasons = scan(text)
    if not triggered:
        return text, []

    safe = text
    if "surgical_or_cosmetic" in reasons:
        # Drop sentences that mention procedures; keep the rest.
        sentences = re.split(r"(?<=[.!?])\s+", safe)
        kept = [s for s in sentences if not _SURGICAL_RE.search(s)]
        safe = " ".join(kept).strip()
        if re.search(r"loose skin", text, re.IGNORECASE):
            safe = (safe + " " + _LOOSE_SKIN_HINT).strip()
    if "lab_interpretation" in reasons:
        sentences = re.split(r"(?<=[.!?])\s+", safe)
        kept = [s for s in sentences if not _LAB_RE.search(s)]
        safe = " ".join(kept).strip()

    safe = (safe + _REDIRECT).strip()
    return safe, reasons
