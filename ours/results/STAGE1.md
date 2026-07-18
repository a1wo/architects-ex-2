# stage1 runs

Stage-1 evaluation: the four spec metrics (relevance, hallucination, citations, latency). No judged conversational quality, no composite score.

4 runs, ranked by correct. Judge pinned in `ours/config.json`. Every run folder holds `answers.jsonl` `verdicts.jsonl` `metrics.json` `config.json` `cases.csv`.

| run | model | prompt | correct | partial | incorrect | refusal | halluc | p50_s | date | why |
|---|---|---|---|---|---|---|---|---|---|---|
| [`citation_selftest`](citation_selftest/cases.csv) | none (synthetic: answers are the ground truth — harness self-test) | — | 100% | 0% | 0% | 0% | 0% | 1.0s | — | — |
| [`base_default`](base_default/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | default | 31% | 4% | 58% | 6% | 58% | 26.7s | 2026-07-18 | Stage-1 bar: strongest open-weights model, bare, provided prompt |
| [`base_cite`](base_cite/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | cite | 25% | 10% | 56% | 8% | 56% | 22.5s | 2026-07-18 | prompt strategy 2: always-cite (it fabricates) |
| [`base_strict`](base_strict/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | strict | 12% | 6% | 4% | 77% | 4% | 16.4s | 2026-07-18 | prompt strategy 1: refuse-if-unsure |

Machine-readable copy: `compare_stage1.csv`. Runs scored by the other evaluation: [STAGE23.md](STAGE23.md) — do not compare across the two. All answers side by side: [all_cases.csv](all_cases.csv). Trace one question: `python ours/show_case.py <question-id> [run]`. Regenerate: `python ours/compare_runs.py`.
