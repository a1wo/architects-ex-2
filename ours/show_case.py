"""
Inspect question / ground truth / model answer / judge verdict — one file, three modes.

Every run lives in its own folder  ours/results/<run>/  containing:
    answers.jsonl   raw model answers
    verdicts.jsonl  per-question judge verdicts
    metrics.json    aggregated metrics
    config.json     who answered, with which system prompt, who judged (written at run time)
    cases.csv       this run's question | ground truth | answer | verdict table

Index mode (no arguments) — regenerate every run's cases.csv, the combined
ours/results/all_cases.csv, and the navigation page ours/results/INDEX.md:

    python ours/show_case.py

Single-run CSV mode (used by run scripts after a run finishes):

    python ours/show_case.py --run-csv base_default

Single-case mode — print one question's full trace to the terminal:

    python ours/show_case.py dev-13-car-easy                    # across all runs
    python ours/show_case.py dev-13-car-easy base_default       # one run
    python ours/show_case.py dev-13-car-easy base_default --rev 2562109   # from a git commit
                                                                # (old flat layout supported)

Hebrew: CSVs store raw logical-order text (Excel/Numbers render RTL correctly).
Terminal output is rendered via python-bidi when installed; --no-bidi disables.
"""
import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "ours" / "results"
JUDGE_PROMPT_POINTER = "ours/stage1/eval_harness.py (RELEVANCE_PROMPT / CITATION_PROMPT)"

try:
    from bidi.algorithm import get_display
except ImportError:
    get_display = None


def rtl(text, enabled):
    if enabled and get_display:
        return "\n".join(get_display(line) for line in text.splitlines())
    return text


def strip_think(text):
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)


def load_questions():
    qs = json.load(open(ROOT / "reference_questions.json", encoding="utf-8"))
    return {q["id"]: q for q in qs}


def git_show(rel):
    return subprocess.run(["git", "show", rel], cwd=ROOT, capture_output=True, text=True)


