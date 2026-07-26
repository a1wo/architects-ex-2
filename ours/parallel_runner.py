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
import datetime
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI

WORKERS = 12
DEFAULT_SYSTEM = ("You are a customer-support assistant for Harel Insurance (Israel). "
                  "Answer the customer's question in the language it was asked. "
                  "If you cite a source, cite the exact document and page.")


def ask(client, model, system_prompt, q):
    for attempt in range(4):
        t0 = time.time()
        try:
            resp = client.chat.completions.create(model=model, messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": q["question"]}],
                timeout=120)
            return {"id": q["id"],
                    "answer": resp.choices[0].message.content or "",  # some models return null content (empty refusal)
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
    ap.add_argument("--prompt-name", default=None,
                    help="label for config.json, e.g. default/strict/cite")
    ap.add_argument("--out", required=True,
                    help="answers path; convention: ours/results/<run>/answers.jsonl")
    args = ap.parse_args()

    client = OpenAI()  # reads OPENAI_API_KEY + OPENAI_BASE_URL from the env
    base = os.environ.get("OPENAI_BASE_URL")  # kept for the run-config record

    questions = json.load(open(args.questions, encoding="utf-8"))
    if isinstance(questions, dict):
        questions = questions["questions"]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.name == "answers.jsonl":  # folder-per-run layout: record the run's config
        prompt_name = args.prompt_name or \
            ("default" if args.system_prompt == DEFAULT_SYSTEM else "custom")
        judge_cfg = {}
        cfg_path = Path(__file__).resolve().parent / "config.json"
        if cfg_path.exists():
            judge_cfg = json.load(open(cfg_path, encoding="utf-8"))
        json.dump({"run": out_path.parent.name,
                   "answering_model": args.model,
                   "system_prompt_name": prompt_name,
                   "system_prompt": args.system_prompt,
                   "judge_model": judge_cfg.get("judge_model"),
                   "judge_temperature": judge_cfg.get("judge_temperature"),
                   "questions": args.questions,
                   "endpoint": base or "provider default",
                   "workers": WORKERS,
                   "ts": datetime.datetime.now().isoformat(timespec="seconds")},
                  open(out_path.parent / "config.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        recs = list(pool.map(lambda q: ask(client, args.model, args.system_prompt, q), questions))
    with open(args.out, "w", encoding="utf-8") as out:
        for rec in recs:  # original question order
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
    errs = sum(1 for r in recs if r["answer"].startswith("[runner error"))
    print(f"wrote {args.out}: {len(recs)} answers in {time.time()-t0:.0f}s "
          f"({WORKERS} workers{', ' + str(errs) + ' ERRORS' if errs else ''})")


if __name__ == "__main__":
    main()
