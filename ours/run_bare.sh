#!/bin/bash
# Bare-model run (no retrieval) + scoring + ledger entry.
# First arg is a configured role OR any Token Factory model id:
#     ./ours/run_bare.sh baseline "why this run exists"
#     ./ours/run_bare.sh test     "why this run exists"
#     ./ours/run_bare.sh moonshotai/Kimi-K2.6 "how does Kimi compare bare?"
# Everything for the run lands in its own folder: ours/results/<run>/
#     answers.jsonl  verdicts.jsonl  metrics.json  config.json  cases.csv
# NOLEDGER=1 skips the ledger write (ledger is append+regenerate — keep it
# sequential when several runs execute in parallel, then log afterwards).
# Prereq: NEBIUS_API_KEY in env or in .env at repo root.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && source .env && set +a
PY=.venv/bin/python
export OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1
export OPENAI_API_KEY=$NEBIUS_API_KEY

WHO=${1:-test}
WHY=${2:-"(no hypothesis given)"}
if [[ "$WHO" == */* ]]; then
  ROLE=candidate
  MODEL=$WHO
  NAME="bare_$(echo "$MODEL" | tr '/' '_')"
else
  ROLE=$WHO
  MODEL=$($PY -c "import json;print(json.load(open('ours/config.json'))['${ROLE}_model'])")
  NAME="bare_${ROLE}_$(echo "$MODEL" | tr '/' '_')"
fi
DIR="ours/results/$NAME"
mkdir -p "$DIR"

echo "== $ROLE model: $MODEL -> $DIR/"
$PY ours/parallel_runner.py --model "$MODEL" --out "$DIR/answers.jsonl"
$PY ours/stage23/eval_harness.py "$DIR/answers.jsonl" --out "$DIR"
$PY ours/show_case.py --run-csv "$NAME"
if [ "${NOLEDGER:-0}" != "1" ]; then
  $PY ours/log_run.py "$DIR/metrics.json" --model "$MODEL" --role "$ROLE" --why "$WHY"
  echo "== done; ledger + results/STAGE*.md updated — commit ours/ and push"
else
  echo "== done (NOLEDGER=1: ledger skipped — log $DIR/metrics.json afterwards)"
fi
