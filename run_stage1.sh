#!/bin/bash
# Stage 1 in one shot: baseline + 2 prompt strategies, all scored by the harness.
# Prereq: export NEBIUS_API_KEY=...   (shared course key)
set -euo pipefail
cd "$(dirname "$0")"
source .venv/bin/activate
export OPENAI_BASE_URL=https://api.tokenfactory.nebius.com/v1
export OPENAI_API_KEY=$NEBIUS_API_KEY
MODEL=${MODEL:-deepseek-ai/DeepSeek-V4-Pro}
mkdir -p results

STRICT="You are a customer-support assistant for Harel Insurance (Israel). Answer in the language of the question. Answer ONLY if you are certain the answer is correct for Harel's actual policies; otherwise reply exactly: אין לי מספיק מידע כדי לענות על כך בוודאות. Never guess."
CITE="You are a customer-support assistant for Harel Insurance (Israel). Answer in the language of the question. Every factual claim MUST cite its source as (document name, page). If you cannot name the exact Harel document and page, state that you cannot verify the answer."

python baseline_runner.py --model "$MODEL" --out results/base_default.jsonl
python baseline_runner.py --model "$MODEL" --system-prompt "$STRICT" --out results/base_strict.jsonl
python baseline_runner.py --model "$MODEL" --system-prompt "$CITE"   --out results/base_cite.jsonl

for v in default strict cite; do
  echo; echo "=== scoring $v ==="
  python eval_harness.py "results/base_$v.jsonl" --out "results/base_$v"
done
