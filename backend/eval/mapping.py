"""The AVeriTeC label space and the mapping to/from Viveka's product verdicts.

AVeriTeC uses four labels. Viveka's product taxonomy is five (it adds an
explicit "not a factual claim" and routes uncertainty to a human). For
benchmark scoring we collapse the product verdict onto the AVeriTeC label the
two modes share a reasoning core; only the final decision policy differs.
"""
from __future__ import annotations

# Canonical AVeriTeC labels (exact strings used in the dataset).
SUPPORTED = "Supported"
REFUTED = "Refuted"
CONFLICTING = "Conflicting Evidence/Cherrypicking"
NEI = "Not Enough Evidence"
AVERITEC_LABELS = [SUPPORTED, REFUTED, CONFLICTING, NEI]

# Short keys the model is asked to emit (less brittle than the long strings).
_KEY_TO_LABEL = {
    "supported": SUPPORTED,
    "refuted": REFUTED,
    "conflicting": CONFLICTING,
    "cherrypicking": CONFLICTING,
    "conflicting evidence/cherrypicking": CONFLICTING,
    "not enough evidence": NEI,
    "nei": NEI,
    "unverified": NEI,
}

# Viveka product verdict -> AVeriTeC label (benchmark scoring).
PRODUCT_TO_AVERITEC = {
    "true": SUPPORTED,
    "false": REFUTED,
    "misleading": CONFLICTING,
    "human": NEI,       # product abstains; in benchmark mode this is minimised
    "opinion": NEI,     # AVeriTeC claims are all checkable, so this is effectively N/A
}


def normalise_label(raw: str) -> str:
    """Map a model's free-text label guess to a canonical AVeriTeC label.
    Unknown/empty -> Not Enough Evidence (the safe, non-committal bucket)."""
    if not raw:
        return NEI
    s = str(raw).strip().lower()
    if s in _KEY_TO_LABEL:
        return _KEY_TO_LABEL[s]
    for key, lab in _KEY_TO_LABEL.items():
        if key in s:
            return lab
    return NEI


def product_to_averitec(verdict: str) -> str:
    return PRODUCT_TO_AVERITEC.get(str(verdict).strip().lower(), NEI)
