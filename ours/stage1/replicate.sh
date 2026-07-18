#!/bin/bash
# Replicate ALL of Stage 1 from scratch: the DeepSeek baseline with 3 prompt
# strategies + the small test model, each scored by the judge and logged to the
# ledger. ~200 model calls + ~400 judge calls ≈ $0.5 of the shared pool.
# Results land in ours/results/, table in ours/RUNS.md.
#
#     ./ours/stage1/replicate.sh
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

run () {  # name, extra args..., why
  local name=$1 why=$2; shift 2
  $PY baseline_runner.py --model "$BASE" "$@" --out "ours/results/$name.jsonl"
  $PY ours/stage1/eval_harness.py "ours/results/$name.jsonl" --out "ours/results/$name"
  $PY ours/log_run.py "ours/results/${name}_metrics.json" --model "$BASE" --role baseline --why "$why"
}

run base_default "Stage-1 bar: strongest open-weights model, bare, provided prompt"
run base_strict  "prompt strategy 1: refuse-if-unsure" --system-prompt "$STRICT"
run base_cite    "prompt strategy 2: always-cite (it fabricates)" --system-prompt "$CITE"
./ours/run_bare.sh test "small test model bare: how big is the gap the RAG must close?"

echo; echo "Stage 1 replicated. See ours/RUNS.md. Inspect any number:"
echo "  $PY ours/show_examples.py base_default hallucination"
