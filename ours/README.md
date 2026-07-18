# Team Guide — APEX Ex2: Harel Insurance Support Bot

Everything in **`ours/`** is ours. Everything at the **repo root** is the given
starter kit, untouched (`baseline_runner.py`, `tf_client.py`, `contract.py`,
`get_corpus.py`, `reference_questions.json`, `submit_runner.py`).

## What's going on (status)

- **Stage 1 (baseline + eval harness) — DONE**, see `stage1/STAGE1_REPORT.md`.
  Best bare-model score ≈ **42/100** on our proxy scoring. Bare models know
  Israeli insurance *law* but not *Harel* (travel: 0% correct), hallucinate
  confidently (56%), and cite nothing real.
- **Stage 2 (RAG, due July 26) — NEXT**: chunk the corpus, build retrieval,
  ground every answer in real {file, page} citations.
- **Stage 3 (agent + `/ask` API, due Aug 2)**: routing, contract, blind-set submission.

## One-time setup

```bash
git clone https://github.com/a1wo/architects-ex-2 && cd architects-ex-2
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/pip install pypdf
echo 'NEBIUS_API_KEY=<the shared course key>' > .env   # NEVER commit; get it from the course channel
.venv/bin/python get_corpus.py                          # downloads corpus/ (~105MB, gitignored)
```

## Running an experiment (the loop)

```bash
./ours/run_bare.sh test "why I'm running this"      # test_model from config.json
./ours/run_bare.sh baseline "why I'm running this"  # baseline_model
```

One command = answer all 48 dev questions → score with the judge → **log to the
ledger** → regenerate the run table. Then `git add ours/ && git commit && git pull --rebase && git push`.

Scoring an answers file you produced some other way (e.g. the future RAG system):

```bash
mkdir -p ours/results/<name>   # every run gets its own folder:
                               # answers.jsonl verdicts.jsonl metrics.json config.json cases.csv
.venv/bin/python ours/stage23/eval_harness.py <answers.jsonl> --out ours/results/<name>
.venv/bin/python ours/log_run.py ours/results/<name>/metrics.json --model <model> --role rag --why "<hypothesis>"
.venv/bin/python ours/show_case.py   # regenerate per-run cases.csv, all_cases.csv, results/INDEX.md
```

## The files

| File | What it is |
|---|---|
| `config.json` | **Single source of truth for models.** `baseline_model` (bar to beat) vs `test_model` (our generator) vs `judge_model` (pinned forever — never bump mid-exercise, scores stop being comparable) |
|  `stage1/eval_harness.py` + `stage23/eval_harness.py` | The measuring stick. 3 LLM-judge prompts: relevance (`correct/partial/incorrect/refusal` + confidence), citation accuracy (resolves each cited {file,page} to the real corpus page, judges `full/partial/none`, nonexistent → `invalid`), conversational quality (1–5 clarity/tone/flow). Plus latency stats. Hallucination = confident AND contradicts ground truth; refusals counted separately on purpose |
|  `stage23/score.py` | Composite score: `65·R + 15·C + 10·E + 10·Q` (proxy of the official rubric). E = latency+cost bands — arithmetic, no judge |
| `log_run.py` | Experiment ledger. Appends what/why/result + config snapshot + git rev to `experiments.jsonl`, regenerates the per-evaluation pages |
| `results/STAGE1.md` + `results/STAGE23.md` | **Generated** — one ranked run table per evaluation type (never compare across the two). Rebuild: `python ours/compare_runs.py` |
| `experiments.jsonl` | Append-only ledger, one JSON per run (the full memory of what we tried and why) |
|  `stage1/selftest_citations.py` | Proves citation scoring works (real ground-truth pages → `full`, bogus file → `invalid`). Run after touching the harness |
| `run_bare.sh` | Bare-model run + score + log, `baseline` or `test` role |
|   `stage1/STAGE1_REPORT.md` | Stage-1 deliverable (metrics + the 3 required analysis answers) |
| `results/` | Raw answers, per-question judge verdicts, metrics JSONs — committed (only `.log` ignored) |

## Rules we follow

- **Shared API key**: all calls through Token Factory cost from a shared course pool — watch the `[tf_client]` cost lines, don't burn it. Key lives in `.env` (gitignored) only.
- **Don't re-scrape harel-group.co.il** — the graded corpus is the frozen HF snapshot (`get_corpus.py`).
- **No fine-tuning/LoRA/RL** — all intelligence goes in the system around the model.
- **Judge stays pinned** (`config.json`). If we ever must change it, rescore *everything* in the same PR.
- Given files at repo root stay untouched; our code lives in `ours/`.
