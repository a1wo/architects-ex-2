"""Batch-run the dev questions through the playground /api/chat endpoint with
explicit strategy params (k, temperature, reasoning, db, model...) — for
parameter sweeps the fixed /ask contract can't express. Output is the same
answers.jsonl shape the stage23 harness scores (latency measured here,
client-side, like submit_runner).

    .venv/bin/python ours/stage2/batch_run.py --out ours/results/<run>/answers.jsonl \
        --params '{"k": 16}' [--strategy topk-context-stuffing] [--db NAME] [--model M]

Resumes: already-answered ids are skipped on rerun.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default=str(REPO_ROOT / "reference_questions.json"))
    ap.add_argument("--endpoint", default="http://localhost:8010")
    ap.add_argument("--out", required=True)
    ap.add_argument("--strategy", default=None)
    ap.add_argument("--db", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--params", default="{}", help="JSON dict of strategy params")
    ap.add_argument("--timeout", type=float, default=1800)
    args = ap.parse_args()

    questions = json.load(open(args.questions, encoding="utf-8"))
    if isinstance(questions, dict):
        questions = questions["questions"]

    done = set()
    if os.path.exists(args.out):
        done = {json.loads(l)["id"] for l in open(args.out, encoding="utf-8") if l.strip()}
        print(f"resuming: {len(done)} already answered", flush=True)

    body_base = {k: v for k, v in [("strategy", args.strategy), ("db", args.db),
                                   ("model", args.model)] if v}
    body_base["params"] = json.loads(args.params)

    url = f"{args.endpoint.rstrip('/')}/api/chat"
    with open(args.out, "a", encoding="utf-8") as out:
        for q in questions:
            if q["id"] in done:
                continue
            t0 = time.time()
            try:
                r = requests.post(url, json={**body_base, "question": q["question"]},
                                  timeout=args.timeout)
                r.raise_for_status()
                d = r.json()
                rec = {"answer": d["answer"], "citations": d["citations"],
                       "cost_usd": d.get("cost_usd"), "domain": d.get("domain")}
            except requests.RequestException as e:
                print(f"  [FAILED on {q['id']}: {e}]", file=sys.stderr, flush=True)
                rec = {"answer": "", "citations": [], "endpoint_error": str(e)}
            rec["latency_ms"] = (time.time() - t0) * 1000
            rec["id"] = q["id"]
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            print(f"  {q['id']} ({rec['latency_ms']:.0f} ms)", flush=True)
    print(f"done: {args.out}", flush=True)


if __name__ == "__main__":
    main()
