"""Embed the parsed corpus into a local Chroma DB at three granularities.

Collections (all BAAI/bge-m3 dense vectors, dim 1024, cosine):
    harel_documents  - one vector per document (routing/coarse retrieval)
    harel_pages      - one vector per PDF page / web page
    harel_paragraphs - paragraph chunks (primary retrieval unit)

Storage: embedded Chroma (no server) persisted at ours/stage2/chroma/

Sources:
    ours/stage2/parsed/docling/<domain>/<stem>.json  (PDFs, per-page text+md)
    corpus/<domain>/pages/*.txt                      (web pages, single page)

Run with the docling venv (has torch + sentence-transformers):
    ours/stage2/parser_bench/.venv-docling/bin/python ours/stage2/ingest/embed_index.py [--limit N] [--granularity all|document|page|paragraph]

Recreates the target collections on each run (deterministic, idempotent).
"""

import argparse
import json
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPO_ROOT / "corpus"
PARSED = REPO_ROOT / "ours" / "stage2" / "parsed" / "docling"
DBS_DIR = REPO_ROOT / "ours" / "stage2" / "dbs"
DEFAULT_DB = "docling__bge-m3__para300-1400"  # parse__embedder__chunking

MODEL = "BAAI/bge-m3"
DOC_CHAR_CAP = 24000      # ~8k tokens; bge-m3 truncates there anyway
PARA_MIN, PARA_MAX = 300, 1400

COLLECTIONS = {"document": "harel_documents", "page": "harel_pages",
               "paragraph": "harel_paragraphs"}


def pid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "|".join(str(p) for p in parts)))


def split_paragraphs(text):
    """Blank-line split, then greedily merge small pieces up to PARA_MAX."""
    raw = [p.strip() for p in text.split("\n\n") if p.strip()]
    out, buf = [], ""
    for p in raw:
        buf = f"{buf}\n\n{p}".strip() if buf else p
        if len(buf) >= PARA_MIN:
            while len(buf) > PARA_MAX:
                out.append(buf[:PARA_MAX])
                buf = buf[PARA_MAX:]
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


def load_docs(limit=None):
    """Yield {rel_path, domain, source, pages: [{page, text}]} for PDFs + web pages."""
    docs = []
    for j in sorted(PARSED.glob("*/*.json")):
        r = json.loads(j.read_text())
        if r.get("error") or not r["pages"]:
            continue
        docs.append({"rel_path": r["rel_path"], "domain": r["domain"], "source": "pdf",
                     "pages": [{"page": p["page"], "text": p["text"]} for p in r["pages"]]})
    for t in sorted(CORPUS.glob("*/pages/*.txt")):
        text = t.read_text(errors="replace").strip()
        if not text:
            continue
        docs.append({"rel_path": str(t.relative_to(CORPUS)),
                     "domain": t.parts[len(CORPUS.parts)], "source": "web",
                     "pages": [{"page": 1, "text": text}]})
    return docs[:limit] if limit else docs


def build_points(docs, granularity):
    """Yield (id, text_to_embed, metadata) per point. Text is stored as the
    Chroma document; metadata holds the citation fields."""
    for d in docs:
        base = {"file": d["rel_path"], "domain": d["domain"], "source": d["source"]}
        if granularity == "document":
            full = "\n".join(p["text"] for p in d["pages"])
            yield (pid("doc", d["rel_path"]), full[:DOC_CHAR_CAP],
                   {**base, "n_pages": len(d["pages"])})
        elif granularity == "page":
            for p in d["pages"]:
                if not p["text"].strip():
                    continue
                yield (pid("page", d["rel_path"], p["page"]), p["text"],
                       {**base, "page": p["page"]})
        elif granularity == "paragraph":
            for p in d["pages"]:
                for i, para in enumerate(split_paragraphs(p["text"])):
                    yield (pid("para", d["rel_path"], p["page"], i), para,
                           {**base, "page": p["page"], "para_idx": i})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="only first N docs (smoke test)")
    ap.add_argument("--granularity", default="all",
                    choices=["all", "document", "page", "paragraph"])
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--db-name", default=DEFAULT_DB,
                    help="strategy-descriptive dir name under ours/stage2/dbs/")
    args = ap.parse_args()

    import chromadb
    from sentence_transformers import SentenceTransformer

    db_path = DBS_DIR / args.db_name
    client = chromadb.PersistentClient(path=str(db_path))
    model = SentenceTransformer(MODEL)
    print(f"model on {model.device}, chroma at {db_path}", flush=True)

    grans = list(COLLECTIONS) if args.granularity == "all" else [args.granularity]
    docs = load_docs(args.limit)
    print(f"{len(docs)} documents loaded "
          f"({sum(d['source'] == 'pdf' for d in docs)} pdf, "
          f"{sum(d['source'] == 'web' for d in docs)} web)", flush=True)

    for gran in grans:
        name = COLLECTIONS[gran]
        # Document-level inputs are up to 8k tokens; a batch of 32 of those
        # blows past MPS memory and thrashes. Keep doc batches tiny.
        batch = 2 if gran == "document" else args.batch
        try:
            client.delete_collection(name)
        except Exception:
            pass
        coll = client.create_collection(name, metadata={"hnsw:space": "cosine"})
        points = list(build_points(docs, gran))
        t0 = time.perf_counter()
        for i in range(0, len(points), batch * 8):
            chunk = points[i:i + batch * 8]
            vecs = model.encode([t for _, t, _ in chunk], batch_size=batch,
                                normalize_embeddings=True, show_progress_bar=False)
            coll.add(ids=[c[0] for c in chunk],
                     embeddings=[v.tolist() for v in vecs],
                     documents=[c[1] for c in chunk],
                     metadatas=[c[2] for c in chunk])
            done = min(i + len(chunk), len(points))
            rate = done / (time.perf_counter() - t0)
            print(f"[{name}] {done}/{len(points)} ({rate:.1f}/s)", flush=True)
        print(f"[{name}] DONE {len(points)} points in "
              f"{time.perf_counter() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
