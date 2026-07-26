"""Shared retrieval layer: embed a query and search one of the named DBs under
ours/stage2/dbs/. DB dir names encode their build strategy
(parser__embedder__chunking, e.g. docling__bge-m3__para300-1400), so choosing
a DB in the UI *is* choosing a db strategy.

The embedder and Chroma clients are cached at module level — first question
pays the model load, the rest are fast.
"""

from functools import lru_cache
from pathlib import Path

from .base import Context

REPO_ROOT = Path(__file__).resolve().parents[3]
DBS_DIR = REPO_ROOT / "ours" / "stage2" / "dbs"
EMBED_MODEL = "BAAI/bge-m3"
DEFAULT_DB = "docling__bge-m3__para300-1400"
PARAGRAPHS = "harel_paragraphs"


def list_dbs():
    return sorted(p.name for p in DBS_DIR.iterdir()
                  if (p / "chroma.sqlite3").exists())


@lru_cache(maxsize=1)
def _embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


@lru_cache(maxsize=4)
def _client(db_name):
    import chromadb
    return chromadb.PersistentClient(path=str(DBS_DIR / db_name))


def retrieve(question, db=DEFAULT_DB, k=8, collection=PARAGRAPHS):
    vec = _embedder().encode([question], normalize_embeddings=True)[0]
    coll = _client(db).get_collection(collection)
    r = coll.query(query_embeddings=[vec.tolist()], n_results=int(k),
                   include=["documents", "metadatas", "distances"])
    return [Context(file=m["file"], page=m.get("page"),
                    domain=m.get("domain", ""), text=t, distance=d)
            for t, m, d in zip(r["documents"][0], r["metadatas"][0],
                               r["distances"][0])]
