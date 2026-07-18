# stage23 runs

Stage-2/3 evaluation: same four metrics from the same pinned judge, PLUS judged conversational quality (Q) and the composite competition proxy `65·R + 15·C + 10·E + 10·Q` (see ours/stage23/score.py).

8 runs, ranked by total. Judge pinned in `ours/config.json`. Every run folder holds `answers.jsonl` `verdicts.jsonl` `metrics.json` `config.json` `cases.csv`.

| run | model | prompt | correct | partial | incorrect | refusal | halluc | p50_s | Q | E | cost_per_q | total | date | why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [`bare_nvidia_Nemotron-3-Ultra-550b-a55b`](bare_nvidia_Nemotron-3-Ultra-550b-a55b/cases.csv) | nvidia/Nemotron-3-Ultra-550b-a55b | default | 31% | 6% | 40% | 23% | 35% | 3.5s | 77% | 94% | $0.0014 | **35.1** | 2026-07-18 | Nemotron flagship bare: does NVIDIA's biggest model know Israeli insurance? |
| [`bare_moonshotai_Kimi-K2.6`](bare_moonshotai_Kimi-K2.6/cases.csv) | moonshotai/Kimi-K2.6 | default | 38% | 6% | 38% | 19% | 31% | 26.6s | 97% | 20% | $0.0064 | **34.2** | 2026-07-18 | Kimi flagship: strong agentic model, bare |
| [`bare_openai_gpt-oss-120b`](bare_openai_gpt-oss-120b/cases.csv) | openai/gpt-oss-120b | default | 40% | 0% | 60% | 0% | 60% | 5.9s | 95% | 81% | $0.0025 | **33.5** | 2026-07-18 | OpenAI open-weights: different training data mix |
| [`bare_deepseek-ai_DeepSeek-V4-Pro`](bare_deepseek-ai_DeepSeek-V4-Pro/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | default | 31% | 6% | 56% | 6% | 56% | 26.7s | 98% | 50% | $0.0007 | **28.5** | 2026-07-18 | stage23 rescore of base_default answers: judged Q for fair comparison with candidates |
| [`bare_Qwen_Qwen3.5-397B-A17B`](bare_Qwen_Qwen3.5-397B-A17B/cases.csv) | Qwen/Qwen3.5-397B-A17B | default | 31% | 8% | 56% | 4% | 44% | 48.5s | 86% | 12% | $0.0079 | **26.0** | 2026-07-18 | largest Qwen: does scale close the no-docs gap? |
| [`bare_zai-org_GLM-5.2`](bare_zai-org_GLM-5.2/cases.csv) | zai-org/GLM-5.2 | default | 33% | 2% | 48% | 17% | 44% | 61.6s | 84% | 6% | $0.0089 | **25.4** | — | — |
| [`bare_meta-llama_Llama-3.3-70B-Instruct`](bare_meta-llama_Llama-3.3-70B-Instruct/cases.csv) | meta-llama/Llama-3.3-70B-Instruct | default | 8% | 15% | 58% | 19% | 42% | 39.4s | 77% | 49% | $0.0012 | **17.2** | 2026-07-18 | smaller western open-weights reference point |
| [`bare_test_Qwen_Qwen3-32B`](bare_test_Qwen_Qwen3-32B/cases.csv) | Qwen/Qwen3-32B | default | 10% | 0% | 90% | 0% | 75% | 24.2s | 22% | 46% | $0.0017 | **6.8** | 2026-07-18 | small test model bare: how big is the gap the RAG must close? |

Machine-readable copy: `compare_stage23.csv`. Runs scored by the other evaluation: [STAGE1.md](STAGE1.md) — do not compare across the two. All answers side by side: [all_cases.csv](all_cases.csv). Trace one question: `python ours/show_case.py <question-id> [run]`. Regenerate: `python ours/compare_runs.py`.
