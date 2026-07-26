"""Local Whisper STT via faster-whisper. Nebius has no STT endpoint, so the
mic feature runs entirely on this machine. The model is heavy (~1.6 GB for
the default), so it is only loaded on demand from the UI and can be dropped
again to free RAM.
"""

import gc
import io
import threading
from pathlib import Path

# Restricted list so /api/stt/load can't be pointed at arbitrary HF repos.
# ivrit-ai's turbo is fine-tuned for Hebrew — best fit for the Harel corpus.
# Hebrew-capable only: "tiny" garbles Hebrew outright (even with language="he"
# forced) and "small" holds up only on clean audio, failing on real mic
# recordings — both deliberately not offered.
MODELS = [
    "ivrit-ai/whisper-large-v3-turbo-ct2",
    "large-v3-turbo",
]

# Models are saved next to the UI (gitignored — multi-GB blobs) so a download
# happens once; every later load reads straight from disk in a few seconds.
MODELS_DIR = Path(__file__).resolve().parent / "models"

_lock = threading.Lock()
_model = None
_state = {"status": "unloaded", "model": None, "error": None}


def _model_dir(model_name: str) -> Path:
    from faster_whisper.utils import _MODELS

    repo = _MODELS.get(model_name, model_name)
    return MODELS_DIR / ("models--" + repo.replace("/", "--"))


def _size_mb(model_name: str):
    """On-disk size in MB, or None if not downloaded yet. Symlinks are skipped:
    the HF layout links snapshots/ files to blobs/, which would double-count."""
    d = _model_dir(model_name)
    if not d.exists():
        return None
    return sum(f.stat().st_size for f in d.rglob("*")
               if f.is_file() and not f.is_symlink()) // 2**20 or None


def status():
    with _lock:
        s = dict(_state)
    s["sizes"] = {m: _size_mb(m) for m in MODELS}
    # First load downloads the model (~1.6 GB for the default) — expose how
    # many MB have landed on disk so the UI can show progress, not a freeze.
    if s["status"] == "loading":
        s["downloaded_mb"] = s["sizes"].get(s["model"]) or 0
    return s


def load(model_name: str):
    """Start loading in a background thread (first load downloads the model);
    the UI polls status() until it flips to "loaded"."""
    with _lock:
        if _state["status"] == "loading" or (
            _state["status"] == "loaded" and _state["model"] == model_name
        ):
            return dict(_state)
        _state.update(status="loading", model=model_name, error=None)
    threading.Thread(target=_load, args=(model_name,), daemon=True).start()
    return status()


def _load(model_name: str):
    global _model
    try:
        from faster_whisper import WhisperModel

        m = WhisperModel(model_name, device="auto", compute_type="int8",
                         download_root=str(MODELS_DIR))
        with _lock:
            _model = m
            _state["status"] = "loaded"
    except Exception as e:
        with _lock:
            _model = None
            _state.update(status="unloaded", model=None,
                          error=f"{type(e).__name__}: {e}")


def unload():
    global _model
    with _lock:
        _model = None
        _state.update(status="unloaded", model=None, error=None)
    gc.collect()
    return status()


def transcribe(data: bytes):
    with _lock:
        m = _model
    if m is None:
        raise RuntimeError("whisper is not loaded")
    segments, info = m.transcribe(io.BytesIO(data), vad_filter=True)
    text = "".join(s.text for s in segments).strip()
    return {"text": text, "language": info.language,
            "duration": round(info.duration, 2)}
