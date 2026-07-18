"""
Show concrete examples behind any metric of any run — so a number in the table
can always be traced to real question/answer/verdict triples.

    python ours/show_examples.py base_default hallucination
    python ours/show_examples.py base_strict refusal -n 5
    python ours/show_examples.py base_cite correct
    python ours/show_examples.py bare_cited_glm52 citations      # citation verdicts incl. invalid
    python ours/show_examples.py base_default conversational     # lowest-rated answers

Metrics: correct | partial | incorrect | refusal | hallucination | citations | conversational
Run name = any <name> that has ours/results/<name>.jsonl + <name>_verdicts.jsonl.
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "ours" / "results"


def load(name):
    qs = {q["id"]: q for q in json.load(open(ROOT / "reference_questions.json", encoding="utf-8"))}
    ans = {r["id"]: r for r in map(json.loads, open(RESULTS / f"{name}.jsonl", encoding="utf-8"))}
    ver = {v["id"]: v for v in map(json.loads, open(RESULTS / f"{name}_verdicts.jsonl", encoding="utf-8"))}
    return qs, ans, ver


def block(qid, q, a, extra):
    print("=" * 78)
    print(f"[{qid}]  {q['question'][:160]}")
    print(f"  GROUND TRUTH: {q['ground_truth_answer'][:200]}")
    print(f"  ANSWER:       {a['answer'][:300]}".replace("\n", " "))
    print(f"  {extra}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", help="e.g. base_default")
    ap.add_argument("metric", choices=["correct", "partial", "incorrect", "refusal",
                                       "hallucination", "citations", "conversational"])
    ap.add_argument("-n", type=int, default=3)
    args = ap.parse_args()

    qs, ans, ver = load(args.run)
    shown = 0
    for qid, v in ver.items():
        if shown >= args.n:
            break
        rel = v.get("relevance", {})
        if args.metric == "hallucination":
            hit = rel.get("verdict") == "incorrect" and rel.get("confident")
        elif args.metric in ("correct", "partial", "incorrect", "refusal"):
            hit = rel.get("verdict") == args.metric
        elif args.metric == "citations":
            hit = bool(v.get("citations"))
        else:  # conversational: lowest scores first
            hit = isinstance(v.get("conversational", {}).get("score"), (int, float)) \
                  and v["conversational"]["score"] <= 3
        if not hit:
            continue
        shown += 1
        if args.metric == "citations":
            extra = "CITATIONS: " + json.dumps(v["citations"], ensure_ascii=False)[:400]
        elif args.metric == "conversational":
            c = v["conversational"]
            extra = f"CONVERSATIONAL: {c['score']}/5 — {c.get('reason','')}"
        else:
            extra = f"JUDGE: {rel.get('verdict')} (confident={rel.get('confident')}) — {rel.get('reason','')}"
        block(qid, qs[qid], ans[qid], extra)
    print("=" * 78)
    print(f"{shown} example(s) of '{args.metric}' in run '{args.run}' "
          f"(full data: ours/results/{args.run}_verdicts.jsonl)")


if __name__ == "__main__":
    main()
