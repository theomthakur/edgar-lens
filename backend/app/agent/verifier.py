"""The part that does not trust the model. Plain code checks each claim against what the agent really saw."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from .evidence import Evidence, normalize

SCALES = {"units": 1.0, "thousands": 1e3, "millions": 1e6, "billions": 1e9, "percent": 0.01}
TOLERANCE = 0.005  # 0.5 percent, to allow for rounding in how a number is written


@dataclass
class ClaimResult:
    text: str
    type: str
    ref: str
    ok: bool
    reason: str

    def as_dict(self) -> dict:
        return asdict(self)


def verify_claim(claim: dict, evidence: Evidence) -> ClaimResult:
    kind = str(claim.get("type", ""))
    ref = str(claim.get("ref", ""))
    text = str(claim.get("text", ""))
    if kind == "number":
        actual = evidence.value_of(ref)
        if actual is None:
            return ClaimResult(text, kind, ref, False, f"'{ref}' is not a figure or calculation from this run.")
        scale = SCALES.get(str(claim.get("scale", "units")))
        if scale is None:
            return ClaimResult(text, kind, ref, False, f"Unknown scale '{claim.get('scale')}'. Use units, thousands, millions, billions or percent.")
        try:
            stated = float(claim["value"]) * scale
        except (KeyError, TypeError, ValueError):
            return ClaimResult(text, kind, ref, False, "A number claim needs a numeric 'value'.")
        denom = max(abs(actual), 1e-12)
        if abs(stated - actual) / denom <= TOLERANCE:
            return ClaimResult(text, kind, ref, True, "Matches the retrieved figure.")
        return ClaimResult(text, kind, ref, False, f"You stated {stated:,.6g} but {ref} is {actual:,.6g}.")
    if kind == "quote":
        source = evidence.texts.get(ref)
        quote = str(claim.get("quote", ""))
        if source is None:
            return ClaimResult(text, kind, ref, False, f"'{ref}' is not filing text you were shown in this run.")
        if len(normalize(quote)) < 12:
            return ClaimResult(text, kind, ref, False, "A quote must be at least a short phrase, copied exactly.")
        if normalize(quote) in normalize(source):
            return ClaimResult(text, kind, ref, True, "The quote appears word for word in the text you were shown.")
        return ClaimResult(text, kind, ref, False, "That quote does not appear word for word in the text you were shown.")
    return ClaimResult(text, kind, ref, False, "A claim must be type 'number' or 'quote'.")


_NUMBER = re.compile(r"\$?\s?(\d[\d,]*\.?\d*)\s?(billion|million|thousand|bn|m|k|%|percent)?", re.IGNORECASE)
_WORD_SCALE = {"billion": 1e9, "bn": 1e9, "million": 1e6, "m": 1e6, "thousand": 1e3, "k": 1e3, "%": 0.01, "percent": 0.01}


def uncovered_numbers(answer: str, verified: list[dict]) -> list[str]:
    """Numbers written in the answer text that no verified claim accounts for. A warning, not a failure."""
    covered = []
    for claim in verified:
        try:
            covered.append(float(claim["value"]) * SCALES.get(str(claim.get("scale", "units")), 1.0))
        except (KeyError, TypeError, ValueError):
            continue
    missing = []
    for match in _NUMBER.finditer(answer):
        raw, unit = match.group(1), (match.group(2) or "").lower()
        try:
            number = float(raw.replace(",", ""))
        except ValueError:
            continue
        if not unit and (1900 <= number <= 2100 or number < 10):
            continue  # years and small counts
        candidates = [number * _WORD_SCALE[unit]] if unit else [number]
        if not any(abs(c - cov) / max(abs(cov), 1e-12) <= 0.01 for c in candidates for cov in covered):
            missing.append(match.group(0).strip())
    return missing
