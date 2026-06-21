"""Hindi fairness slice — does verdict quality hold when the CLAIM is in Hindi?

India-first product, so non-English accuracy is the most exploitable fairness gap.
This measures it honestly on a small balanced slice: run the shipped gold-evidence
recipe (Likert-softmax + dynamic exemplars) on the SAME claims twice, once in
English and once machine-translated to Hindi (gold evidence stays as-is), and report
the delta plus abstention. Small n; read as directional, not precise.

  cd backend && VIVEKA_RPM_THROTTLE=4.3 .venv/Scripts/python eval/hindi_slice.py --n 20
"""
from __future__ import annotations
import argparse, json, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from averitec_runner import load_split, stratified_subset  # noqa: E402
from mapping import normalise_label  # noqa: E402
import predict  # noqa: E402
from llm import complete_json  # noqa: E402

NEI = "Not Enough Evidence"


def to_hindi(claim: str) -> str:
    try:
        r = complete_json(
            "You translate text to natural Hindi (Devanagari). Output only JSON.",
            f'Translate this claim to natural Hindi. Keep names/numbers intact.\n"{claim}"\nReturn {{"hi": "<hindi>"}}',
            max_tokens=2048)
        return (r.get("hi") or "").strip() or claim
    except Exception:
        return claim


def score(rows: list[dict], key: str) -> dict:
    n = len(rows)
    correct = sum(1 for r in rows if r[f"{key}_pred"] == r["gold"])
    abstain = sum(1 for r in rows if r[f"{key}_pred"] == NEI and r["gold"] != NEI)
    return {"n": n, "accuracy": round(correct / max(1, n), 3),
            "abstain_rate": round(abstain / max(1, n), 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--n", type=int, default=20)
    args = ap.parse_args()

    data = load_split(args.split)
    subset = stratified_subset(data, args.n)
    print(f"Hindi fairness slice: {len(subset)} claims, gold-evidence recipe (likert+dynamic)")
    print(f"throttle={os.environ.get('VIVEKA_RPM_THROTTLE')}s/call\n")

    rows = []
    for i, e in enumerate(subset, 1):
        gold = normalise_label(e.get("label"))
        en = predict.predict_gold(e, fewshot_mode="dynamic", likert=True)
        hi_claim = to_hindi(e.get("claim", ""))
        e_hi = {**e, "claim": hi_claim}
        hi = predict.predict_gold(e_hi, fewshot_mode="dynamic", likert=True)
        en_pred, hi_pred = normalise_label(en.get("pred")), normalise_label(hi.get("pred"))
        rows.append({"gold": gold, "en_pred": en_pred, "hi_pred": hi_pred,
                     "en_conf": en.get("confidence"), "hi_conf": hi.get("confidence"),
                     "claim": e.get("claim", "")[:60], "hi_claim": hi_claim[:60]})
        flag = "" if en_pred == hi_pred else "  <- verdict changed"
        print(f"[{i:2}/{len(subset)}] gold={gold[:10]:10} EN={en_pred[:10]:10} HI={hi_pred[:10]:10}{flag}")

    en_s, hi_s = score(rows, "en"), score(rows, "hi")
    agree = sum(1 for r in rows if r["en_pred"] == r["hi_pred"]) / max(1, len(rows))
    out = {"n": len(rows), "english": en_s, "hindi": hi_s,
           "en_hi_agreement": round(agree, 3), "rows": rows}
    print("\n=== RESULT ===")
    print(f"English: acc={en_s['accuracy']}  abstain={en_s['abstain_rate']}")
    print(f"Hindi:   acc={hi_s['accuracy']}  abstain={hi_s['abstain_rate']}")
    print(f"EN/HI verdict agreement: {round(agree*100)}%")
    path = os.path.join(os.path.dirname(__file__), "reports", f"hindi_slice_{args.split}_n{len(rows)}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nReport written: {path}")


if __name__ == "__main__":
    main()
