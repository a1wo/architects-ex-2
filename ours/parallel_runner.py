"""
Parallel drop-in for the (sequential) given baseline_runner.py: answers all dev
questions concurrently, same output schema, ~20x faster wall-clock.

    python ours/parallel_runner.py --model deepseek-ai/DeepSeek-V4-Pro \
        --out ours/results/base_default.jsonl
    python ours/parallel_runner.py --model ... --system-prompt "..." --out ...

Per-call retries with backoff (shared TF endpoint drops/throttles under load);
per-question latency is still the single-call wall time, so latency metrics
stay comparable with sequential runs.
"""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import litellm

WORKERS = 12
DEFAULT_SYSTEM = ("You are a customer-support assistant for Harel Insurance (Israel). "
                  "Answer the customer's question in the language it was asked. "
                  "If you cite a source, cite the exact document and page.")


def ask(model, kwargs, system_prompt, q):
    for attempt in range(4):
        t0 = time.time()
        try:
            resp = litellm.completion(model=model, messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": q["question"]}],
                timeout=120, **kwargs)
            return {"id": q["id"],
                    "answer": resp.choices[0].message.content,
                    "citations": [],  # bare model has no documents -- that's the point
                    "latency_ms": (time.time() - t0) * 1000,
                    "tokens": {"prompt": resp.usage.prompt_tokens,
                               "completion": resp.usage.completion_tokens}}
        except Exception as e:
            if attempt == 3:
                return {"id": q["id"], "answer": f"[runner error: {e}]", "citations": [],
                        "latency_ms": (time.time() - t0) * 1000,
                        "tokens": {"prompt": 0, "completion": 0}}
            time.sleep(2 ** attempt * 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="reference_questions.json")
    ap.add_argument("--model", required=True)
    ap.add_argument("--system-prompt", default=DEFAULT_SYSTEM)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    model, kwargs = args.model, {}
    base = os.environ.get("OPENAI_BASE_URL")
    if base:  # same routing rule as the given baseline_runner.py
        kwargs["api_base"] = base
        model = f"openai/{model.removeprefix('openai/')}"

    questions = json.load(open(args.questions, encoding="utf-8"))
    if isinstance(questions, dict):
        questions = questions["questions"]

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        recs = list(pool.map(lambda q: ask(model, kwargs, args.system_prompt, q), questions))
    with open(args.out, "w", encoding="utf-8") as out:
        for rec in recs:  # original question order
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    errs = sum(1 for r in recs if r["answer"].startswith("[runner error"))
    print(f"wrote {args.out}: {len(recs)} answers in {time.time()-t0:.0f}s "
          f"({WORKERS} workers{', ' + str(errs) + ' ERRORS' if errs else ''})")


if __name__ == "__main__":
    main()
