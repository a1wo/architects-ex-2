"""
Bare-model run that actually exercises the citation field. Unlike the given
baseline_runner.py (which hardcodes citations=[]), this asks the model to
return JSON {"answer", "citations": [{"file", "page"}]} — citing Harel
documents FROM MEMORY, since it still sees no corpus. This tests the question
"could a strong bare model cite real sources?" (expectation: no — the files it
names won't exist in the corpus, and the harness counts those as invalid).

    python ours/bare_cited_runner.py --model zai-org/GLM-5.2 \
        --out ours/results/bare_cited_glm52.jsonl
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tf_client import chat

SYSTEM = (
    "You are a customer-support assistant for Harel Insurance (Israel). Answer in the "
    "language of the question. You must ground every answer in Harel's official policy "
    "documents. Reply with ONLY a JSON object, no prose around it, no code fences:\n"
    '{"answer": "<the answer, in the question\'s language>", '
    '"citations": [{"file": "<Harel document filename>", "page": <1-based page number>}]}\n'
    "Cite the exact document(s) and page(s) that establish your answer. "
    "If you are not sure of the answer, say so in the answer field and cite nothing.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--questions", default=str(ROOT / "reference_questions.json"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    questions = json.load(open(args.questions, encoding="utf-8"))
    if isinstance(questions, dict):
        questions = questions["questions"]

    with open(args.out, "w", encoding="utf-8") as out:
        for q in questions:
            t0 = time.time()
            try:
                reply = chat([{"role": "system", "content": SYSTEM},
                              {"role": "user", "content": q["question"]}],
                             model=args.model, max_tokens=1024, temperature=0.2, quiet=True)
                m = re.search(r"\{.*\}", reply, re.DOTALL)
                parsed = json.loads(m.group(0)) if m else {"answer": reply, "citations": []}
            except Exception as e:
                parsed = {"answer": f"[runner error: {e}]", "citations": []}
            cites = [c for c in (parsed.get("citations") or [])
                     if isinstance(c, dict) and c.get("file")]
            rec = {"id": q["id"], "answer": str(parsed.get("answer", "")),
                   "citations": cites,
                   "latency_ms": (time.time() - t0) * 1000,
                   "tokens": {"prompt": 0, "completion": 0}}  # tf_client hides usage; cost negligible
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            print(f"{q['id']}: {len(cites)} citations, {rec['latency_ms']:.0f} ms", flush=True)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
