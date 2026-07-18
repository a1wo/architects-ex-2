#!/bin/bash
# Bare-model run (no retrieval) + scoring, for either configured model:
#     ./ours/run_bare.sh baseline    # baseline_model from ours/config.json
#     ./ours/run_bare.sh test        # test_model  (default)
# Prereq: NEBIUS_API_KEY in env or in .env at repo root.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && source .env && set +a
source .venv/bin/activate
export OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1
export OPENAI_API_KEY=$NEBIUS_API_KEY

ROLE=${1:-test}
MODEL=$(python -c "import json;print(json.load(open('ours/config.json'))['${ROLE}_model'])")
NAME="bare_${ROLE}_$(echo "$MODEL" | tr '/' '_')"
mkdir -p ours/results

echo "== $ROLE model: $MODEL -> ours/results/$NAME.jsonl"
python baseline_runner.py --model "$MODEL" --out "ours/results/$NAME.jsonl"
python ours/eval_harness.py "ours/results/$NAME.jsonl" --out "ours/results/$NAME"
echo "== done; append the row to ours/RUNS.md from ours/results/${NAME}_metrics.json"
