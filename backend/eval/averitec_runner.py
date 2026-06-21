"""AVeriTeC evaluation runner — the scoreboard.

Usage (from the backend dir, with the venv python):
  python eval/averitec_runner.py --split dev --n 40 --track gold
  python eval/averitec_runner.py --split dev --n 20 --track live
  python eval/averitec_runner.py --split dev --n 0  --track both   # 0 = all 500

Tracks:
  gold  — Track A: reason over AVeriTeC's gold evidence (isolates reasoning).
  live  — Track B: full analyze->retrieve->verify pipeline on the bare claim.
  both  — run gold then live on the same subset.

Writes a human-readable report and a JSON dump to eval/reports/. Every Gemma
call is disk-cached, so re-running after a code change only pays for the claims
whose prompts actually changed.
"""
from __future__ import annotations
import os
import sys
import json
import argparse
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
for p in (_HERE, _BACKEND):
    if p not in sys.path:
        sys.path.insert(0, p)

# Throttle real Gemma calls to stay under 15 RPM for the whole run.
os.environ.setdefault("VIVEKA_RPM_THROTTLE", "4.3")

import predict       # noqa: E402
import metrics       # noqa: E402
import llm_cache     # noqa: E402
from mapping import normalise_label  # noqa: E402

DATA_DIR = os.path.join(_HERE, "data")
REPORTS_DIR = os.path.join(_HERE, "reports")


def load_split(split: str) -> list[dict]:
    with open(os.path.join(DATA_DIR, f"{split}.json"), encoding="utf-8") as f:
        return json.load(f)


def stratified_subset(data: list[dict], n: int) -> list[dict]:
    """Deterministic, label-balanced subset: round-robin across labels in
    dataset order. Guarantees every label appears even for small n; with n=0
    returns everything."""
    if n <= 0 or n >= len(data):
        return data
    buckets: dict[str, list[dict]] = defaultdict(list)
    for e in data:
        buckets[normalise_label(e.get("label"))].append(e)
    order = sorted(buckets, key=lambda k: -len(buckets[k]))  # biggest class first
    picked, i = [], 0
    while len(picked) < n:
        progressed = False
        for k in order:
            if i < len(buckets[k]):
                picked.append(buckets[k][i])
                progressed = True
                if len(picked) >= n:
                    break
        if not progressed:
            break
        i += 1
    return picked


def _predict_one(track: str, e: dict, opts: dict) -> dict:
    claim = e.get("claim", "")
    fm, likert, fulldoc, hyde = opts["fewshot"], opts["likert"], opts["fulldoc"], opts["hyde"]
    if track == "gold":
        return predict.predict_gold(e, fewshot_mode=fm, likert=likert, samples=opts.get("samples", 1))
    if track == "golddebate":
        return predict.predict_gold_debate(e)
    if track == "agentic":
        return predict.predict_agentic(claim, fewshot_mode=fm, likert=likert, fulldoc=fulldoc, hyde=hyde)
    if track == "debate":
        return predict.predict_debate(claim)
    return predict.predict_live(claim)


def _print_row(j: int, total: int, track: str, gold: str, out: dict, claim: str) -> None:
    flag = "ok " if out["pred"] == gold else "MISS"
    if track == "live":
        extra = f" src={out.get('n_sources')}"
    elif track == "agentic":
        extra = f" hops={out.get('hops')} src={out.get('n_sources')}"
    elif track == "debate":
        extra = f" hops={out.get('hops')} src={out.get('n_sources')} split={out.get('split')}"
    elif track == "golddebate":
        extra = f" split={out.get('split')}"
    else:
        extra = ""
    print(f"  [{j:>3}/{total}] {flag}  gold={gold[:9]:<9} pred={out['pred'][:9]:<9}"
          f" conf={out.get('confidence',0):>3}{extra}  {claim[:60]}")
    sys.stdout.flush()


