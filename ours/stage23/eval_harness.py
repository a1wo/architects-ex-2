"""
STAGE 2/3 evaluation harness — the competition proxy. Everything Stage 1
measures (relevance, hallucination, citations, latency — reused from
ours/stage1/eval_harness.py, same pinned judge) PLUS judged conversational
quality, then the composite competition score from score.py:

    score = 65*R + 15*C + 10*E + 10*Q

This is what we grade our RAG (Stage 2) and agent system (Stage 3) with,
because it mirrors the official final rubric.

    python ours/stage23/eval_harness.py ours/results/<run>.jsonl --out ours/results/<run>
"""
import importlib.util
import sys
from pathlib import Path

def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

_HERE = Path(__file__).resolve().parent
stage1 = _load("stage1_eval_harness", _HERE.parent / "stage1" / "eval_harness.py")
score = _load("stage23_score", _HERE / "score.py")

CONVERSATIONAL_PROMPT = """You are rating the conversational quality of a customer-support reply from an insurance company, NOT its factual correctness.

Customer question (Hebrew): {question}

Support reply: {answer}

Rate ONLY clarity, tone, and flow on a 1-5 scale:
5 = clear, warm, well-structured, right length, same language as the question, directly addresses the customer
4 = good but minor issues (slightly too long/short, small structure problems)
3 = understandable but flawed (wall of text, robotic tone, poor structure, hedging clutter)
2 = hard to follow, wrong register, ignores the customer's framing, or partially wrong language
1 = confusing, rude, wrong language entirely, or doesn't engage with the question

A polite, clear refusal can still score 4-5. A correct but unreadable answer scores low.

Reply with ONLY a JSON object, no prose, no code fences:
{{"score": 1 | 2 | 3 | 4 | 5, "reason": "<one short sentence>"}}"""


def score_one(q, ans, corpus):
    """Stage-1's four metrics + the conversational judge."""
    v = stage1.score_one(q, ans, corpus)
    v["conversational"] = stage1.judge(
        CONVERSATIONAL_PROMPT.format(question=q["question"], answer=ans.get("answer", "")))
    return v


if __name__ == "__main__":
    args = stage1.make_argparser().parse_args()
    stage1.evaluate(args.answers, args.questions, args.corpus, args.out,
                    score_fn=score_one, harness="stage23")
    if args.out and Path(args.out).is_dir():          # folder-per-run layout
        mpath = Path(args.out) / "metrics.json"
    elif not args.out and Path(args.answers).name == "answers.jsonl":
        mpath = Path(args.answers).parent / "metrics.json"
    else:                                             # legacy prefix layout
        mpath = Path(f"{args.out or Path(args.answers).stem}_metrics.json")
    print("\ncomposite competition score:")
    s = score.compute(mpath)
    print(f"  R {s['R']:.3f} | C {s['C']:.3f} | E {s['E']:.3f} | Q {s['Q']:.3f} ({s['q_source']})"
          f"  ->  TOTAL {s['total']:.1f}/100")
