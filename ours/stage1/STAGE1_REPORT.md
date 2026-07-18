# Stage 1 Report — Baseline & Evaluation Harness

*(single combined deliverable: baseline results + the three required answers + full per-metric methodology with prompts and code)*

**Setup.** 48 Hebrew dev questions (`reference_questions.json`) through bare `deepseek-ai/DeepSeek-V4-Pro` (strongest open-weights on Nebius Token Factory) — no documents. Three system prompts: **default** (provided), **strict** ("answer only if certain, else refuse"), **cite** ("every claim must cite document + page"). Model roles are configured in [`../config.json`](../config.json): `baseline_model` (bar to beat) / `test_model` (our future generator) / `judge_model` (pinned).

## Results

| metric | default | strict | cite | test model (Qwen3-32B) |
|---|---|---|---|---|
| correct | **35%** | 13% | 31% | 17% |
| partial | 2% | 0% | 6% | 2% |
| incorrect | 58% | 10% | 42% | 27% |
| refusals | 4% | **77%** | 21% | 54% |
| **hallucination rate** | **56%** | **8%** | **42%** | 25% |
| citation accuracy | 0 (no citations) | 0 (no citations) | 0 (all invented) | 0 |
| conversational Q (judged, 0–1) | 0.98 | 0.41 | 0.84 | 0.23 |
| latency mean / p95 (ms) | 9292 / 27148 | 2289 / 6362 | 7082 / 17074 | 25631 / 51041 |
| **est. competition score /100** | **42.3** | 22.2 | 39.8 | 17.8 |

Correct by difficulty (default): easy 8/16, medium 4/16, hard 5/16. By domain: business/life 67%, health 50%, **travel 0%**, car/mortgage 17%. Full run ledger: [`../RUNS.md`](../RUNS.md).

## The three required answers

### 1. Where does the baseline succeed without any Harel documents?

It succeeds where the answer is **Israeli insurance law or industry-standard practice**, not Harel-specific: the 3-year limitation period (חוק חוזה הביטוח), "join via your insurance agent," beneficiary defaults, proportional premium refunds. These are in the training data because they appear across the public Israeli legal/insurance web. It fails hardest where answers depend on **Harel's specific numbers and service contracts** — travel (0%) and car (17%) hinge on particular service providers, coverage caps, and rider names. The model knows *insurance*; it does not know *Harel's policies*.

### 2. When it's wrong, is it wrong confidently? Which failure is worse for an insurer?

Almost always confidently: 56% of default answers are confident contradictions of the ground truth with fabricated specifics — "עד 12 חודשים" where the policy says 100 days (dev-09), "8% מסכום הביטוח" where the truth is 6,000 ₪ (dev-04), 12,000 ₪ where the cap is 24,000 ₪ (dev-06). The **cite** prompt is the cautionary tale: it *invents* authoritative-looking citations ("פוליסת ביטוח מחזיקי אקדח, סעיף 4.2.1, עמוד 7") to documents that don't exist. For an insurer, a confident wrong answer is far worse than "I don't know": it creates reliance, liability, and regulatory exposure. The strict prompt proves the dial exists — hallucinations 56%→8% — but at the cost of refusing 77% of everything, including much of what it knew. **Only retrieval moves both numbers at once.**

### 3. A question where we disagree with the judge

`dev-13-car-easy` (keys locked in car — does the service cover break-in?). Ground truth: yes, unconditionally. The model answered "depends on your service rider: covered under כתב שירות DRIVE, not under כתב שירות כבישים" — and the judge scored it **incorrect + confident**, i.e., a hallucination. We'd call it partial-correct: the caveat is reasonable customer-service behavior and the DRIVE branch matches the ground truth. Implication at scale: an LLM judge anchors on ground-truth phrasing and punishes legitimate conditional answers, so (a) judged deltas are trustworthy only when large, (b) borderline verdicts need human spot-checks, (c) the judge model + prompts must stay pinned so the bias is at least constant.

---

# How every metric is measured

All measurement is in [`../eval_harness.py`](../eval_harness.py); composite scoring in [`../score.py`](../score.py). The judge is `deepseek-ai/DeepSeek-V4-Pro`, `temperature=0.0`, forced JSON, 5 retries with exponential backoff; every verdict carries a one-sentence `reason` and is saved per-question in `<run>_verdicts.jsonl` — nothing is silently dropped.

```python
def judge(prompt):
    for attempt in range(5):
        try:
            reply = chat([{"role": "user", "content": prompt}], model=JUDGE_MODEL,
                         temperature=0.0, max_tokens=300, quiet=True)
            parsed = parse_json_reply(reply)      # permissive {...} extraction
            if parsed: return parsed
        except Exception as e:
            if attempt == 4: return {"error": str(e)}
            time.sleep(2 ** attempt * 2)          # 2s..16s backoff
```

## 1. Answer relevance — LLM-as-judge, exact prompt

```text
You are grading a customer-support answer about Harel Insurance policies.

Question (Hebrew): {question}
Ground-truth answer: {ground_truth}
System's answer: {answer}

Grade ONLY whether the system's answer agrees with the ground truth on the fact
that was asked. Ignore style, length, and extra caveats. An answer that refuses
("I don't know", "cannot answer without the policy", refers the customer
elsewhere without answering) is a REFUSAL, not wrong.

Reply with ONLY a JSON object, no prose, no code fences:
{"verdict": "correct" | "partial" | "incorrect" | "refusal",
 "confident": true | false, "reason": "<one short sentence>"}

"confident" = does the system's answer assert its claims without hedging?
(a refusal is never confident)
```

