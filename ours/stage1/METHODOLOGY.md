# Evaluation Methodology — how every metric is measured

All measurement lives in [`../eval_harness.py`](../eval_harness.py). Input: an answers
JSONL (one record per dev question: `{id, answer, citations[], latency_ms, tokens}`).
Output: `<name>_verdicts.jsonl` (per-question, for audits) and `<name>_metrics.json`
(aggregates). Composite scoring on top: [`../score.py`](../score.py).

**The judge**: `deepseek-ai/DeepSeek-V4-Pro` (pinned in [`../config.json`](../config.json)),
`temperature=0.0`, `max_tokens=300`, forced-JSON prompts ("Reply with ONLY a JSON object,
no prose, no code fences"). Replies are parsed with a permissive `{...}` regex
(`parse_json_reply`); on API error or unparseable output the call retries up to 5 times
with exponential backoff (2s→16s), then records `{"error": ...}` — errored questions are
visible in the verdicts file, never silently dropped. 4 judge calls run in parallel
(`ThreadPoolExecutor`), each verdict includes a one-sentence `reason` for auditability.

---

## 1. Answer relevance

**Question asked of the judge** (`RELEVANCE_PROMPT`): given the customer question, the
ground-truth answer, and the system's answer — *does the system's answer agree with the
ground truth on the fact that was asked?* Style, length, and extra caveats are explicitly
excluded. Output schema:

```json
{"verdict": "correct" | "partial" | "incorrect" | "refusal",
 "confident": true | false,
 "reason": "<one short sentence>"}
```

- `refusal` is defined in the prompt ("I don't know", "cannot answer without the policy",
  refers the customer elsewhere without answering) so refusals are never scored as wrong.
- `confident` = does the answer assert its claims without hedging (a refusal is never confident).
  This flag exists solely to feed the hallucination metric.
- **Aggregation**: fraction of each verdict over all questions; relevance score
  `R = (correct + 0.5·partial) / n`. Also broken down per domain and per difficulty.

## 2. Hallucination rate

**No separate judge call** — derived from the relevance verdict, by design (one source of
truth for "wrong"):

```
hallucination = verdict == "incorrect" AND confident == true
rate = count / n
```

- Decision recorded up front: **a refusal is NOT a hallucination.** A system that knows
  what it doesn't know is measured separately (refusal rate) and rewarded relative to
  confident wrongness. Hedged wrong answers (`incorrect`, `confident=false`) are wrong
  but not counted as hallucinations either — the metric isolates the worst failure mode:
  asserting falsehoods.
- Validated on the strict-prompt run: refusals 4%→77%, hallucinations 56%→8% — the metric
  separates the two behaviors exactly as intended.

## 3. Citation accuracy

Two-step: **mechanical resolution, then judged support.**

**Step 1 — resolve** (`Corpus.resolve`): each cited `{file, page}` is looked up in the
frozen corpus snapshot. Exact relative path first (`corpus/<file>`), then a
basename-index fallback (tolerates `corpus/`-prefix or path variants; the corpus has no
duplicate basenames). PDFs: the cited page (1-based) is extracted with `pypdf`; a page
outside `1..len(pages)` fails. Web pages (`.txt`): whole file. Page text is truncated to
6,000 chars for the judge. **Any failure — file not found, bad page, empty extraction —
is verdict `invalid` with no judge call.** This is what makes fabricated citations
("סעיף 4.2.1, עמוד 7" of a nonexistent PDF) count against a run.

**Step 2 — judge** (`CITATION_PROMPT`): the judge sees the ground-truth answer and the
*actual resolved page text*, and answers: does this page establish the ground-truth
answer? `{"support": "full" | "partial" | "none"}`.

- Judged against the **ground truth**, not the system's answer — per the exercise: "do the
  cited pages establish the ground-truth answer". There is **no fixed list of correct
  sources**: any corpus page that truly establishes the fact earns credit;
  `ground_truth_sources` is used only for debugging retrieval, never for scoring.
- At most 3 citations judged per answer (cost bound). Aggregate:
  `C = (full + 0.5·partial) / judged`, 0 if nothing judged.
- **Verified end-to-end** by [`../selftest_citations.py`](../selftest_citations.py):
  answers citing the known ground-truth pages score 3/3 `full`; a deliberately bogus
  citation (`does-not-exist.pdf` p.99) scores `invalid`. All 58 ground-truth sources in
  the dev set resolve to readable Hebrew text (RTL extraction spot-checked).

## 4. Latency

Measured by the runner around the full model call (`time.time()` delta → `latency_ms`
per record, includes network + queueing — what a customer would feel). The harness
aggregates mean, p50 (median), p95 (or max when n<20). Never judged, never estimated.

## 5. Conversational quality (mirrors the final rubric's 10%)

**Judge call per answer** (`CONVERSATIONAL_PROMPT`): rates ONLY clarity/tone/flow on a
1–5 rubric spelled out in the prompt (5 = clear, warm, right language/length … 1 =
confusing/wrong language), with correctness explicitly out of scope. Two calibration
rules baked into the prompt: *a polite clear refusal can still score 4–5; a correct but
unreadable answer scores low.* Aggregate: mean of 1–5 scores, normalized
`Q = (mean − 1) / 4` ∈ [0,1]. (Empirically: fluent DeepSeek answers 4.92/5 → 0.98;
Qwen3-32B with leaked reasoning 0.23 — the metric catches unreadable output.)

## 6. Efficiency (mirrors the final rubric's 10%)

Pure arithmetic in `score.py`, no judge: `E = 0.5·latency_band + 0.5·cost_band` where
latency_band is 1.0 at p50 ≤ 2s falling linearly to 0.0 at 20s, and cost_band is 1.0 at
≤ $0.001/question falling linearly to 0.0 at $0.01/q. Cost per question = token counts ×
Token Factory estimate ($0.5/M in, $2/M out — same prices `tf_client.py` prints).

---

## Known limitations (kept deliberately visible)

1. **The judge is an LLM** — it anchors on ground-truth phrasing and can punish
   legitimate conditional answers (documented case: `dev-13-car-easy`, a defensible
   partial-correct scored as a confident hallucination). Small deltas between runs need
   human spot-checks of the verdicts files.
2. **Judge = generator family** for the DeepSeek baseline (self-preference risk). The
   judge is pinned, so any bias is at least *constant* across runs; relative deltas
   remain meaningful.
3. **pypdf extraction** of Hebrew PDFs is imperfect (occasional reversed/garbled
   fragments); a citation could in principle fail on extraction rather than substance.
   Stage 2's document pipeline (Docling) will replace this path.
4. **temp-0 ≠ deterministic** on TF serving; rescoring the same file can shift a verdict
   or two (~±2%). Treat sub-3-point score differences as noise.
5. **E and Q band formulas are our proxies** — the official internal harness's exact
   formulas are unknown. R and C are the trustworthy comparison numbers.
