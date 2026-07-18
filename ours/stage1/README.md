# Stage 1 — Baseline & Evaluation Harness (due July 19)

Point-by-point answers to the Stage-1 requirements in
[`exercise2_customer_support_agent.md`](../../exercise2_customer_support_agent.md).
**The deliverable is [`BASELINE_REPORT.md`](BASELINE_REPORT.md)**; full measurement detail per metric: [`METHODOLOGY.md`](METHODOLOGY.md) (1 page: metrics table + the three required answers).

## 1. Measure the baseline ✅

- Model: `deepseek-ai/DeepSeek-V4-Pro` — the strongest open-weights model on Token Factory
  (role `baseline_model` in [`../config.json`](../config.json)).
- Ran all 48 dev questions bare (no documents) via the provided `baseline_runner.py`
  through Token Factory (`OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1`),
  key via `tf_client`-style shared-pool etiquette (~$0.03/run in estimated cost).
- Raw answers: [`../results/base_default.jsonl`](../results/base_default.jsonl) (+ `strict`, `cite` variants).
- Result: **35% correct, 56% hallucination rate, zero real citations** — the bar Stage 2 must beat.

## 2. Evaluation harness ✅

[`../eval_harness.py`](../eval_harness.py) scores any answers JSONL against the dev ground truths:

| required metric | how we measure it |
|---|---|
| Answer relevance | LLM-as-judge (pinned `deepseek-ai/DeepSeek-V4-Pro`, temp 0, forced JSON) → `correct / partial / incorrect / refusal` + `confident` flag |
| Hallucination rate | `confident AND contradicts ground truth`. Refusals are a separate class — "I don't know" is *not* a hallucination, and we report it on its own line |
| Citation accuracy | every cited `{file, page}` is resolved to the actual corpus page (pypdf / page text); judge rates whether that page establishes the ground-truth answer (`full/partial/none`); nonexistent file or page → `invalid`, counted against. No fixed source list — any establishing page earns credit |
| Latency | per-question, aggregated mean / p50 / p95 |
| (bonus) Conversational quality | judged 1–5 clarity/tone/flow, normalized to Q ∈ [0,1] — mirrors the final grading's 10% |

Sanity check: [`../selftest_citations.py`](../selftest_citations.py) — ground-truth pages score `full`,
a bogus file scores `invalid`. Composite competition score: [`../score.py`](../score.py) (65R+15C+10E+10Q).
Wired into the loop from day one: every run auto-logs to [`../experiments.jsonl`](../experiments.jsonl) → [`../RUNS.md`](../RUNS.md).

## 3. Two prompt strategies ✅

| strategy | what shifted |
|---|---|
| **"Answer only if certain"** (strict) | hallucinations 56% → **8%**, but refusals explode to 77% and correct collapses 35% → 13%. The knob exists; it's just brutally blunt without retrieval |
| **"Always cite your source"** (cite) | correctness ~unchanged (31%), hallucinations dip to 42%, but the model **fabricates** authoritative-looking citations (real-sounding docs, "סעיף 4.2.1, עמוד 7") — the most dangerous failure mode for an insurer |

Failure-profile takeaway: prompting alone trades correctness against refusals; only grounding can improve both.

## The three report questions ✅

Answered in [`BASELINE_REPORT.md`](BASELINE_REPORT.md): (1) the bare model succeeds on Israeli
insurance *law*/norms — that's what's in its training data — and fails on Harel-specific
numbers (travel 0%); (2) it is wrong *confidently* (56%), and for an insurer a confident
wrong answer is worse than "I don't know"; (3) judge-disagreement case `dev-13-car-easy`,
where a reasonable conditional answer was scored as a hallucination — LLM judges anchor
on ground-truth phrasing, so small score deltas need human spot-checks.
