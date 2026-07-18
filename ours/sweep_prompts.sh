#!/bin/bash
# Prompt-strategy sweep: every model x {strict, cite} system prompts, scored with
# the stage23 harness. (The x default runs already exist as bare_<model>.)
# Throttled to 3 concurrent runs (36 in-flight requests max) — shared course key.
#
#     ./ours/sweep_prompts.sh
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && source .env && set +a
: "${NEBIUS_API_KEY:?put the key in .env at repo root}"
PY=.venv/bin/python
export OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1
export OPENAI_API_KEY=$NEBIUS_API_KEY

MODELS=(
  deepseek-ai/DeepSeek-V4-Pro
  zai-org/GLM-5.2
  moonshotai/Kimi-K2.6
  nvidia/Nemotron-3-Ultra-550b-a55b
  openai/gpt-oss-120b
  Qwen/Qwen3.5-397B-A17B
  Qwen/Qwen3-32B
  meta-llama/Llama-3.3-70B-Instruct
)

STRICT="You are a customer-support assistant for Harel Insurance (Israel). Answer in the language of the question. Answer ONLY if you are certain the answer is correct for Harel's actual policies; otherwise reply exactly: אין לי מספיק מידע כדי לענות על כך בוודאות. Never guess."
CITE="You are a customer-support assistant for Harel Insurance (Israel). Answer in the language of the question. Every factual claim MUST cite its source as (document name, page). If you cannot name the exact Harel document and page, state that you cannot verify the answer."

one_run () {  # model prompt_name prompt_text
  local model=$1 pname=$2 ptext=$3
  local dir="ours/results/bare_$(echo "$model" | tr '/' '_')_${pname}"
  if [ -f "$dir/metrics.json" ]; then echo "skip $dir (already scored)"; return; fi
  $PY ours/parallel_runner.py --model "$model" --prompt-name "$pname" \
      --system-prompt "$ptext" --out "$dir/answers.jsonl" \
    && $PY ours/stage23/eval_harness.py "$dir/answers.jsonl" \
    || echo "FAILED: $dir"
}

for model in "${MODELS[@]}"; do
  for pname in strict cite; do
    [ "$pname" = strict ] && ptext="$STRICT" || ptext="$CITE"
    while [ "$(jobs -rp | wc -l)" -ge 3 ]; do sleep 5; done   # throttle
    one_run "$model" "$pname" "$ptext" &
  done
done
wait

$PY ours/show_case.py          # regenerate per-run cases.csv + INDEX
$PY ours/compare_runs.py       # ranked tables + CSVs
echo SWEEP_DONE
