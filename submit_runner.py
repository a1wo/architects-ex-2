"""
Submission runner: asks YOUR running /ask endpoint every question in a file
and writes one answers JSONL -- the file you submit for final grading.

    uvicorn your_app:app --port 8000        # your system, running locally
    python submit_runner.py --questions blind_questions.json \
        --endpoint http://localhost:8000 --out submission_<team>.jsonl

Also handy during development for batch runs over the dev set. Latency is
measured here, client-side; it is part of your grade, so run on a quiet
machine. Resumes: already-answered ids are skipped on rerun.
"""
import argparse
import json
import os
import sys
import time

import requests


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True)
    ap.add_argument("--endpoint", default="http://localhost:8000")
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeout", type=float, default=90)
    args = ap.parse_args()

    questions = json.load(open(args.questions, encoding="utf-8"))
    if isinstance(questions, dict):
        questions = questions["questions"]

    done = set()
    if os.path.exists(args.out):
        done = {json.loads(l)["id"] for l in open(args.out, encoding="utf-8") if l.strip()}
        print(f"resuming: {len(done)} already answered")

    url = f"{args.endpoint.rstrip('/')}/ask"
    with open(args.out, "a", encoding="utf-8") as out:
        for q in questions:
            if q["id"] in done:
                continue
            t0 = time.time()
            try:
                r = requests.post(url, json={"question": q["question"]}, timeout=args.timeout)
                r.raise_for_status()
                rec = r.json()
            except requests.RequestException as e:
                # your system failing on a question IS part of the measurement;
                # recorded as an empty answer so the run keeps going
                print(f"  [ENDPOINT FAILED on {q['id']}: {e}]", file=sys.stderr)
                rec = {"answer": "", "citations": [], "endpoint_error": str(e)}
            # latency is measured HERE, end-to-end; a self-reported value
            # from the endpoint does not count
            rec["latency_ms"] = (time.time() - t0) * 1000
            rec["id"] = q["id"]
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            out.flush()
            print(f"  {q['id']} ({rec['latency_ms']:.0f} ms)")
    print(f"\nwrote {args.out} -- this is the file you submit")


if __name__ == "__main__":
    main()
