"""
Composite competition-score calculator — our proxy of the official rubric:

    score = 65*R + 15*C + 10*E + 10*Q          (+5 voice, +5 UI, added manually)

    R relevance    = (correct + 0.5*partial) / questions      [eval_harness judge]
    C citations    = (full + 0.5*partial) / judged, 0 if none  [eval_harness judge]
    E efficiency   = 0.5*latency + 0.5*cost
                     latency: 1.0 at p50<=2s -> 0.0 at 20s (linear)
                     cost:    1.0 at <=$0.001/q -> 0.0 at $0.01/q (linear, TF est $0.5/$2 per M)
    Q conversational = NOT judged yet; pass --q (default 0.70; use 0.30 for refuse-heavy runs).
                     TODO Stage 2: add an LLM-judged Q and delete the flag.

Usage:  python ours/score.py ours/results/base_cite_metrics.json [--q 0.7]
The answers .jsonl (same prefix, without _metrics.json) is read for token counts.
"""
import argparse
import json
from pathlib import Path

PRICE_IN, PRICE_OUT = 0.5, 2.0  # $/M tokens, same estimate as tf_client.py


def clamp01(x):
    return max(0.0, min(1.0, x))


def compute(metrics_path, q_assumed=0.70):
    """Returns the full score breakdown as a dict (also used by log_run.py)."""
    m = json.load(open(metrics_path, encoding="utf-8"))
    r, c, lat = m["relevance"], m["citations"], m["latency_ms"]

    R = r["correct"] + 0.5 * r["partial"]
    C = (c["full"] + 0.5 * c["partial"]) / c["judged"] if c["judged"] else 0.0

    answers_file = Path(str(metrics_path).replace("_metrics.json", ".jsonl"))
    cost_q = None
    if answers_file.exists():
        recs = [json.loads(l) for l in open(answers_file, encoding="utf-8")]
        cost_q = sum(a["tokens"]["prompt"] * PRICE_IN + a["tokens"]["completion"] * PRICE_OUT
                     for a in recs) / 1e6 / len(recs)
    lat_score = clamp01(1 - (lat["p50"] / 1000 - 2) / 18)
    cost_score = clamp01(1 - (cost_q - 0.001) / 0.009) if cost_q is not None else 0.5
    E = 0.5 * lat_score + 0.5 * cost_score
    q_judged = m.get("conversational", {}).get("Q")
    Q, q_src = (q_judged, "judged") if q_judged is not None else (q_assumed, "ASSUMED")

    return {"R": R, "C": C, "E": E, "Q": Q, "q_source": q_src,
            "latency_p50_ms": lat["p50"], "cost_per_q_usd": cost_q,
            "total": 65 * R + 15 * C + 10 * E + 10 * Q}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metrics", help="..._metrics.json from eval_harness.py")
    ap.add_argument("--q", type=float, default=0.70,
                    help="conversational-quality assumption for pre-Q-judge metrics files")
    args = ap.parse_args()
    s = compute(args.metrics, args.q)
    print(f"R relevance     {s['R']:.3f}  -> {65*s['R']:5.1f} / 65")
    print(f"C citations     {s['C']:.3f}  -> {15*s['C']:5.1f} / 15")
    print(f"E efficiency    {s['E']:.3f}  -> {10*s['E']:5.1f} / 10   (p50 {s['latency_p50_ms']:.0f} ms, $/q {s['cost_per_q_usd']})")
    print(f"Q conversational{s['Q']:7.3f}  -> {10*s['Q']:5.1f} / 10   ({s['q_source']})")
    print(f"TOTAL           {s['total']:5.1f} / 100")


if __name__ == "__main__":
    main()
