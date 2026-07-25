"""Run docling over the whole corpus (corpus/*/files/*.pdf).

Run with the parser_bench docling venv:
    ours/stage2/parser_bench/.venv-docling/bin/python ours/stage2/ingest/docling_corpus.py --shard 0 --num-shards 3

Writes ours/stage2/parsed/docling/<domain>/<stem>.json with per-page text +
markdown (same schema as parser_bench). Skips files whose output already
exists, so it's resumable — delete a JSON to redo it.
"""

import argparse
import json
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CORPUS = REPO_ROOT / "corpus"
OUT = REPO_ROOT / "ours" / "stage2" / "parsed" / "docling"


def convert_one(converter, pdf: Path) -> dict:
    t0 = time.perf_counter()
    try:
        doc = converter.convert(str(pdf)).document
        pages = [{"page": pno,
                  "text": doc.export_to_text(page_no=pno),
                  "markdown": doc.export_to_markdown(page_no=pno)}
                 for pno in range(1, len(doc.pages) + 1)]
        return {"parser": "docling", "file": str(pdf), "n_pages": len(doc.pages),
                "seconds": round(time.perf_counter() - t0, 3), "error": None,
                "pages": pages}
    except Exception:
        return {"parser": "docling", "file": str(pdf), "n_pages": 0,
                "seconds": round(time.perf_counter() - t0, 3),
                "error": traceback.format_exc(limit=5), "pages": []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--num-shards", type=int, default=1)
    args = ap.parse_args()

    # Sort by size descending, round-robin across shards → balanced load.
    pdfs = sorted(CORPUS.glob("*/files/*.pdf"),
                  key=lambda p: p.stat().st_size, reverse=True)
    mine = [p for i, p in enumerate(pdfs) if i % args.num_shards == args.shard]

    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions()
    opts.do_ocr = False
    opts.do_table_structure = True
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})

    done = skipped = failed = 0
    for pdf in mine:
        domain = pdf.parts[len(CORPUS.parts)]
        dest = OUT / domain / f"{pdf.stem}.json"
        if dest.exists():
            skipped += 1
            continue
        res = convert_one(converter, pdf)
        res["rel_path"] = str(pdf.relative_to(CORPUS))
        res["domain"] = domain
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(res, ensure_ascii=False))
        done += 1
        if res["error"]:
            failed += 1
            print(f"[shard {args.shard}] FAIL {res['rel_path']}", flush=True)
        else:
            chars = sum(len(p["text"]) for p in res["pages"])
            print(f"[shard {args.shard}] {done}/{len(mine)} {res['rel_path']} "
                  f"({res['n_pages']}pp, {res['seconds']}s, {chars}ch)", flush=True)

    print(f"[shard {args.shard}] DONE: {done} converted, {skipped} skipped, "
          f"{failed} failed", flush=True)


if __name__ == "__main__":
    main()
