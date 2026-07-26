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

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import stt
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


# Local Whisper STT (see stt.py). Load/unload are explicit so the ~GB model
# only occupies RAM while the mic feature is in use; load returns immediately
# and the UI polls GET /api/stt until status == "loaded".
@app.get("/api/stt")
def stt_status():
    return {**stt.status(), "models": stt.MODELS}


@app.post("/api/stt/load")
def stt_load(model: str = stt.MODELS[0]):
    if model not in stt.MODELS:
        raise HTTPException(404, f"unknown stt model {model!r}")
    return stt.load(model)


@app.post("/api/stt/unload")
def stt_unload():
    return stt.unload()


@app.post("/api/stt/transcribe")
def stt_transcribe(audio: UploadFile):
    try:
        return stt.transcribe(audio.file.read())
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise HTTPException(500, f"{type(e).__name__}: {e}")


# ---- results browser (UI "Runs" / analysis tabs): read-only over ours/results/
RESULTS_DIR = REPO_ROOT / "ours" / "results"
LEDGER = REPO_ROOT / "ours" / "experiments.jsonl"

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "stage23_score", REPO_ROOT / "ours" / "stage23" / "score.py")
_score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_score)


def _ledger_by_run():
    out = {}
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            try:
                r = json.loads(line)
                out[r.get("name")] = r
            except json.JSONDecodeError:
                continue
    return out


@app.get("/api/runs")
def runs():
    ledger = _ledger_by_run()
    out = []
    for d in sorted(RESULTS_DIR.iterdir()):
        mp = d / "metrics.json"
        if not d.is_dir() or not mp.exists() or "selftest" in d.name:
            continue
        m = json.loads(mp.read_text())
        try:
            s = _score.compute(mp)
        except Exception:
            s = None
        led = ledger.get(d.name, {})
        out.append({"run": d.name, "harness": m.get("harness"), "n": m.get("n"),
                    "relevance": m.get("relevance"),
                    "hallucination_rate": m.get("hallucination_rate"),
                    "citations": m.get("citations"),
                    "latency_ms": m.get("latency_ms"),
                    "conversational": m.get("conversational"),
                    "correct_by_domain": m.get("correct_by_domain"),
                    "model": led.get("model"), "role": led.get("role"),
                    "why": led.get("why"), "ts": led.get("ts"), "score": s})
    out.sort(key=lambda r: (r["score"] or {}).get("total", -1), reverse=True)
    return out


@app.get("/api/runs/{name}")
def run_detail(name: str):
    d = RESULTS_DIR / name
    if "/" in name or ".." in name or not (d / "answers.jsonl").exists():
        raise HTTPException(404, f"unknown run {name!r}")
    questions = json.load(open(REPO_ROOT / "reference_questions.json"))
    if isinstance(questions, dict):
        questions = questions["questions"]
    answers = {r["id"]: r for r in
               map(json.loads, open(d / "answers.jsonl", encoding="utf-8"))}
    verdicts = {}
    if (d / "verdicts.jsonl").exists():
        verdicts = {r["id"]: r for r in
                    map(json.loads, open(d / "verdicts.jsonl", encoding="utf-8"))}
    items = []
    for q in questions:
        a = answers.get(q["id"]) or {}
        v = verdicts.get(q["id"]) or {}
        rel = v.get("relevance") or {}
        items.append({
            "id": q["id"], "domain": q["domain"], "difficulty": q["difficulty"],
            "question": q["question"],
            "ground_truth": q.get("ground_truth_answer"),
            "gt_sources": q.get("ground_truth_sources", []),
            "answer": a.get("answer"),
            "citations": a.get("citations", []),
            "latency_ms": a.get("latency_ms"), "cost_usd": a.get("cost_usd"),
            "verdict": rel.get("verdict"), "confident": rel.get("confident"),
            "verdict_reason": rel.get("reason"),
            # harness definition: hallucination = confident AND contradicts GT
            "hallucination": rel.get("verdict") == "incorrect"
                             and bool(rel.get("confident")),
            "citation_verdicts": v.get("citations", []),
            "conversational": v.get("conversational"),
        })
    return {"run": name, "items": items}


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
