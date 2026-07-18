"""
STAGE 1 evaluation harness — exactly the four metrics the Stage-1 spec requires,
nothing more. (Stage 2/3 evaluation, which adds conversational quality and the
competition composite, lives in ours/stage23/ and reuses this module.)

Scores an answers JSONL (from baseline_runner.py / submit_runner.py / our RAG)
against the dev set's ground truths and reports:

  * relevance          -- LLM-as-judge: does the answer agree with the ground
                          truth on the asked fact? (correct / partial / wrong)
  * hallucination rate -- confident answers that contradict the ground truth.
                          Refusals ("I don't know") are counted separately, NOT
                          as hallucinations: knowing what you don't know scores
                          better than a confident wrong answer.
  * citation accuracy  -- each cited {file, page} is resolved to the actual
                          corpus page; a judge decides whether the cited text
                          establishes the ground-truth answer (full / partial /
                          no). Nonexistent file or page => invalid citation.
  * latency            -- mean / p50 / p95 from the answers file.

Usage:
    export NEBIUS_API_KEY=...
    python eval_harness.py baseline_answers.jsonl
    python eval_harness.py answers.jsonl --questions reference_questions.json \
        --corpus corpus --out results/baseline
Outputs <out>_verdicts.jsonl (per question, for debugging) and
<out>_metrics.json + a printed markdown table.

The judge model is PINNED (JUDGE_MODEL below) and runs at temperature 0 with
forced-JSON prompting, so runs are comparable across the whole exercise.
"""
import argparse
import json
import os
import re
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))  # tf_client.py lives in the given starter kit at repo root
from tf_client import chat

CONFIG = json.load(open(REPO_ROOT / "ours" / "config.json", encoding="utf-8"))
JUDGE_MODEL = os.environ.get("JUDGE_MODEL", CONFIG["judge_model"])  # pinned; do not bump mid-exercise
JUDGE_WORKERS = 12
PAGE_CHARS = 6000  # max chars of cited page text shown to the judge

RELEVANCE_PROMPT = """You are grading a customer-support answer about Harel Insurance policies.

Question (Hebrew): {question}

Ground-truth answer: {ground_truth}

System's answer: {answer}

Grade ONLY whether the system's answer agrees with the ground truth on the fact that was asked. Ignore style, length, and extra caveats. An answer that refuses ("I don't know", "cannot answer without the policy", refers the customer elsewhere without answering) is a REFUSAL, not wrong.

Reply with ONLY a JSON object, no prose, no code fences:
{{"verdict": "correct" | "partial" | "incorrect" | "refusal", "confident": true | false, "reason": "<one short sentence>"}}

"confident" = does the system's answer assert its claims without hedging? (a refusal is never confident)"""

CITATION_PROMPT = """You are checking a citation in an insurance support answer.

Ground-truth answer to the customer's question: {ground_truth}

The system cited {file} page {page}. Text of that page:
---
{page_text}
---

Does this page establish the ground-truth answer? Reply with ONLY a JSON object, no prose, no code fences:
{{"support": "full" | "partial" | "none", "reason": "<one short sentence>"}}"""


def parse_json_reply(text):
    """Judge replies sometimes arrive fenced or with stray prose; dig the JSON out."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    return json.loads(m.group(0)) if m else None


def judge(prompt):
    for attempt in range(5):
        try:
            reply = chat([{"role": "user", "content": prompt}], model=JUDGE_MODEL,
                         temperature=0.0, max_tokens=300, quiet=True)
            parsed = parse_json_reply(reply)
            if parsed:
                return parsed
        except Exception as e:
            if attempt == 4:
                return {"error": str(e)}
            time.sleep(2 ** attempt * 2)  # 2s..16s backoff; TF drops connections under load
    return {"error": "unparseable judge reply"}


class Corpus:
    """Resolves {file, page} citations to page text. PDFs by page; .txt pages whole."""

    def __init__(self, root):
        self.root = Path(root)
        # tolerate path variants: with/without corpus/ prefix, URL-ish citations
        self.by_name = {}
        if self.root.exists():
            for p in self.root.rglob("*"):
                if p.suffix.lower() in (".pdf", ".txt"):
                    self.by_name.setdefault(p.name, p)
        self._pdf_cache = {}

    def resolve(self, file, page):
        """Returns page text, or None if the file/page doesn't exist."""
        cand = self.root / file if file else None
        if not (cand and cand.exists()):
            cand = self.by_name.get(Path(file or "").name)
        if not cand:
            return None
        if cand.suffix.lower() == ".txt":
            return cand.read_text(encoding="utf-8", errors="replace")[:PAGE_CHARS]
        try:
            from pypdf import PdfReader
            if cand not in self._pdf_cache:
                self._pdf_cache[cand] = PdfReader(str(cand))
            reader = self._pdf_cache[cand]
            if not page or page < 1 or page > len(reader.pages):
                return None
            return (reader.pages[page - 1].extract_text() or "")[:PAGE_CHARS]
        except Exception:
            return None


def score_one(q, ans, corpus):
    v = {"id": q["id"], "domain": q.get("domain"), "difficulty": q.get("difficulty")}

    rel = judge(RELEVANCE_PROMPT.format(question=q["question"],
                                        ground_truth=q["ground_truth_answer"],
                                        answer=ans.get("answer", "")))
    v["relevance"] = rel

    cites = ans.get("citations") or []
    cite_verdicts = []
    for c in cites[:3]:  # judge at most 3 citations per answer
        file, page = c.get("file"), c.get("page")
        text = corpus.resolve(file, page)
        if text is None or not text.strip():
            cite_verdicts.append({"file": file, "page": page, "support": "invalid"})
            continue
        cv = judge(CITATION_PROMPT.format(ground_truth=q["ground_truth_answer"],
                                          file=file, page=page, page_text=text))
        cite_verdicts.append({"file": file, "page": page, **cv})
    v["citations"] = cite_verdicts
    v["latency_ms"] = ans.get("latency_ms")
    v["tokens"] = ans.get("tokens")
    return v


