#!/bin/bash
# Bare-model run (no retrieval) + scoring + ledger entry, for either configured model:
#     ./ours/run_bare.sh baseline "why this run exists"
#     ./ours/run_bare.sh test     "why this run exists"
# Prereq: NEBIUS_API_KEY in env or in .env at repo root.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && source .env && set +a
PY=.venv/bin/python
export OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1
export OPENAI_API_KEY=$NEBIUS_API_KEY

ROLE=${1:-test}
WHY=${2:-"(no hypothesis given)"}
MODEL=$($PY -c "import json;print(json.load(open('ours/config.json'))['${ROLE}_model'])")
NAME="bare_${ROLE}_$(echo "$MODEL" | tr '/' '_')"
mkdir -p ours/results

echo "== $ROLE model: $MODEL -> ours/results/$NAME.jsonl"
$PY baseline_runner.py --model "$MODEL" --out "ours/results/$NAME.jsonl"
$PY ours/eval_harness.py "ours/results/$NAME.jsonl" --out "ours/results/$NAME"
$PY ours/log_run.py "ours/results/${NAME}_metrics.json" --model "$MODEL" --role "$ROLE" --why "$WHY"
echo "== done; ledger + RUNS.md updated — commit ours/ and push"
