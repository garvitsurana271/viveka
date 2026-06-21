"""Calibration analysis — does stated confidence match empirical accuracy?

Reads a scored report JSON (written by averitec_runner) and bins predictions by
stated confidence, then compares each bin's confidence to its actual accuracy.
A well-calibrated system that says "90% confident" is right ~90% of the time.

Reports:
  - a reliability table (per-bin confidence vs accuracy)
  - ECE (Expected Calibration Error) — the headline calibration number
  - a suggested abstention threshold: the confidence below which accuracy drops
    under a target, so product mode knows where to route to a human.

Pure analysis — no API calls. Usage:
  python eval/calibration.py reports/baseline_dev_n100_gold.json
"""
from __future__ import annotations
import sys
import json

BINS = [(0, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 101)]


def analyse(rows: list[dict]) -> dict:
    pts = [(int(r.get("confidence", 0)), r.get("pred") == r.get("gold"))
           for r in rows if not r.get("error")]
    n = len(pts)
    if not n:
        return {"n": 0}
    bins = []
    ece = 0.0
    for lo, hi in BINS:
        grp = [c for c in pts if lo <= c[0] < hi]
        if not grp:
            continue
        acc = sum(1 for _, ok in grp if ok) / len(grp)
        avg_conf = sum(c for c, _ in grp) / len(grp) / 100.0
        ece += abs(acc - avg_conf) * len(grp) / n
        bins.append({"range": f"{lo}-{hi-1}", "count": len(grp),
                     "avg_conf": round(avg_conf, 3), "accuracy": round(acc, 3),
                     "gap": round(acc - avg_conf, 3)})
    return {"n": n, "ece": round(ece, 4), "bins": bins}


def suggest_threshold(rows: list[dict], target: float = 0.75) -> dict:
    """Lowest confidence cutoff at which kept predictions hit `target` accuracy."""
    pts = sorted(((int(r.get("confidence", 0)), r.get("pred") == r.get("gold"))
                  for r in rows if not r.get("error")), reverse=True)
    best = None
    for cut in range(100, 0, -5):
        kept = [ok for c, ok in pts if c >= cut]
        if not kept:
            continue
        acc = sum(kept) / len(kept)
        coverage = len(kept) / len(pts)
        if acc >= target:
            best = {"threshold": cut, "accuracy_at_or_above": round(acc, 3),
                    "coverage": round(coverage, 3)}
    return best or {"threshold": None, "note": f"no cutoff reaches {target} accuracy"}


def format_report(rows: list[dict], title: str = "") -> str:
    a = analyse(rows)
    if not a.get("n"):
        return f"{title}\n  (no calibratable predictions)"
    lines = [title, f"  n={a['n']}  ECE={a['ece']:.3f}  (lower is better; 0 = perfectly calibrated)"]
    lines.append("  reliability (confidence bin -> actual accuracy):")
    lines.append(f"    {'bin':<10}{'count':>7}{'avg_conf':>10}{'accuracy':>10}{'gap':>8}")
    for b in a["bins"]:
        lines.append(f"    {b['range']:<10}{b['count']:>7}{b['avg_conf']:>10.2f}"
                     f"{b['accuracy']:>10.2f}{b['gap']:>8.2f}")
    for tgt in (0.75, 0.80):
        t = suggest_threshold(rows, tgt)
        if t.get("threshold"):
            lines.append(f"  to hold >= {tgt:.0%} accuracy: keep conf >= {t['threshold']} "
                         f"(covers {t['coverage']:.0%} of claims at {t['accuracy_at_or_above']:.0%})")
        else:
            lines.append(f"  to hold >= {tgt:.0%} accuracy: {t.get('note')}")
    return "\n".join(lines)


def _rows_from_report(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        rep = json.load(f)
    rows = []
    for tname, t in rep.get("tracks", {}).items():
        for r in t.get("_rows", []):
            rows.append(r)
    return rows


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python eval/calibration.py <report.json>")
        sys.exit(1)
    rows = _rows_from_report(sys.argv[1])
    print(format_report(rows, f"Calibration — {sys.argv[1]}"))
