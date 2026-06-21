"""Scoring for AVeriTeC predictions — pure Python, no sklearn.

Because dev is ~61% "Refuted", raw accuracy is a weak signal (always-Refuted
already scores 0.61). So we report macro-averaged precision/recall/F1 and the
full confusion matrix alongside accuracy, plus the AVeriTeC-style accuracy
with abstentions counted as wrong (a system that abstains everywhere must not
look good).
"""
from __future__ import annotations
from collections import defaultdict
from mapping import AVERITEC_LABELS, NEI


def score(pairs: list[tuple[str, str]]) -> dict:
    """pairs: list of (gold_label, pred_label), both canonical AVeriTeC strings."""
    n = len(pairs)
    if not n:
        return {"n": 0}
    correct = sum(1 for g, p in pairs if g == p)
    # Confusion matrix: conf[gold][pred]
    conf = {g: defaultdict(int) for g in AVERITEC_LABELS}
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)
    for g, p in pairs:
        conf.setdefault(g, defaultdict(int))[p] += 1
        if g == p:
            tp[g] += 1
        else:
            fp[p] += 1
            fn[g] += 1

    per_class = {}
    f1s = []
    for lab in AVERITEC_LABELS:
        prec = tp[lab] / (tp[lab] + fp[lab]) if (tp[lab] + fp[lab]) else 0.0
        rec = tp[lab] / (tp[lab] + fn[lab]) if (tp[lab] + fn[lab]) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        support = sum(1 for g, _ in pairs if g == lab)
        per_class[lab] = {"precision": round(prec, 4), "recall": round(rec, 4),
                          "f1": round(f1, 4), "support": support}
        f1s.append(f1)

    abstain = sum(1 for _, p in pairs if p == NEI)
    return {
        "n": n,
        "accuracy": round(correct / n, 4),
        "macro_f1": round(sum(f1s) / len(f1s), 4),
        "correct": correct,
        "abstain_rate": round(abstain / n, 4),
        "per_class": per_class,
        "confusion": {g: dict(conf[g]) for g in AVERITEC_LABELS},
    }


def format_report(s: dict, title: str = "") -> str:
    if not s.get("n"):
        return f"{title}\n  (no predictions)"
    lines = [title, f"  n={s['n']}  accuracy={s['accuracy']:.3f}  macro-F1={s['macro_f1']:.3f}"
             f"  abstain={s['abstain_rate']:.3f}"]
    lines.append("  per-class (P / R / F1 / support):")
    for lab, m in s["per_class"].items():
        lines.append(f"    {lab:<38} {m['precision']:.2f} / {m['recall']:.2f} / {m['f1']:.2f}  (n={m['support']})")
    lines.append("  confusion (gold rows -> pred cols):")
    labs = list(s["per_class"].keys())
    short = {l: l.split("/")[0][:10] for l in labs}
    header = " " * 14 + "".join(f"{short[l]:>12}" for l in labs)
    lines.append(header)
    for g in labs:
        row = "".join(f"{s['confusion'][g].get(p, 0):>12}" for p in labs)
        lines.append(f"    {short[g]:<10}{row}")
    return "\n".join(lines)