def aggregate(verdicts):
    n = len(verdicts)
    rel = [v["relevance"].get("verdict") for v in verdicts]
    confident = [v["relevance"].get("confident") for v in verdicts]
    halluc = sum(1 for r, c in zip(rel, confident) if r == "incorrect" and c)
    lat = [v["latency_ms"] for v in verdicts if v.get("latency_ms")]
    all_cites = [c for v in verdicts for c in v["citations"]]

    m = {
        "n": n,
        "relevance": {
            "correct": rel.count("correct") / n,
            "partial": rel.count("partial") / n,
            "incorrect": rel.count("incorrect") / n,
            "refusal": rel.count("refusal") / n,
        },
        "hallucination_rate": halluc / n,   # confident AND contradicts ground truth
        "citations": {
            "answers_with_citations": sum(1 for v in verdicts if v["citations"]) / n,
            "judged": len(all_cites),
            "full": sum(1 for c in all_cites if c.get("support") == "full"),
            "partial": sum(1 for c in all_cites if c.get("support") == "partial"),
            "none": sum(1 for c in all_cites if c.get("support") == "none"),
            "invalid": sum(1 for c in all_cites if c.get("support") == "invalid"),
        },
        "conversational": (lambda s: {"mean_1to5": statistics.mean(s) if s else None,
                                      "Q": (statistics.mean(s) - 1) / 4 if s else None})(
            [v["conversational"]["score"] for v in verdicts
             if isinstance(v.get("conversational", {}).get("score"), (int, float))]),
        "latency_ms": {
            "mean": statistics.mean(lat) if lat else None,
            "p50": statistics.median(lat) if lat else None,
            "p95": statistics.quantiles(lat, n=20)[-1] if len(lat) >= 20 else (max(lat) if lat else None),
        },
        "judge_model": JUDGE_MODEL,
    }
    # per-domain correct rate -- where does it break?
    by_domain = {}
    for v in verdicts:
        d = v.get("domain") or "?"
        by_domain.setdefault(d, []).append(v["relevance"].get("verdict") == "correct")
    m["correct_by_domain"] = {d: sum(xs) / len(xs) for d, xs in sorted(by_domain.items())}
    return m


def print_table(m):
    r, c, l = m["relevance"], m["citations"], m["latency_ms"]
    print(f"""
| metric | value |
|---|---|
| questions | {m['n']} |
| relevance: correct | {r['correct']:.0%} |
| relevance: partial | {r['partial']:.0%} |
| relevance: incorrect | {r['incorrect']:.0%} |
| refusals | {r['refusal']:.0%} |
| **hallucination rate** (confident + wrong) | **{m['hallucination_rate']:.0%}** |
| answers with citations | {c['answers_with_citations']:.0%} |
| citations judged full / partial / none / invalid | {c['full']} / {c['partial']} / {c['none']} / {c['invalid']} (of {c['judged']}) |
| latency mean / p50 / p95 (ms) | {l['mean']:.0f} / {l['p50']:.0f} / {l['p95']:.0f} |
| judge model | {m['judge_model']} |""")
    if m["conversational"]["Q"] is not None:
        print(f"| conversational (Stage-2/3 extra, 1-5 mean → Q) | {m['conversational']['mean_1to5']:.2f} → Q={m['conversational']['Q']:.2f} |")
    print("\nCorrect by domain: " + ", ".join(f"{d} {v:.0%}" for d, v in m["correct_by_domain"].items()))


def evaluate(answers_path, questions_path, corpus_path, out_prefix, score_fn=score_one):
    """Full pipeline: load -> judge every answer with score_fn -> write verdicts +
    metrics -> print table. stage23/eval_harness.py reuses this with its own score_fn."""
    questions = json.load(open(questions_path, encoding="utf-8"))
    if isinstance(questions, dict):
        questions = questions["questions"]
    qby = {q["id"]: q for q in questions}
    answers = [json.loads(line) for line in open(answers_path, encoding="utf-8")]
    answers = [a for a in answers if a["id"] in qby]
    if not answers:
        sys.exit("no answers match the question set")
    corpus = Corpus(corpus_path)

    with ThreadPoolExecutor(max_workers=JUDGE_WORKERS) as pool:
        verdicts = list(pool.map(lambda a: score_fn(qby[a["id"]], a, corpus), answers))

    out = out_prefix or Path(answers_path).stem
    with open(f"{out}_verdicts.jsonl", "w", encoding="utf-8") as f:
        for v in verdicts:
            f.write(json.dumps(v, ensure_ascii=False) + "\n")
    metrics = aggregate(verdicts)
    json.dump(metrics, open(f"{out}_metrics.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print_table(metrics)
    print(f"\nwrote {out}_verdicts.jsonl, {out}_metrics.json")
    return metrics


def make_argparser():
    ap = argparse.ArgumentParser()
    ap.add_argument("answers")
    ap.add_argument("--questions", default="reference_questions.json")
    ap.add_argument("--corpus", default="corpus")
    ap.add_argument("--out", default=None, help="prefix for _verdicts.jsonl / _metrics.json")
    return ap


if __name__ == "__main__":
    args = make_argparser().parse_args()
    evaluate(args.answers, args.questions, args.corpus, args.out)
