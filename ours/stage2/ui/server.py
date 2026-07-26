"""Strategy-agnostic chat server. Serves the static UI, a /api/* layer for it,
and the official /ask contract endpoint (default strategy + default DB).

Run: ours/stage2/ui/serve.sh   (uses the docling venv — it has torch/chroma)
"""

import json
import os
import queue
import sys
import threading
import time
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE.parent))          # ours/stage2 → strategies pkg
sys.path.insert(0, str(REPO_ROOT))            # → contract models

# .env at repo root (NEBIUS_API_KEY); loaded here so plain uvicorn works too
for line in (REPO_ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from contract import AskRequest, AskResponse
from strategies import STRATEGIES
from strategies.retrieval import DEFAULT_DB, list_dbs

CONFIG = json.loads((REPO_ROOT / "ours" / "config.json").read_text())
MODELS = list(dict.fromkeys([CONFIG["test_model"], CONFIG["baseline_model"]]))
DEFAULT_STRATEGY = "topk-context-stuffing"

app = FastAPI(title="APEX Ex2 — strategy playground")


class ChatRequest(BaseModel):
    question: str
    strategy: str = DEFAULT_STRATEGY
    db: str = DEFAULT_DB
    model: str = MODELS[0]
    history: list[dict] = []
    params: dict = {}


def run_strategy(req: ChatRequest, progress=None):
    strat = STRATEGIES.get(req.strategy)
    if strat is None:
        raise HTTPException(404, f"unknown strategy {req.strategy!r}")
    if req.db not in list_dbs():
        raise HTTPException(404, f"unknown db {req.db!r}")
    return strat.ask(req.question, history=req.history, db=req.db,
                     model=req.model, progress=progress, **req.params)


@app.get("/api/meta")
def meta():
    return {
        "strategies": [{"name": s.name, "description": s.description,
                        "params": s.params} for s in STRATEGIES.values()],
        "dbs": list_dbs(),
        "models": MODELS,
        "defaults": {"strategy": DEFAULT_STRATEGY, "db": DEFAULT_DB,
                     "model": MODELS[0]},
    }


@app.post("/api/chat")
def api_chat(req: ChatRequest):
    try:
        return asdict(run_strategy(req))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


# SSE: emits {"type": "stage", "stage", "t"} as the strategy enters each stage
# (t = server seconds since request start; the next stage event or the final
# {"type": "result"|"error"} event closes the previous stage), so the UI debug
# panel can show live per-stage timings.
@app.post("/api/chat/stream")
def api_chat_stream(req: ChatRequest):
    q: queue.Queue = queue.Queue()
    t0 = time.perf_counter()

    def emit(ev):
        q.put({**ev, "t": round(time.perf_counter() - t0, 3)})

    def run():
        try:
            r = run_strategy(req, progress=lambda s: emit({"type": "stage",
                                                           "stage": s}))
            emit({"type": "result", "data": asdict(r)})
        except HTTPException as e:
            emit({"type": "error", "detail": e.detail})
        except Exception as e:
            emit({"type": "error", "detail": f"{type(e).__name__}: {e}"})
        q.put(None)

    threading.Thread(target=run, daemon=True).start()

    def gen():
        while (ev := q.get()) is not None:
            yield f"data: {json.dumps(ev)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    r = run_strategy(ChatRequest(question=req.question))
    return AskResponse(answer=r.answer,
                       citations=[asdict(c) for c in r.citations],
                       domain=r.domain, latency_ms=r.latency_ms,
                       cost_usd=r.cost_usd)


# cited files are corpus-relative → /corpus/<file>#page=N opens the PDF there
app.mount("/corpus", StaticFiles(directory=REPO_ROOT / "corpus"))
app.mount("/", StaticFiles(directory=HERE / "static", html=True))
