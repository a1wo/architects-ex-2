# Stage 1 Report — Baseline & Evaluation Harness

*(single combined deliverable: baseline results + the three required answers + full per-metric methodology with prompts and code)*

**Setup.** 48 Hebrew dev questions (`reference_questions.json`) through bare `deepseek-ai/DeepSeek-V4-Pro` (strongest open-weights on Nebius Token Factory) — no documents. Three system prompts: **default** (provided), **strict** ("answer only if certain, else refuse"), **cite** ("every claim must cite document + page"). Model roles are configured in [`../config.json`](../config.json): `baseline_model` (bar to beat) / `test_model` (our future generator) / `judge_model` (pinned).


### 1. Where does the baseline succeed without any Harel documents?

It succeeds where the answer is **Israeli insurance law or industry-standard practice**, not Harel-specific: the 3-year limitation period (חוק חוזה הביטוח), "join via your insurance agent," beneficiary defaults, proportional premium refunds. These are in the training data because they appear across the public Israeli legal/insurance web. It fails hardest where answers depend on **Harel's specific numbers and service contracts** — travel (0%) and car (17%) hinge on particular service providers, coverage caps, and rider names. The model knows *insurance*; it does not know *Harel's policies*.

### 2. When it's wrong, is it wrong confidently? Which failure is worse for an insurer?

Almost always confidently: 56% of default answers are confident contradictions of the ground truth with fabricated specifics — "עד 12 חודשים" where the policy says 100 days (dev-09), "8% מסכום הביטוח" where the truth is 6,000 ₪ (dev-04), 12,000 ₪ where the cap is 24,000 ₪ (dev-06). The **cite** prompt is the cautionary tale: it *invents* authoritative-looking citations ("פוליסת ביטוח מחזיקי אקדח, סעיף 4.2.1, עמוד 7") to documents that don't exist. For an insurer, a confident wrong answer is far worse than "I don't know": it creates reliance, liability, and regulatory exposure. The strict prompt proves the dial exists — hallucinations 56%→8% — but at the cost of refusing 77% of everything, including much of what it knew. **Only retrieval moves both numbers at once.**

### 3. A question where we disagree with the judge
`dev-13-car-easy`: "המפתחות שלי ננעלו בתוך הרכב – האם מגיע לי שירות פריצה לרכב במסגרת כתב השירות?". Ground truth: **yes, unconditionally** — a representative comes to the car and breaks in (policy PDF, p. 55). The **cite** baseline answered that per "כתב שירות הראל טרייד אין" the service is given only at arrangement garages and is conditioned on towing, and therefore "אינני יכול לאמת מזכותך לשירות זה מתוך המסמך שברשותי" — and the judge scored it **incorrect + confident** ("the system's answer denies coverage"), i.e., a hallucination. We disagree with the category: the model never denied coverage — it explicitly declined to verify, so the fair verdict is a refusal (the invented "טרייד אין" citation is a real defect, but it belongs to the citation metric, not to confident denial). The judge anchored on the unconditional ground truth and read the hedge as a contradiction.

An earlier run of the same variant (preserved at commit `2562109`; results were later regenerated) showed the same bias more sharply: base_default answered "depends on your rider — covered under כתב שירות DRIVE, not under כתב שירות כבישים" — a reasonable conditional whose DRIVE branch matches the ground truth — and was also scored incorrect + confident. Implication at scale: an LLM judge anchors on ground-truth phrasing and punishes legitimate conditional or can't-verify answers, so (a) judged deltas are trustworthy only when large, (b) borderline verdicts need human spot-checks, (c) the judge model + prompts must stay pinned so the bias is at least constant. Reproduce either case: `python ours/show_case.py dev-13-car-easy base_cite` and `python ours/show_case.py dev-13-car-easy base_default --rev 2562109`.



---

# Stage-1 evaluation harness 
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

**Step 2 — judge** the resolved page text against **the system's own answer** — groundedness, not ground-truth matching. This is a deliberate design decision: the citation check never sees the ground truth. It asks one question — *does the page the system cited actually back what the system said?* — which (a) measures the honesty of the citation itself, (b) works identically on the blind set where we have no ground truths, and (c) is the same check the production system can run on itself before answering (verify-then-respond). Correctness against ground truth is already fully covered by the relevance metric; keeping the two orthogonal means a wrong-but-honestly-cited answer loses relevance points, not citation points, and a right-but-badly-cited answer loses citation points, not relevance points. (No fixed source list either way — any corpus page that genuinely supports the answer earns credit; `ground_truth_sources` is debug-only. Note the official harness wording judges citations against the ground-truth answer; on answers that are correct — the ones earning citation points in practice — the two definitions coincide.) Exact prompt:

