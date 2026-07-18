# Run Table

Every scored run of the system, with an estimated competition score. Add a row per run — never overwrite; this is the team's progress ledger.

## Estimated competition score (our proxy of the official rubric)

`score = 65·R + 15·C + 10·E + 10·Q` out of 100 (+5 voice, +5 UI at the end), where:

- **R (relevance)** = (correct + 0.5·partial) / questions — from `eval_harness.py` (judge: `deepseek-ai/DeepSeek-V4-Pro`, temp 0, pinned)
- **C (citations)** = (full + 0.5·partial) / citations judged; 0 when the system emits no valid citations
- **E (efficiency)** = ½·latency + ½·cost, latency = 1.0 at p50 ≤ 2s falling linearly to 0.0 at 20s; cost = 1.0 at ≤ $0.001/question falling linearly to 0.0 at $0.01/q (cost from tf_client estimate: $0.5/M in, $2/M out)
- **Q (conversational)** = not yet judge-measured. Assumed **0.70** for runs that answer fluently, **0.30** for runs that refuse most questions. Replace with a judged metric in Stage 2.

The official internal harness's E and Q formulas are unknown — treat E/Q as ±5 pts of slack. **R and C are the honest signal; only compare runs scored with the same judge.**

## Runs

All runs: 48 dev questions (`reference_questions.json`), bare model (no retrieval), `deepseek-ai/DeepSeek-V4-Pro`, 2026-07-18.

| # | run | correct | partial | incorrect | refusal | halluc. | citations (full/judged) | latency p50/mean/p95 ms | $/question | R | C | E | Q | **est. score /100** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `base_default` | 17/48 | 1/48 | 28/48 | 2/48 | 27/48 (56.3%) | 0/0 | 6360 / 9292 / 27148 | $0.00068 | .365 | .00 | .88 | .70 | **39.5** |
| 2 | `base_strict` | 6/48 | 0/48 | 5/48 | 37/48 | 4/48 (8.3%) | 0/0 | 1283 / 2289 / 6362 | $0.00016 | .125 | .00 | 1.00 | .30 | **21.1** |
| 3 | `base_cite` | 16/48 | 3/48 | 19/48 | 10/48 | 19/48 (39.6%) | 0/0 (in-text cites all fabricated) | 5516 / 7082 / 17074 | $0.00053 | .365 | .00 | .90 | .70 | **39.7** |

**Score breakdown, best run (#3 `base_cite`):** relevance 65×0.365 = **23.7** · citations 15×0 = **0.0** · efficiency 10×0.902 = **9.0** · conversational 10×0.70 = **7.0** → **39.7**

## Current standing

- **Best baseline: ≈ 39.7/100** (runs #1 and #3 are statistically tied on relevance; #3 hallucinates less).
- **Up to 15 citation points sit at exactly 0** — no run produced a single resolvable {file, page}. This is Stage 2's cheapest large win.
- The relevance ceiling without documents is ~36.5% → **max ~24/65 relevance points**; every point above that must come from retrieval.
- Hallucination rate is not directly scored, but 27/48 confident-wrong answers will bleed into both R and Q on the blind set.

## Reproduce / add a run

```bash
export NEBIUS_API_KEY=...        # never commit; lives in .env (gitignored)
./run_stage1.sh                  # or: python eval_harness.py <answers.jsonl> --out results/<name>
```

Then append a row here using `results/<name>_metrics.json` (exact counts = fraction × 48) and the formula above.
