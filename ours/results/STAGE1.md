# stage1 runs

Stage-1 evaluation: the four spec metrics (relevance, hallucination, citations, latency). This page shows the stage-1 view of EVERY run: stage23-scored runs are included because stage23 embeds the full stage-1 evaluation (same pinned judge, same prompts) — see the `scored_by` column. No conversational quality, no composite score here.

27 runs, ranked by correct. Judge pinned in `ours/config.json`. Every run folder holds `answers.jsonl` `verdicts.jsonl` `metrics.json` `config.json` `cases.csv`.

| run | model | prompt | correct | partial | incorrect | refusal | halluc | p50_s | scored_by | date | why |
|---|---|---|---|---|---|---|---|---|---|---|---|
| [`bare_openai_gpt-oss-120b`](bare_openai_gpt-oss-120b/cases.csv) | openai/gpt-oss-120b | default | 40% | 0% | 60% | 0% | 60% | 5.9s | stage23 | 2026-07-18 | OpenAI open-weights: different training data mix |
| [`bare_moonshotai_Kimi-K2.6`](bare_moonshotai_Kimi-K2.6/cases.csv) | moonshotai/Kimi-K2.6 | default | 38% | 6% | 38% | 19% | 31% | 26.6s | stage23 | 2026-07-18 | Kimi flagship: strong agentic model, bare |
| [`bare_zai-org_GLM-5.2`](bare_zai-org_GLM-5.2/cases.csv) | zai-org/GLM-5.2 | default | 33% | 2% | 48% | 17% | 44% | 61.6s | stage23 | 2026-07-18 | GLM flagship: already used for cited-runner probe |
| [`bare_Qwen_Qwen3.5-397B-A17B`](bare_Qwen_Qwen3.5-397B-A17B/cases.csv) | Qwen/Qwen3.5-397B-A17B | default | 31% | 8% | 56% | 4% | 44% | 48.5s | stage23 | 2026-07-18 | largest Qwen: does scale close the no-docs gap? |
| [`bare_deepseek-ai_DeepSeek-V4-Pro`](bare_deepseek-ai_DeepSeek-V4-Pro/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | default | 31% | 6% | 56% | 6% | 56% | 26.7s | stage23 | 2026-07-18 | stage23 rescore of base_default answers: judged Q for fair comparison with candidates |
| [`bare_nvidia_Nemotron-3-Ultra-550b-a55b`](bare_nvidia_Nemotron-3-Ultra-550b-a55b/cases.csv) | nvidia/Nemotron-3-Ultra-550b-a55b | default | 31% | 6% | 40% | 23% | 35% | 3.5s | stage23 | 2026-07-18 | Nemotron flagship bare: does NVIDIA's biggest model know Israeli insurance? |
| [`base_default`](base_default/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | default | 31% | 4% | 58% | 6% | 58% | 26.7s | stage1 | 2026-07-18 | Stage-1 bar: strongest open-weights model, bare, provided prompt |
| [`bare_deepseek-ai_DeepSeek-V4-Pro_cite`](bare_deepseek-ai_DeepSeek-V4-Pro_cite/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | cite | 27% | 8% | 46% | 19% | 44% | 11.5s | stage23 | — | — |
| [`base_cite`](base_cite/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | cite | 25% | 10% | 56% | 8% | 56% | 22.5s | stage1 | 2026-07-18 | prompt strategy 2: always-cite (it fabricates) |
| [`bare_meta-llama_Llama-3.3-70B-Instruct_cite`](bare_meta-llama_Llama-3.3-70B-Instruct_cite/cases.csv) | meta-llama/Llama-3.3-70B-Instruct | cite | 19% | 4% | 40% | 38% | 27% | 21.6s | stage23 | — | — |
| [`bare_deepseek-ai_DeepSeek-V4-Pro_strict`](bare_deepseek-ai_DeepSeek-V4-Pro_strict/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | strict | 12% | 4% | 6% | 77% | 6% | 2.4s | stage23 | — | — |
| [`base_strict`](base_strict/cases.csv) | deepseek-ai/DeepSeek-V4-Pro | strict | 12% | 6% | 4% | 77% | 4% | 16.4s | stage1 | 2026-07-18 | prompt strategy 1: refuse-if-unsure |
| [`bare_test_Qwen_Qwen3-32B`](bare_test_Qwen_Qwen3-32B/cases.csv) | Qwen/Qwen3-32B | default | 10% | 0% | 90% | 0% | 75% | 24.2s | stage23 | 2026-07-18 | small test model bare: how big is the gap the RAG must close? |
| [`bare_meta-llama_Llama-3.3-70B-Instruct`](bare_meta-llama_Llama-3.3-70B-Instruct/cases.csv) | meta-llama/Llama-3.3-70B-Instruct | default | 8% | 15% | 58% | 19% | 42% | 39.4s | stage23 | 2026-07-18 | smaller western open-weights reference point |
| [`bare_zai-org_GLM-5.2_strict`](bare_zai-org_GLM-5.2_strict/cases.csv) | zai-org/GLM-5.2 | strict | 8% | 0% | 4% | 88% | 4% | 29.1s | stage23 | — | — |
| [`bare_Qwen_Qwen3-32B_cite`](bare_Qwen_Qwen3-32B_cite/cases.csv) | Qwen/Qwen3-32B | cite | 4% | 0% | 83% | 12% | 81% | 24.7s | stage23 | — | — |
| [`bare_Qwen_Qwen3-32B_strict`](bare_Qwen_Qwen3-32B_strict/cases.csv) | Qwen/Qwen3-32B | strict | 2% | 2% | 21% | 75% | 15% | 15.3s | stage23 | — | — |
| [`bare_Qwen_Qwen3.5-397B-A17B_cite`](bare_Qwen_Qwen3.5-397B-A17B_cite/cases.csv) | Qwen/Qwen3.5-397B-A17B | cite | 2% | 0% | 0% | 98% | 0% | 56.2s | stage23 | — | — |
| [`bare_nvidia_Nemotron-3-Ultra-550b-a55b_cite`](bare_nvidia_Nemotron-3-Ultra-550b-a55b_cite/cases.csv) | nvidia/Nemotron-3-Ultra-550b-a55b | cite | 2% | 0% | 0% | 98% | 0% | 2.3s | stage23 | — | — |
| [`bare_zai-org_GLM-5.2_cite`](bare_zai-org_GLM-5.2_cite/cases.csv) | zai-org/GLM-5.2 | cite | 2% | 0% | 0% | 98% | 0% | 41.0s | stage23 | — | — |
| [`bare_Qwen_Qwen3.5-397B-A17B_strict`](bare_Qwen_Qwen3.5-397B-A17B_strict/cases.csv) | Qwen/Qwen3.5-397B-A17B | strict | 0% | 0% | 0% | 100% | 0% | 29.0s | stage23 | — | — |
| [`bare_meta-llama_Llama-3.3-70B-Instruct_strict`](bare_meta-llama_Llama-3.3-70B-Instruct_strict/cases.csv) | meta-llama/Llama-3.3-70B-Instruct | strict | 0% | 4% | 0% | 96% | 0% | 2.0s | stage23 | — | — |
| [`bare_moonshotai_Kimi-K2.6_cite`](bare_moonshotai_Kimi-K2.6_cite/cases.csv) | moonshotai/Kimi-K2.6 | cite | 0% | 0% | 0% | 100% | 0% | 13.6s | stage23 | — | — |
| [`bare_moonshotai_Kimi-K2.6_strict`](bare_moonshotai_Kimi-K2.6_strict/cases.csv) | moonshotai/Kimi-K2.6 | strict | 0% | 0% | 2% | 98% | 2% | 6.7s | stage23 | — | — |
| [`bare_nvidia_Nemotron-3-Ultra-550b-a55b_strict`](bare_nvidia_Nemotron-3-Ultra-550b-a55b_strict/cases.csv) | nvidia/Nemotron-3-Ultra-550b-a55b | strict | 0% | 0% | 0% | 100% | 0% | 1.9s | stage23 | — | — |
| [`bare_openai_gpt-oss-120b_cite`](bare_openai_gpt-oss-120b_cite/cases.csv) | openai/gpt-oss-120b | cite | 0% | 0% | 0% | 100% | 0% | 0.6s | stage23 | — | — |
| [`bare_openai_gpt-oss-120b_strict`](bare_openai_gpt-oss-120b_strict/cases.csv) | openai/gpt-oss-120b | strict | 0% | 0% | 0% | 100% | 0% | 0.6s | stage23 | — | — |

Machine-readable copy: `compare_stage1.csv`. Runs scored by the other evaluation: [STAGE23.md](STAGE23.md) — do not compare across the two. All answers side by side: [all_cases.csv](all_cases.csv). Trace one question: `python ours/show_case.py <question-id> [run]`. Regenerate: `python ours/compare_runs.py`.
