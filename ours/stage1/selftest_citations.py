"""
Sanity check that the harness's citation scoring actually works (it reads 0 on
bare baselines by design, which looks suspicious). Builds a tiny answers file
where each answer IS the ground truth citing its known ground-truth page, plus
one answer citing a nonexistent file. Expected: all real citations "full",
the bogus one "invalid", relevance 100%.

    python ours/selftest_citations.py       # needs NEBIUS_API_KEY (4 judge calls)
"""
import json
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent.parent
qs = json.load(open(root / "reference_questions.json", encoding="utf-8"))
out = root / "ours" / "results" / "citation_selftest" / "answers.jsonl"
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    for q in qs[:3]:
        src = q["ground_truth_sources"][0]["any_of"][0]
        f.write(json.dumps({"id": q["id"], "answer": q["ground_truth_answer"],
                            "citations": [{"file": src["file"], "page": src.get("page")}],
                            "latency_ms": 1000, "tokens": {"prompt": 0, "completion": 0}},
                           ensure_ascii=False) + "\n")
    f.write(json.dumps({"id": qs[3]["id"], "answer": qs[3]["ground_truth_answer"],
                        "citations": [{"file": "car/files/does-not-exist.pdf", "page": 99}],
                        "latency_ms": 1000, "tokens": {"prompt": 0, "completion": 0}},
                       ensure_ascii=False) + "\n")

sys.exit(subprocess.call([sys.executable, str(root / "ours" / "stage1" / "eval_harness.py"), str(out),
                          "--out", str(out.parent)], cwd=root))
