"""Build the leaderboard / ablation table from all scored reports.

Reads every reports/*.json and emits one markdown table comparing methods on
accuracy, macro-F1, and per-class F1 — the "results section" of the submission.
Sorted by macro-F1 (the honest headline, since dev is 61% Refuted and raw
accuracy flatters a lazy classifier).

Usage:  python eval/compare.py            # all reports
        python eval/compare.py --md results.md
"""
from __future__ import annotations
import os
import sys
import json
import glob
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from mapping import AVERITEC_LABELS  # noqa: E402

REPORTS_DIR = os.path.join(_HERE, "reports")
_SHORT = {"Supported": "Sup", "Refuted": "Ref",
          "Conflicting Evidence/Cherrypicking": "Conf", "Not Enough Evidence": "NEI"}


def _collect(min_n: int = 20) -> list[dict]:
    rows = []
    for path in sorted(glob.glob(os.path.join(REPORTS_DIR, "*.json"))):
        try:
            rep = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        name = os.path.basename(path)[:-5]
        if "smoke" in name:
            continue
        for tname, t in rep.get("tracks", {}).items():
            if not t.get("n") or t["n"] < min_n:
                continue
            method = f"{tname}{'+fewshot' if 'fewshot' in name else ''}"
            pc = t.get("per_class", {})
            rows.append({
                "method": method, "file": name, "n": t["n"],
                "accuracy": t.get("accuracy", 0), "macro_f1": t.get("macro_f1", 0),
                "abstain": t.get("abstain_rate", 0),
                "f1": {lab: pc.get(lab, {}).get("f1", 0) for lab in AVERITEC_LABELS},
            })
    # Dedup by (method, n): keep the most recent file's numbers.
    seen = {}
    for r in rows:
        seen[(r["method"], r["n"])] = r
    return sorted(seen.values(), key=lambda r: r["macro_f1"], reverse=True)


def to_markdown(rows: list[dict]) -> str:
    if not rows:
        return "_no reports found_"
    head = ["Method", "n", "Acc", "MacroF1"] + [_SHORT[l] + "·F1" for l in AVERITEC_LABELS] + ["Abst"]
    lines = ["| " + " | ".join(head) + " |",
             "|" + "|".join(["---"] * len(head)) + "|"]
    for r in rows:
        cells = [r["method"], str(r["n"]), f"{r['accuracy']:.3f}", f"**{r['macro_f1']:.3f}**"]
        cells += [f"{r['f1'][l]:.2f}" for l in AVERITEC_LABELS]
        cells += [f"{r['abstain']:.2f}"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", default="", help="also write the table to this path")
    args = ap.parse_args()
    rows = _collect()
    table = to_markdown(rows)
    print("AVeriTeC dev — method comparison (sorted by macro-F1)\n")
    print(table)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write("# Viveka — AVeriTeC dev results\n\n" + table + "\n")
        print(f"\nwritten: {args.md}")


if __name__ == "__main__":
    main()