```text
You are checking a citation in an insurance support answer.

The system's answer to the customer: {answer}
To support it, the system cited {file} page {page}. Text of that page:
---
{page_text}
---
Does this page actually support the factual claims of the system's answer?
Judge ONLY answer-vs-page grounding; you have no other source of truth.
{"support": "full" | "partial" | "none", "reason": "<one short sentence>"}
"full" = every factual claim tied to this citation appears in the page;
"partial" = some do; "none" = the page does not back what the answer says.
```

Aggregate: `C = (full + 0.5·partial) / judged` (≤3 citations judged per answer, cost bound). **End-to-end verification** ([`../selftest_citations.py`](../selftest_citations.py)): answers citing the known ground-truth pages → 3/3 `full`; a bogus `does-not-exist.pdf` p.99 → `invalid`. All 58 dev ground-truth sources resolve to readable Hebrew text.

## 4. Latency — measured, never judged

The runner wraps the full model call: `latency_ms = (time.time() - t0) * 1000` — includes network and queueing, i.e., what a customer feels. Harness aggregates mean / p50 / p95 (max when n<20).

## Comparing models
We reran the same bare evaluation (default prompt, no documents, same pinned judge) across seven more open-weights models on the shared endpoint:

| model | correct | halluc. | refusal | p50 |
|---|---|---|---|---|
| openai/gpt-oss-120b | **40%** | 60% | 0% | 5.9s |
| moonshotai/Kimi-K2.6 | 38% | **31%** | 19% | 26.6s |
| zai-org/GLM-5.2 | 33% | 44% | 17% | 61.6s |
| Qwen/Qwen3.5-397B-A17B | 31% | 44% | 4% | 48.5s |
| deepseek-ai/DeepSeek-V4-Pro (the §1–§3 baseline) | 31% | 56% | 6% | 26.7s |
| nvidia/Nemotron-3-Ultra-550b-a55b | 31% | 35% | 23% | **3.5s** |
| Qwen/Qwen3-32B | 10% | 75% | 0% | 24.2s |
| meta-llama/Llama-3.3-70B-Instruct | 8% | 42% | 19% | 39.4s |

Four results matter. **(a) No model breaks 40% correct without the documents** — eight families spanning 32B–550B land in the same band, so model choice does not substitute for retrieval; the conclusion of §1 is family-independent. **(b) Models differ far more in honesty than in knowledge**: gpt-oss-120b and Qwen3-32B refuse *nothing* (every miss is a confident hallucination), while Kimi and Nemotron refuse ~20% and cut the hallucination rate roughly in half at the same accuracy. Because a confident wrong answer is the worst outcome for an insurer (§2), we changed the relevance score to `correct + 0.5·partial + 0.1·refusal − 0.25·hallucination` — under it the composite ranking flips to Nemotron (35.1) > Kimi (34.2) > gpt-oss (33.5). **(c) The strict/cite dials from §2 are also model-independent** — strict collapses every model to 75–100% refusal; cite splits by scale: flagships refuse nearly everything (98–100%), while smaller models keep answering with fabricated citations (Qwen3-32B: 81% hallucination under cite). **(d) One anomaly**: Nemotron emitted raw `<tool_call>` JSON for nonexistent search tools on 6/48 questions — it *assumes* a retrieval loop even bare, and Qwen3-32B leaked `<think>` traces and garbled bytes, which the conversational judge punished (Q=0.22).

**Decision:** `test_model` (the Stage-2 RAG generator) = **moonshotai/Kimi-K2.6** — near-best accuracy with the best calibration; a generator that already prefers "I don't know" over invention is the right substrate for grounding. Full ranked tables, per-run folders, and per-question CSVs: `ours/results/STAGE1.md`, `ours/results/STAGE23.md`, `ours/results/<run>/`.
## Comparing policies

Three prompt policies so far (exact texts in each run's `config.json`): **default** — answer in the question's language, cite if you cite; **strict** — answer only if certain, otherwise refuse verbatim; **cite** — every factual claim must cite (document, page), else say you cannot verify. Effect on the two lead models:

| policy | Kimi-K2.6 correct | halluc. | refusal | gpt-oss-120b correct | halluc. | refusal |
|---|---|---|---|---|---|---|
| default | **38%** | 31% | 19% | **40%** | 60% | 0% |
| strict | 0% | 2% | 98% | 0% | 0% | 100% (0.6s p50) |
| cite | 0% | 0% | 100% | 0% | 0% | 100% (0.6s p50) |

Both collapse to total refusal under strict *and* cite — there is no middle setting. gpt-oss's collapse is instant (p50 drops to 0.6s: it pattern-matches the policy and emits a refusal template without deliberating). The instructive contrast is **where the honesty comes from**: gpt-oss's calibration is 100% policy-controlled (0% refusal without the policy, 100% with), while Kimi refuses 19% *unprompted* — its default behavior already includes self-assessment, which is why it keeps 38% correct with half of gpt-oss's hallucination rate. Prompt policies are a binary kill-switch on these models; useful calibration has to either come from the model (Kimi) or from retrieval (Stage 2).