def run_track(track: str, subset: list[dict], opts: dict, workers: int = 1) -> dict:
    total = len(subset)
    results: list[dict | None] = [None] * total
    if workers <= 1:
        for i, e in enumerate(subset):
            out = _predict_one(track, e, opts)
            results[i] = out
            _print_row(i + 1, total, track, normalise_label(e.get("label")), out, e.get("claim", ""))
    else:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_predict_one, track, e, opts): i for i, e in enumerate(subset)}
            done = 0
            for fut in as_completed(futs):
                i = futs[fut]
                out = fut.result()
                results[i] = out
                done += 1
                _print_row(done, total, track, normalise_label(subset[i].get("label")),
                           out, subset[i].get("claim", ""))
    pairs, rows = [], []
    for i, e in enumerate(subset):
        gold = normalise_label(e.get("label"))
        out = results[i]
        pairs.append((gold, out["pred"]))
        rows.append({"claim": e.get("claim", "")[:160], "gold": gold, **out})
    s = metrics.score(pairs)
    s["_rows"] = rows
    return s


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="dev")
    ap.add_argument("--n", type=int, default=40, help="subset size (0 = all)")
    ap.add_argument("--track", choices=["gold", "golddebate", "live", "agentic", "debate", "both"], default="gold")
    ap.add_argument("--tag", default="", help="label for the report filename")
    ap.add_argument("--fewshot", choices=["none", "static", "dynamic"], default="none",
                    help="P3: few-shot exemplars (dynamic = BM25 nearest train claims)")
    ap.add_argument("--likert", action="store_true", help="P2: Likert-softmax decision")
    ap.add_argument("--fulldoc", action="store_true", help="P1: read full articles (agentic track)")
    ap.add_argument("--hyde", action="store_true", help="P5: HyDE conflict-aware query expansion (agentic track)")
    ap.add_argument("--samples", type=int, default=1, help="self-consistency: average N Likert samples (gold+likert)")
    ap.add_argument("--workers", type=int, default=4,
                    help="concurrent predictors (Gemma starts stay rate-limited; latencies overlap)")
    args = ap.parse_args()

    data = load_split(args.split)
    subset = stratified_subset(data, args.n)
    print(f"AVeriTeC {args.split}: scoring {len(subset)}/{len(data)} claims  track={args.track}")
    print(f"model={__import__('config').GEMINI_MODEL}  throttle={os.environ.get('VIVEKA_RPM_THROTTLE')}s/call\n")

    opts = {"fewshot": args.fewshot, "likert": args.likert, "fulldoc": args.fulldoc,
            "hyde": args.hyde, "samples": args.samples}
    cfg = "".join([f"+{args.fewshot}fs" if args.fewshot != "none" else "",
                   "+likert" if args.likert else "", "+fulldoc" if args.fulldoc else "",
                   "+hyde" if args.hyde else "", f"+sc{args.samples}" if args.samples > 1 else ""])
    tracks = ["gold", "live"] if args.track == "both" else [args.track]
    report = {"split": args.split, "n": len(subset), "opts": opts, "tracks": {}}
    text_blocks = []
    for t in tracks:
        print(f"--- Track {t.upper()}{cfg} (workers={args.workers}) ---")
        llm_cache.reset_stats()
        s = run_track(t, subset, opts, workers=args.workers)
        report["tracks"][t] = s
        desc = {"gold": "gold-evidence reasoning", "live": "live single-hop baseline",
                "golddebate": "gold-evidence + 3-lens debate panel",
                "agentic": "live bounded agentic multi-hop",
                "debate": "agentic + 3-lens debate panel"}.get(t, t)
        title = f"Track {t.upper()} ({desc})"
        block = metrics.format_report(s, title)
        block += (f"\n  cache: {llm_cache.STATS['hits']} hits, "
                  f"{llm_cache.STATS['misses']} API calls, {llm_cache.STATS['errors']} errors")
        if t == "live":
            abst = sum(1 for r in s["_rows"] if r.get("abstained"))
            block += f"\n  product-mode would have abstained on {abst}/{s['n']} ({abst/max(1,s['n']):.0%})"
        if t in ("agentic", "debate"):
            avg_hops = sum(r.get("hops", 0) for r in s["_rows"]) / max(1, s["n"])
            avg_src = sum(r.get("n_sources", 0) for r in s["_rows"]) / max(1, s["n"])
            block += f"\n  avg hops={avg_hops:.1f}  avg sources={avg_src:.1f}"
        if t in ("debate", "golddebate"):
            splits = [r for r in s["_rows"] if r.get("split")]
            if splits:
                sp_acc = sum(1 for r in splits if r["pred"] == r["gold"]) / len(splits)
                sp_conf = sum(1 for r in splits if r["gold"].startswith("Conflicting")) / len(splits)
                block += (f"\n  panel split on {len(splits)}/{s['n']} claims "
                          f"(acc on splits {sp_acc:.0%}; {sp_conf:.0%} of splits were truly Conflicting)")
        text_blocks.append(block)
        print("\n" + block + "\n")

    os.makedirs(REPORTS_DIR, exist_ok=True)
    tag = (args.tag + "_") if args.tag else ""
    base = f"{tag}{args.split}_n{len(subset)}_{args.track}{cfg.replace('+', '_')}"
    with open(os.path.join(REPORTS_DIR, base + ".json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    summary = f"AVeriTeC {args.split} — {len(subset)} claims\n\n" + "\n\n".join(text_blocks) + "\n"
    with open(os.path.join(REPORTS_DIR, base + ".txt"), "w", encoding="utf-8") as f:
        f.write(summary)
    print(f"\nReport written: eval/reports/{base}.txt (+ .json)")


if __name__ == "__main__":
    main()