Aggregation: `R = (correct + 0.5·partial) / n`, plus per-domain and per-difficulty splits.

## 2. Hallucination rate — derived, no second judge

One source of truth for "wrong"; the hallucination metric just isolates the *confident* wrongs:

```python
halluc = sum(1 for r, c in zip(rel, confident) if r == "incorrect" and c)
hallucination_rate = halluc / n
```

Decisions, made explicit: **refusal ≠ hallucination** (a system that knows what it doesn't know is measured — and rewarded — separately via the refusal rate); hedged-wrong (`incorrect, confident=false`) is wrong but not a hallucination. Validation: the strict prompt moved refusals 4%→77% and hallucinations 56%→8% — the metric separates the two behaviors exactly as designed.

## 3. Citation accuracy — resolve mechanically, then judge support

**Step 1 — resolve** each cited `{file, page}` against the frozen corpus (exact path, then unique-basename fallback). PDFs: cited 1-based page extracted with `pypdf`; `.txt` web pages: whole file; text truncated to 6,000 chars. **Any failure — missing file, out-of-range page, empty extraction — is `invalid` with no judge call**, which is how fabricated citations count against a run:

```python
def resolve(self, file, page):
    cand = self.root / file if file else None
    if not (cand and cand.exists()):
        cand = self.by_name.get(Path(file or "").name)   # basename fallback
    if not cand: return None                             # -> "invalid"
    if cand.suffix.lower() == ".txt":
        return cand.read_text(...)[:PAGE_CHARS]
    reader = PdfReader(str(cand))
    if not page or page < 1 or page > len(reader.pages): return None  # -> "invalid"
    return (reader.pages[page - 1].extract_text() or "")[:PAGE_CHARS]
```

**Step 2 — judge** the resolved page text against the **ground truth** (not the system's answer — per the exercise; no fixed source list, any establishing page earns credit; `ground_truth_sources` is debug-only). Exact prompt:

```text
You are checking a citation in an insurance support answer.

Ground-truth answer to the customer's question: {ground_truth}
The system cited {file} page {page}. Text of that page:
---
{page_text}
---
Does this page establish the ground-truth answer? Reply with ONLY a JSON object,
no prose, no code fences:
{"support": "full" | "partial" | "none", "reason": "<one short sentence>"}
```

Aggregate: `C = (full + 0.5·partial) / judged` (≤3 citations judged per answer, cost bound). **End-to-end verification** ([`../selftest_citations.py`](../selftest_citations.py)): answers citing the known ground-truth pages → 3/3 `full`; a bogus `does-not-exist.pdf` p.99 → `invalid`. All 58 dev ground-truth sources resolve to readable Hebrew text.

## 4. Latency — measured, never judged

The runner wraps the full model call: `latency_ms = (time.time() - t0) * 1000` — includes network and queueing, i.e., what a customer feels. Harness aggregates mean / p50 / p95 (max when n<20).

## 5. Conversational quality — judged 1–5, correctness excluded

Mirrors the final rubric's 10%. Exact prompt:

```text
You are rating the conversational quality of a customer-support reply from an
insurance company, NOT its factual correctness.

Customer question (Hebrew): {question}
Support reply: {answer}

Rate ONLY clarity, tone, and flow on a 1-5 scale:
5 = clear, warm, well-structured, right length, same language as the question,
    directly addresses the customer
4 = good but minor issues (slightly too long/short, small structure problems)
3 = understandable but flawed (wall of text, robotic tone, poor structure,
    hedging clutter)
2 = hard to follow, wrong register, ignores the customer's framing, or
    partially wrong language
1 = confusing, rude, wrong language entirely, or doesn't engage with the question

A polite, clear refusal can still score 4-5. A correct but unreadable answer
scores low.

Reply with ONLY a JSON object, no prose, no code fences:
{"score": 1 | 2 | 3 | 4 | 5, "reason": "<one short sentence>"}
```

Aggregate: `Q = (mean(scores) − 1) / 4` ∈ [0,1]. Calibration held in practice: fluent DeepSeek 4.92/5 → 0.98; Qwen3-32B leaking chain-of-thought → 0.23.

## 6. Efficiency — arithmetic, no prompt by design

```python
lat_score  = clamp01(1 - (p50_seconds - 2) / 18)        # 1.0 at <=2s, 0.0 at 20s
cost_score = clamp01(1 - (cost_per_q - 0.001) / 0.009)  # 1.0 at <=$0.001/q, 0.0 at $0.01/q
E = 0.5 * lat_score + 0.5 * cost_score                  # cost: $0.5/M in, $2/M out (TF est.)
```

## Composite score (proxy of the official rubric)

`score = 65·R + 15·C + 10·E + 10·Q` (+5 voice, +5 UI later) — [`../score.py`](../score.py). Every run is logged with config snapshot + git commit + hypothesis to [`../experiments.jsonl`](../experiments.jsonl) by [`../log_run.py`](../log_run.py), which regenerates [`../RUNS.md`](../RUNS.md).

## Known limitations (deliberately visible)

1. **The judge is an LLM** — anchors on ground-truth phrasing; can punish legitimate conditional answers (`dev-13`). Sub-3-point deltas need verdict spot-checks.
2. **Judge = generator family** for the DeepSeek baseline (self-preference risk); pinning makes the bias constant, so relative deltas stay meaningful.
3. **pypdf Hebrew extraction** is imperfect; Stage 2's Docling pipeline replaces it.
4. **temp-0 ≠ deterministic** on TF serving — rescores drift ~±2%.
5. **E and Q formulas are our proxies** — the official internal versions are unknown; R and C are the trustworthy comparison numbers.
