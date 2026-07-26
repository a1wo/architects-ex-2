"""Retrieval-only k sweep: does the ground-truth source appear in the top-k
retrieved paragraph chunks? No LLM calls — pure embedding + Chroma, so it's
free and measures the retrieval ceiling: if the right page isn't in the
context, no prompt can save the answer.

A question's ground_truth_sources is a list of required source groups, each
satisfied by any of its any_of options. We report per k:
  file hit   — some group satisfied at file level
  page hit   — some group satisfied at file+page level
  full cover — ALL groups satisfied (file+page), i.e. everything needed is in context

    ours/stage2/parser_bench/.venv-docling/bin/python ours/stage2/retrieval_sweep.py [--kmax 10] [--db NAME]
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kmax", type=int, default=10)
    ap.add_argument("--db", default=None)
    args = ap.parse_args()

    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from strategies.retrieval import DEFAULT_DB, retrieve
    db = args.db or DEFAULT_DB

    questions = json.load(open(REPO_ROOT / "reference_questions.json"))
    if isinstance(questions, dict):
        questions = questions["questions"]

    per_q = []
    for q in questions:
        ctxs = retrieve(q["question"], db=db, k=args.kmax)
        groups = [g["any_of"] for g in q["ground_truth_sources"]]
        # for each group: first rank (1-based) satisfying it at file / page level
        first_file, first_page = [], []
        for opts in groups:
            f_rank = p_rank = None
            for rank, c in enumerate(ctxs, 1):
                for o in opts:
                    if c.file == o["file"]:
                        f_rank = min(f_rank or rank, rank)
                        if c.page == o.get("page"):
                            p_rank = min(p_rank or rank, rank)
            first_file.append(f_rank)
            first_page.append(p_rank)
        per_q.append({"id": q["id"], "difficulty": q["difficulty"],
                      "first_file": first_file, "first_page": first_page})
        print(".", end="", flush=True)
    print()

    n = len(per_q)
    print(f"\ndb={db}  collection=harel_paragraphs  n={n} questions\n")
    print(f"{'k':>2} | {'file hit':>8} | {'page hit':>8} | {'full cover':>10}")
    print("-" * 40)
    rows = []
    for k in range(1, args.kmax + 1):
        fh = sum(any(r and r <= k for r in q["first_file"]) for q in per_q)
        ph = sum(any(r and r <= k for r in q["first_page"]) for q in per_q)
        fc = sum(all(r and r <= k for r in q["first_page"]) for q in per_q)
        rows.append({"k": k, "file_hit": fh / n, "page_hit": ph / n,
                     "full_cover": fc / n})
        print(f"{k:>2} | {fh:>3}/{n} {fh/n:>4.0%} | {ph:>3}/{n} {ph/n:>4.0%} | "
              f"{fc:>3}/{n} {fc/n:>6.0%}")

    print("\nby difficulty (page hit @ k):")
    by_diff = defaultdict(list)
    for q in per_q:
        by_diff[q["difficulty"]].append(q)
    ks = [1, 3, 5, 8, 10]
    print(f"{'':>8} | " + " | ".join(f"k={k:<2}" for k in ks if k <= args.kmax))
    for diff in ["easy", "medium", "hard"]:
        qs = by_diff[diff]
        cells = []
        for k in ks:
            if k > args.kmax:
                continue
            h = sum(any(r and r <= k for r in q["first_page"]) for q in qs)
            cells.append(f"{h/len(qs):>4.0%}")
        print(f"{diff:>8} | " + " | ".join(cells))

    misses = [q["id"] for q in per_q
              if not any(r for r in q["first_file"])]
    if misses:
        print(f"\nnever hit at file level even @ k={args.kmax}: {misses}")

    out = Path(__file__).parent / f"retrieval_sweep__{db}.json"
    out.write_text(json.dumps({"db": db, "kmax": args.kmax, "rows": rows,
                               "per_question": per_q}, ensure_ascii=False, indent=1))
    print(f"\nwrote {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
