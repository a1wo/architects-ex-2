# stage23 runs

Stage-2/3 evaluation: same four metrics from the same pinned judge, PLUS judged conversational quality (Q) and the composite competition proxy `65·R + 15·C + 10·E + 10·Q` (see ours/stage23/score.py). Only runs with a judged Q appear here.

24 runs, ranked by total. Judge pinned in `ours/config.json`. Every run folder holds `answers.jsonl` `verdicts.jsonl` `metrics.json` `config.json` `cases.csv`.

| run | model | prompt | correct | partial | incorrect | refusal | halluc | p50_s | Q | E | cost_per_q | total | date | why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [`bare_nvidia_Nemotron-3-Ultra-550b-a55b`](bare_nvidia_Nemotron-3-Ultra-550b-a55b/cases.csv) | nvidia/Nemotron-3-Ultra-550b-a55b | default | 31% | 6% | 40% | 23% | 35% | 3.5s | 77% | 94% | $0.0014 | **35.1** | 2026-07-18 | Nemotron flagship bare: does NVIDIA's biggest model know Israeli insurance? |
| [`bare_moonshotai_Kimi-K2.6`](bare_moonshotai_Kimi-K2.6/cases.csv) | moonshotai/Kimi-K2.6 | default | 38% | 6% | 38% | 19% | 31% | 26.6s | 97% | 20% | $0.0064 | **34.2** | 2026-07-18 | Kimi flagship: strong agentic model, bare |
| [`bare_openai_gpt-oss-120b`](bare_openai_gpt-oss-120b/cases.csv) | openai/gpt-oss-120b | default | 40% | 0% | 60% | 0% | 60% | 5.9s | 95% | 81% | $0.0025 | **33.5** | 2026-07-18 | OpenAI open-weights: different training data mix |
| [`bare_deepseek-ai_DeepSeek-V4-Pro_cite`](bare_deepseek-ai_DeepSeek-V4-Pro_cite/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | cite | 27% | 8% | 46% | 19% | 44% | 11.5s | 88% | 74% | $0.0005 | **30.5** | — | — |
| [`bare_deepseek-ai_DeepSeek-V4-Pro`](bare_deepseek-ai_DeepSeek-V4-Pro/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | default | 31% | 6% | 56% | 6% | 56% | 26.7s | 98% | 50% | $0.0007 | **28.5** | 2026-07-18 | stage23 rescore of base_default answers: judged Q for fair comparison with candidates |
| [`bare_deepseek-ai_DeepSeek-V4-Pro_strict`](bare_deepseek-ai_DeepSeek-V4-Pro_strict/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | strict | 12% | 4% | 6% | 77% | 6% | 2.4s | 44% | 99% | $0.0002 | **27.7** | — | — |
| [`bare_Qwen_Qwen3.5-397B-A17B`](bare_Qwen_Qwen3.5-397B-A17B/cases.csv) | Qwen/Qwen3.5-397B-A17B | default | 31% | 8% | 56% | 4% | 44% | 48.5s | 86% | 12% | $0.0079 | **26.0** | 2026-07-18 | largest Qwen: does scale close the no-docs gap? |
| [`bare_zai-org_GLM-5.2`](bare_zai-org_GLM-5.2/cases.csv) | zai-org/GLM-5.2 | default | 33% | 2% | 48% | 17% | 44% | 61.6s | 84% | 6% | $0.0089 | **25.4** | 2026-07-18 | GLM flagship: already used for cited-runner probe |
| [`bare_meta-llama_Llama-3.3-70B-Instruct_cite`](bare_meta-llama_Llama-3.3-70B-Instruct_cite/cases.csv) | meta-llama/Llama-3.3-70B-Instruct | cite | 19% | 4% | 40% | 38% | 27% | 21.6s | 59% | 50% | $0.0008 | **22.5** | — | — |
| [`bare_nvidia_Nemotron-3-Ultra-550b-a55b_cite`](bare_nvidia_Nemotron-3-Ultra-550b-a55b_cite/cases.csv) | nvidia/Nemotron-3-Ultra-550b-a55b | cite | 2% | 0% | 0% | 98% | 0% | 2.3s | 34% | 99% | $0.0007 | **21.1** | — | — |
| [`bare_meta-llama_Llama-3.3-70B-Instruct_strict`](bare_meta-llama_Llama-3.3-70B-Instruct_strict/cases.csv) | meta-llama/Llama-3.3-70B-Instruct | strict | 0% | 4% | 0% | 96% | 0% | 2.0s | 27% | 100% | $0.0002 | **20.3** | — | — |
| [`bare_nvidia_Nemotron-3-Ultra-550b-a55b_strict`](bare_nvidia_Nemotron-3-Ultra-550b-a55b_strict/cases.csv) | nvidia/Nemotron-3-Ultra-550b-a55b | strict | 0% | 0% | 0% | 100% | 0% | 1.9s | 22% | 100% | $0.0004 | **18.7** | — | — |
| [`bare_zai-org_GLM-5.2_strict`](bare_zai-org_GLM-5.2_strict/cases.csv) | zai-org/GLM-5.2 | strict | 8% | 0% | 4% | 88% | 4% | 29.1s | 33% | 44% | $0.0022 | **18.1** | — | — |
| [`bare_moonshotai_Kimi-K2.6_cite`](bare_moonshotai_Kimi-K2.6_cite/cases.csv) | moonshotai/Kimi-K2.6 | cite | 0% | 0% | 0% | 100% | 0% | 13.6s | 59% | 54% | $0.0034 | **17.8** | — | — |
| [`bare_meta-llama_Llama-3.3-70B-Instruct`](bare_meta-llama_Llama-3.3-70B-Instruct/cases.csv) | meta-llama/Llama-3.3-70B-Instruct | default | 8% | 15% | 58% | 19% | 42% | 39.4s | 77% | 49% | $0.0012 | **17.2** | 2026-07-18 | smaller western open-weights reference point |
| [`bare_moonshotai_Kimi-K2.6_strict`](bare_moonshotai_Kimi-K2.6_strict/cases.csv) | moonshotai/Kimi-K2.6 | strict | 0% | 0% | 2% | 98% | 2% | 6.7s | 28% | 82% | $0.0019 | **17.0** | — | — |
| [`bare_zai-org_GLM-5.2_cite`](bare_zai-org_GLM-5.2_cite/cases.csv) | zai-org/GLM-5.2 | cite | 2% | 0% | 0% | 98% | 0% | 41.0s | 56% | 33% | $0.0040 | **16.7** | — | — |
| [`bare_openai_gpt-oss-120b_cite`](bare_openai_gpt-oss-120b_cite/cases.csv) | openai/gpt-oss-120b | cite | 0% | 0% | 0% | 100% | 0% | 0.6s | 0% | 100% | $0.0000 | **16.5** | — | — |
| [`bare_openai_gpt-oss-120b_strict`](bare_openai_gpt-oss-120b_strict/cases.csv) | openai/gpt-oss-120b | strict | 0% | 0% | 0% | 100% | 0% | 0.6s | 0% | 100% | $0.0000 | **16.5** | — | — |
| [`bare_Qwen_Qwen3-32B_strict`](bare_Qwen_Qwen3-32B_strict/cases.csv) | Qwen/Qwen3-32B | strict | 2% | 2% | 21% | 75% | 15% | 15.3s | 42% | 63% | $0.0010 | **15.0** | — | — |
| [`bare_Qwen_Qwen3.5-397B-A17B_cite`](bare_Qwen_Qwen3.5-397B-A17B_cite/cases.csv) | Qwen/Qwen3.5-397B-A17B | cite | 2% | 0% | 0% | 98% | 0% | 56.2s | 55% | 11% | $0.0081 | **14.2** | — | — |
| [`bare_Qwen_Qwen3.5-397B-A17B_strict`](bare_Qwen_Qwen3.5-397B-A17B_strict/cases.csv) | Qwen/Qwen3.5-397B-A17B | strict | 0% | 0% | 0% | 100% | 0% | 29.0s | 29% | 23% | $0.0058 | **11.7** | — | — |
| [`bare_test_Qwen_Qwen3-32B`](bare_test_Qwen_Qwen3-32B/cases.csv) | Qwen/Qwen3-32B | default | 10% | 0% | 90% | 0% | 75% | 24.2s | 22% | 46% | $0.0017 | **6.8** | 2026-07-18 | small test model bare: how big is the gap the RAG must close? |
| [`bare_Qwen_Qwen3-32B_cite`](bare_Qwen_Qwen3-32B_cite/cases.csv) | Qwen/Qwen3-32B | cite | 4% | 0% | 83% | 12% | 81% | 24.7s | 19% | 47% | $0.0016 | **6.6** | — | — |

Machine-readable copy: `compare_stage23.csv`. Runs scored by the other evaluation: [STAGE1.md](STAGE1.md) — do not compare across the two. All answers side by side: [all_cases.csv](all_cases.csv). Trace one question: `python ours/show_case.py <question-id> [run]`. Regenerate: `python ours/compare_runs.py`.
