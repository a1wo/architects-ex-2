"""
Experiment ledger. Every scored run gets ONE record: what ran (config snapshot,
model, git commit), WHY it ran (your hypothesis, --why), and what came out
(metrics + score). Append-only in ours/experiments.jsonl; the per-evaluation
pages ours/results/STAGE1.md + STAGE23.md are regenerated from it (latest
record per run name wins) via compare_runs.py.

    python ours/log_run.py ours/results/base_cite/metrics.json \
        --model deepseek-ai/DeepSeek-V4-Pro --role baseline \
        --why "does forcing citations change the failure profile?"

Re-logging the same name appends a new revision; the tables show the latest.
"""
import argparse
import datetime
import json
import subprocess
from pathlib import Path

import sys as _sys; from pathlib import Path as _P; _sys.path.insert(0, str(_P(__file__).resolve().parent / "stage23")); import score

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "ours" / "experiments.jsonl"


def load_ledger():
    if not LEDGER.exists():
        return []
    return [json.loads(l) for l in open(LEDGER, encoding="utf-8")]


def regenerate_pages():
    """One markdown per evaluation type (results/STAGE1.md, STAGE23.md) via compare_runs."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "compare_runs", Path(__file__).resolve().parent / "compare_runs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.generate()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("metrics")
    ap.add_argument("--why", required=True, help="hypothesis / reason this run exists")
    ap.add_argument("--model", required=True)
    ap.add_argument("--role", default="test", help="baseline | test | rag | ...")
    ap.add_argument("--name", default=None, help="defaults to metrics filename stem")
    ap.add_argument("--q", type=float, default=0.70)
    args = ap.parse_args()

    mpath = Path(args.metrics)
    # folder layout: results/<run>/metrics.json -> run name is the folder
    name = args.name or (mpath.parent.name if mpath.name == "metrics.json"
                         else mpath.name.replace("_metrics.json", ""))
    git_rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    rec = {
        "name": name,
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "model": args.model,
        "role": args.role,
        "why": args.why,
        "git": git_rev,
        "config": json.load(open(ROOT / "ours" / "config.json", encoding="utf-8")),
        "score": score.compute(args.metrics, args.q),
        "metrics": json.load(open(args.metrics, encoding="utf-8")),
    }
    with open(LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    pages = regenerate_pages()
    print(f"logged '{name}' (total {rec['score']['total']:.1f}/100) -> {LEDGER.name}; regenerated "
          + ", ".join(p.name for p in pages if p.suffix == ".md"))


if __name__ == "__main__":
    main()