def read_jsonl(run, kind, rev=None):
    """kind: 'answers' | 'verdicts'. With --rev, tries the folder layout first,
    then the old flat layout (<run>.jsonl / <run>_verdicts.jsonl)."""
    if rev:
        candidates = [f"ours/results/{run}/{kind}.jsonl",
                      f"ours/results/{run}.jsonl" if kind == "answers"
                      else f"ours/results/{run}_verdicts.jsonl"]
        lines = None
        for rel in candidates:
            out = git_show(f"{rev}:{rel}")
            if out.returncode == 0:
                lines = out.stdout.splitlines()
                break
        if lines is None:
            return {}
    else:
        path = RESULTS / run / f"{kind}.jsonl"
        if not path.exists():
            return {}
        lines = path.read_text(encoding="utf-8").splitlines()
    recs = {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" in r:
            recs[r["id"]] = r
    return recs


def load_models():
    try:
        return json.load(open(ROOT / "ours" / "config.json", encoding="utf-8"))
    except OSError:
        return {}


def infer_config(run):
    """Fallback for runs that predate per-run config.json (e.g. --rev on old commits)."""
    cfg = load_models()
    base, test = cfg.get("baseline_model", "?"), cfg.get("test_model", "?")
    known = {"base_default": (base, "default"), "base_strict": (base, "strict"),
             "base_cite": (base, "cite")}
    if run in known:
        model, pname = known[run]
    elif run.startswith("bare_test"):
        model, pname = test, "default"
    elif run.startswith("bare_baseline"):
        model, pname = base, "default"
    elif run == "citation_selftest":
        model, pname = "none (synthetic: answers are the ground truth — harness self-test)", None
    else:
        model, pname = "unknown — see ours/experiments.jsonl", None
    return {"answering_model": model, "system_prompt_name": pname,
            "judge_model": cfg.get("judge_model", "?"),
            "judge_temperature": cfg.get("judge_temperature")}


def run_config(run, rev=None):
    """Per-run config.json (the recorded truth), falling back to inference."""
    if rev:
        out = git_show(f"{rev}:ours/results/{run}/config.json")
        if out.returncode == 0:
            return json.loads(out.stdout)
    else:
        path = RESULTS / run / "config.json"
        if path.exists():
            return json.load(open(path, encoding="utf-8"))
    return infer_config(run)


def run_names():
    return sorted(p.name for p in RESULTS.iterdir()
                  if p.is_dir() and (p / "verdicts.jsonl").exists())


CSV_FIELDS = ["id", "domain", "difficulty", "run", "answering_model", "system_prompt",
              "judge_model", "question", "ground_truth", "model_answer",
              "verdict", "confident", "judge_reason", "citations"]


def run_rows(run, qs):
    answers = read_jsonl(run, "answers")
    verdicts = read_jsonl(run, "verdicts")
    cfg = run_config(run)
    rows = []
    for qid, q in qs.items():
        a, v = answers.get(qid), verdicts.get(qid)
        if not a and not v:
            continue
        rel = (v or {}).get("relevance", {})
        rows.append({
            "id": qid, "domain": q.get("domain", ""), "difficulty": q.get("difficulty", ""),
            "run": run,
            "answering_model": cfg.get("answering_model", ""),
            "system_prompt": cfg.get("system_prompt_name") or "",
            "judge_model": cfg.get("judge_model", ""),
            "question": q["question"], "ground_truth": q["ground_truth_answer"],
            "model_answer": strip_think((a or {}).get("answer", "")),
            "verdict": rel.get("verdict", ""), "confident": rel.get("confident", ""),
            "judge_reason": rel.get("reason", ""),
            "citations": json.dumps((a or {}).get("citations", []), ensure_ascii=False)
                         if (a or {}).get("citations") else "",
        })
    rows.sort(key=lambda r: r["id"])
    return rows


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel detects UTF-8
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        w.writerows(rows)


def write_run_csv(run):
    qs = load_questions()
    rows = run_rows(run, qs)
    if not rows:
        sys.exit(f"no results found in ours/results/{run}/")
    write_csv(RESULTS / run / "cases.csv", rows)
    print(f"wrote ours/results/{run}/cases.csv ({len(rows)} rows)")
    return rows


def regenerate_compare_pages():
    """One markdown + one CSV per evaluation type (STAGE1.md / STAGE23.md)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "compare_runs", Path(__file__).resolve().parent / "compare_runs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.generate()


def write_all():
    qs = load_questions()
    runs = run_names()
    if not runs:
        sys.exit(f"no run folders with verdicts.jsonl found in {RESULTS}")
    all_rows = []
    for run in runs:
        rows = run_rows(run, qs)
        if rows:
            write_csv(RESULTS / run / "cases.csv", rows)
        all_rows.extend(rows)
    all_rows.sort(key=lambda r: (r["id"], r["run"]))
    write_csv(RESULTS / "all_cases.csv", all_rows)
    pages = regenerate_compare_pages()
    print(f"wrote per-run cases.csv for {len(runs)} runs, "
          f"ours/results/all_cases.csv ({len(all_rows)} rows), "
          + ", ".join(p.name for p in pages if p.suffix == ".md"))
    print(f"runs: {', '.join(runs)}")


def show_run(run, qid, rev, bidi):
    a = read_jsonl(run, "answers", rev).get(qid)
    v = read_jsonl(run, "verdicts", rev).get(qid)
    if not a and not v:
        return False
    where = f"@{rev}" if rev else "working tree"
    print(f"\n--- run: {run} ({where}) " + "-" * max(0, 50 - len(run)))
    cfg = run_config(run, rev)
    print(f"ANSWERING MODEL: {cfg.get('answering_model', '?')}")
    jt = cfg.get("judge_temperature")
    print(f"JUDGE MODEL:     {cfg.get('judge_model', '?')}"
          + (f"  (temperature {jt})" if jt is not None else "")
          + f"  — judge prompts: {JUDGE_PROMPT_POINTER}")
    pname = cfg.get("system_prompt_name")
    if pname:
        text = cfg.get("system_prompt")
        print(f"SYSTEM PROMPT ({pname}):" + (f"\n  {text}" if text else " <text not recorded>"))
    if a:
        print("MODEL ANSWER:")
        print(rtl(strip_think(a.get("answer", "<no answer field>")), bidi))
        if a.get("citations"):
            print(f"CITATIONS: {json.dumps(a['citations'], ensure_ascii=False)}")
    else:
        print("MODEL ANSWER: <not found in this run>")
    if v:
        rel = v.get("relevance", {})
        print(f"JUDGE: verdict={rel.get('verdict')}  confident={rel.get('confident')}")
        if rel.get("reason"):
            print(f"REASON: {rel['reason']}")
    else:
        print("JUDGE: <no verdicts for this run>")
    return True


def show_case(qid, run, rev, bidi):
    q = load_questions().get(qid)
    if not q:
        sys.exit(f"unknown question id: {qid}  (see reference_questions.json)")
    if bidi and not get_display:
        print("(python-bidi not installed — printing raw text; pip install python-bidi)\n",
              file=sys.stderr)
    print(f"[{q['id']}]  domain={q['domain']}  difficulty={q['difficulty']}")
    print("QUESTION:")
    print(rtl(q["question"], bidi))
    print("GROUND TRUTH:")
    print(rtl(q["ground_truth_answer"], bidi))
    for src in q.get("ground_truth_sources", []):
        for opt in src.get("any_of", [src]):
            print(f"SOURCE: {opt.get('file')}  p.{opt.get('page')}")
    names = [run] if run else run_names()
    hits = sum(show_run(n, qid, rev, bidi) for n in names)
    if not hits:
        print("\n(no run contained this question id"
              + (f" at rev {rev})" if rev else ")"))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("qid", nargs="?", help="question id; omit to rebuild all CSVs + INDEX.md")
    ap.add_argument("run", nargs="?", help="run folder name (default: every run)")
    ap.add_argument("--run-csv", metavar="RUN", help="write ours/results/RUN/cases.csv and exit")
    ap.add_argument("--rev", help="git revision to read results from (e.g. 2562109)")
    ap.add_argument("--no-bidi", action="store_true", help="print raw logical-order text")
    args = ap.parse_args()
    if args.run_csv:
        write_run_csv(args.run_csv)
    elif args.qid:
        show_case(args.qid, args.run, args.rev, not args.no_bidi)
    else:
        write_all()


if __name__ == "__main__":
    main()
