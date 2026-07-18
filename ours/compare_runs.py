"""
Compare all runs — grouped by which evaluation scored them, never blended.

Runs scored by different harnesses are not directly comparable (stage1 has no
judged conversational Q; stage23's composite needs it), so every output here is
per evaluation type — ONE markdown page and ONE CSV for each:

    ours/results/STAGE1.md  + compare_stage1.csv    stage1-scored runs  (4 spec metrics)
    ours/results/STAGE23.md + compare_stage23.csv   stage23-scored runs (+ Q + composite /100)

    python ours/compare_runs.py                # print tables + rewrite MD/CSV files
    python ours/compare_runs.py --sort halluc  # sort the printed tables by any column

The evaluation type comes from each run's metrics.json ("harness", stamped at
scoring time). Date/why per run come from the ledger (ours/experiments.jsonl,
latest record per run). log_run.py and show_case.py regenerate these pages
automatically after every logged run / CSV rebuild.
"""
import argparse
import csv
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "ours" / "results"
LEDGER = ROOT / "ours" / "experiments.jsonl"

_spec = importlib.util.spec_from_file_location("score", ROOT / "ours" / "stage23" / "score.py")
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)

DESCRIPTION = {
    "stage1": "Stage-1 evaluation: the four spec metrics (relevance, hallucination, "
              "citations, latency). No judged conversational quality, no composite score.",
    "stage23": "Stage-2/3 evaluation: same four metrics from the same pinned judge, PLUS "
               "judged conversational quality (Q) and the composite competition proxy "
               "`65·R + 15·C + 10·E + 10·Q` (see ours/stage23/score.py).",
}


def load_ledger():
    latest = {}
    if LEDGER.exists():
        for line in open(LEDGER, encoding="utf-8"):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            latest[rec.get("name")] = rec
    return latest


def load_runs():
    ledger = load_ledger()
    by_harness = {}
    for mfile in sorted(RESULTS.glob("*/metrics.json")):
        run = mfile.parent.name
        m = json.load(open(mfile, encoding="utf-8"))
        harness = m.get("harness")
        if not harness:
            print(f"warning: {run}/metrics.json has no 'harness' field — skipped "
                  f"(re-score it, or backfill the field)", file=sys.stderr)
            continue
        cfg = {}
        cfile = mfile.parent / "config.json"
        if cfile.exists():
            cfg = json.load(open(cfile, encoding="utf-8"))
        by_harness.setdefault(harness, []).append((run, cfg, m, ledger.get(run, {})))
    return by_harness


def base_row(run, cfg, m, led):
    rel = m.get("relevance", {})
    return {
        "run": run,
        "model": cfg.get("answering_model", "?"),
        "prompt": cfg.get("system_prompt_name") or "—",
        "correct": rel.get("correct"),
        "partial": rel.get("partial"),
        "incorrect": rel.get("incorrect"),
        "refusal": rel.get("refusal"),
        "halluc": m.get("hallucination_rate"),
        "p50_s": (m.get("latency_ms", {}).get("p50") or 0) / 1000,
        "date": (led.get("ts") or "")[:10] or "—",
        "why": led.get("why", "—"),
    }


def stage23_row(run, cfg, m, led):
    row = base_row(run, cfg, m, led)
    s = score.compute(RESULTS / run / "metrics.json")
    row.update({"Q": s["Q"], "E": s["E"],
                "cost_per_q": s["cost_per_q_usd"], "total": s["total"]})
    # column order: metrics first, provenance last
    for k in ("date", "why"):
        row[k] = row.pop(k)
    return row


ROW_BUILDERS = {"stage1": base_row, "stage23": stage23_row}
DEFAULT_SORT = {"stage1": "correct", "stage23": "total"}
PCT_COLS = {"correct", "partial", "incorrect", "refusal", "halluc", "Q", "E"}


def fmt(col, v):
    if v is None:
        return "—"
    if col in PCT_COLS:
        return f"{100 * v:.0f}%"
    if col == "p50_s":
        return f"{v:.1f}s"
    if col == "cost_per_q":
        return f"${v:.4f}"
    if col == "total":
        return f"**{v:.1f}**"
    return str(v)


def write_md(harness, rows):
    cols = [c for c in rows[0] if c not in ("run", "model")]
    lines = [f"# {harness} runs", "", DESCRIPTION.get(harness, ""), "",
             f"{len(rows)} runs, ranked by {DEFAULT_SORT.get(harness, 'correct')}. "
             f"Judge pinned in `ours/config.json`. Every run folder holds "
             "`answers.jsonl` `verdicts.jsonl` `metrics.json` `config.json` `cases.csv`.",
             "",
             "| run | model | " + " | ".join(cols) + " |",
             "|" + "---|" * (2 + len(cols))]
    for r in rows:
        cells = [f"[`{r['run']}`]({r['run']}/cases.csv)", r["model"]]
        cells += [fmt(c, r[c]).replace("**", "**") for c in cols]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    other = "STAGE23" if harness == "stage1" else "STAGE1"
    lines += ["",
              f"Machine-readable copy: `compare_{harness}.csv`. Runs scored by the other "
              f"evaluation: [{other}.md]({other}.md) — do not compare across the two. "
              "All answers side by side: [all_cases.csv](all_cases.csv). "
              "Trace one question: `python ours/show_case.py <question-id> [run]`. "
              "Regenerate: `python ours/compare_runs.py`.", ""]
    path = RESULTS / f"{harness.upper()}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def print_table(harness, rows, sort_key):
    cols = [c for c in rows[0] if c not in ("model", "why", "date")]
    print(f"\n== {harness} — {len(rows)} runs, sorted by {sort_key} ==")
    widths = {c: max(len(c), *(len(fmt(c, r[c]).replace('**', '')) for r in rows)) for c in cols}
    print("  ".join(c.ljust(widths[c]) if c == "run" else c.rjust(widths[c]) for c in cols))
    for r in rows:
        print("  ".join((fmt(c, r[c]).replace("**", "")).ljust(widths[c]) if c == "run"
                        else (fmt(c, r[c]).replace("**", "")).rjust(widths[c]) for c in cols))
        print(f"    {r['model']}")


def generate(sort=None, verbose=False):
    """Rewrite STAGE1.md/STAGE23.md + compare_*.csv. Returns the written paths."""
    by_harness = load_runs()
    written = []
    for harness in sorted(by_harness):
        builder = ROW_BUILDERS.get(harness, base_row)
        rows = [builder(*args) for args in by_harness[harness]]
        sort_key = sort if sort and sort in rows[0] else DEFAULT_SORT.get(harness, "correct")
        rows.sort(key=lambda r: (r.get(sort_key) is None,
                                 -(r.get(sort_key) if isinstance(r.get(sort_key), (int, float)) else 0)))
        if verbose:
            print_table(harness, rows, sort_key)
        cpath = RESULTS / f"compare_{harness}.csv"
        with open(cpath, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        written += [write_md(harness, rows), cpath]
    return written


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sort", default=None,
                    help="column to sort by (default: correct for stage1, total for stage23)")
    args = ap.parse_args()
    written = generate(sort=args.sort, verbose=True)
    if not written:
        sys.exit(f"no scored runs found under {RESULTS}")
    print("\nwrote: " + ", ".join(str(p.relative_to(ROOT)) for p in written))


if __name__ == "__main__":
    main()
