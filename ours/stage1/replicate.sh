#!/bin/bash
# Replicate ALL of Stage 1 from scratch: the DeepSeek baseline with 3 prompt
# strategies + the small test model, each scored by the judge and logged to the
# ledger. ~200 model calls + ~400 judge calls ≈ $0.5 of the shared pool.
# Results land in ours/results/<run>/, tables in ours/results/STAGE1.md + STAGE23.md.
#
#     ./ours/stage1/replicate.sh

export $(cat .env | xargs)

set -euo pipefail
cd "$(dirname "$0")/../.."     # repo root (this script lives in ours/stage1/)
[ -f .env ] && set -a && source .env && set +a
if [ -z "${NEBIUS_API_KEY:-}" ]; then
  echo "NEBIUS_API_KEY not set — put it in .env at the repo root (see ours/README.md)" >&2
  exit 1
fi
PY=.venv/bin/python
export OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1
export OPENAI_API_KEY=$NEBIUS_API_KEY
BASE=$($PY -c "import json;print(json.load(open('ours/config.json'))['baseline_model'])")
mkdir -p ours/results

STRICT="You are a customer-support assistant for Harel Insurance (Israel). Answer in the language of the question. Answer ONLY if you are certain the answer is correct for Harel's actual policies; otherwise reply exactly: אין לי מספיק מידע כדי לענות על כך בוודאות. Never guess."
CITE="You are a customer-support assistant for Harel Insurance (Israel). Answer in the language of the question. Every factual claim MUST cite its source as (document name, page). If you cannot name the exact Harel document and page, state that you cannot verify the answer."

run () {  # name, why, prompt-name, extra runner args... — answers + scores one variant
  local name=$1 why=$2 pname=$3; shift 3
  echo "Running $name: $why"
  mkdir -p "ours/results/$name"
  $PY ours/parallel_runner.py --model "$BASE" --prompt-name "$pname" "$@" \
      --out "ours/results/$name/answers.jsonl"
  $PY ours/stage1/eval_harness.py "ours/results/$name/answers.jsonl" --out "ours/results/$name"
}

# all three variants concurrently; each is internally parallel too
run base_default "Stage-1 bar: strongest open-weights model, bare, provided prompt" default &
run base_strict  "prompt strategy 1: refuse-if-unsure" strict --system-prompt "$STRICT" &
run base_cite    "prompt strategy 2: always-cite (it fabricates)" cite --system-prompt "$CITE" &
wait

# ledger writes are append+regenerate — keep them sequential
$PY ours/log_run.py ours/results/base_default/metrics.json --model "$BASE" --role baseline --why "Stage-1 bar: strongest open-weights model, bare, provided prompt"
$PY ours/log_run.py ours/results/base_strict/metrics.json  --model "$BASE" --role baseline --why "prompt strategy 1: refuse-if-unsure"
$PY ours/log_run.py ours/results/base_cite/metrics.json    --model "$BASE" --role baseline --why "prompt strategy 2: always-cite (it fabricates)"
./ours/run_bare.sh test "small test model bare: how big is the gap the RAG must close?"

# per-run cases.csv + combined all_cases.csv + INDEX.md over every run folder
$PY ours/show_case.py

echo; echo "Stage 1 replicated. See ours/results/STAGE1.md + STAGE23.md. Inspect any number:"
echo "  $PY ours/show_examples.py base_default hallucination"
echo "  $PY ours/show_case.py dev-13-car-easy"
