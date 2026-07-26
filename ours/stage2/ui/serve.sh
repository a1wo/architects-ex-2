#!/usr/bin/env bash
# Chat UI: http://localhost:${PORT:-8010}
# Uses the docling venv — the only one with torch + sentence-transformers
# (needed to embed queries) alongside chromadb/fastapi/openai.
set -e
cd "$(dirname "$0")/../../.."
exec ours/stage2/parser_bench/.venv-docling/bin/python -m uvicorn server:app \
    --app-dir ours/stage2/ui --port "${PORT:-8010}" "$@"
