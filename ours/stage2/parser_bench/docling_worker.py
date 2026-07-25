"""Docling extraction worker — run with the .venv-docling python, one PDF per call.

Usage: .venv-docling/bin/python docling_worker.py <pdf> [max_pages]
Prints the common bench JSON to stdout (everything else goes to stderr).

Emits per-page plain text AND per-page markdown (tables serialized), so the
report can judge table-structure fidelity.
"""

import json
import sys
import time
import traceback


def main():
    file = sys.argv[1]
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 else 0

    t0 = time.perf_counter()
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        opts = PdfPipelineOptions()
        opts.do_ocr = False  # digital PDFs; OCR would be slow and unneeded
        opts.do_table_structure = True
        converter = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
        )
        kwargs = {}
        if max_pages:
            kwargs["page_range"] = (1, max_pages)
        doc = converter.convert(file, **kwargs).document

        n_pages = len(doc.pages)
        limit = min(n_pages, max_pages) if max_pages else n_pages
        pages = []
        for pno in range(1, limit + 1):
            text = doc.export_to_text(page_no=pno)
            md = doc.export_to_markdown(page_no=pno)
            pages.append({"page": pno, "text": text, "markdown": md})

        out = {"parser": "docling", "file": file, "n_pages": n_pages,
               "seconds": round(time.perf_counter() - t0, 3),
               "error": None, "pages": pages}
    except Exception:
        out = {"parser": "docling", "file": file, "n_pages": 0,
               "seconds": round(time.perf_counter() - t0, 3),
               "error": traceback.format_exc(limit=5), "pages": []}

    json.dump(out, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    main()
