"""Common extraction contract + implementations for the lightweight parsers.

Every extractor returns:
    {"parser": str, "file": str, "n_pages": int, "seconds": float,
     "error": str | None,
     "pages": [{"page": int, "text": str, "markdown": str | None}]}

Pages are 1-indexed (citations use 1-indexed pages).
"""

import time
import traceback


def _result(parser, file, pages, seconds, error=None, n_pages=0):
    return {
        "parser": parser,
        "file": str(file),
        "n_pages": n_pages or len(pages),
        "seconds": round(seconds, 3),
        "error": error,
        "pages": pages,
    }


def _run(parser, file, max_pages, fn):
    """Wrap an extraction function with timing and error capture."""
    t0 = time.perf_counter()
    try:
        pages, n_pages = fn(file, max_pages)
        return _result(parser, file, pages, time.perf_counter() - t0, n_pages=n_pages)
    except Exception:
        return _result(parser, file, [], time.perf_counter() - t0,
                       error=traceback.format_exc(limit=3))


def extract_pypdf(file, max_pages=None):
    def fn(file, max_pages):
        from pypdf import PdfReader
        reader = PdfReader(file)
        n = len(reader.pages)
        limit = min(n, max_pages) if max_pages else n
        pages = [{"page": i + 1, "text": reader.pages[i].extract_text() or "",
                  "markdown": None} for i in range(limit)]
        return pages, n
    return _run("pypdf", file, max_pages, fn)


def extract_pymupdf(file, max_pages=None):
    def fn(file, max_pages):
        import pymupdf
        doc = pymupdf.open(file)
        n = doc.page_count
        limit = min(n, max_pages) if max_pages else n
        pages = [{"page": i + 1, "text": doc[i].get_text("text"),
                  "markdown": None} for i in range(limit)]
        doc.close()
        return pages, n
    return _run("pymupdf", file, max_pages, fn)


def extract_pdfplumber(file, max_pages=None):
    def fn(file, max_pages):
        import pdfplumber
        pages = []
        with pdfplumber.open(file) as pdf:
            n = len(pdf.pages)
            limit = min(n, max_pages) if max_pages else n
            for i in range(limit):
                p = pdf.pages[i]
                pages.append({"page": i + 1, "text": p.extract_text() or "",
                              "markdown": None})
                p.flush_cache()
        return pages, n
    return _run("pdfplumber", file, max_pages, fn)


def extract_pdfplumber_bidi(file, max_pages=None):
    """pdfplumber emits Hebrew in visual (letter-reversed) order; run the bidi
    algorithm per line to recover logical order."""
    res = extract_pdfplumber(file, max_pages)
    if res["error"]:
        res["parser"] = "pdfplumber-bidi"
        return res
    from bidi.algorithm import get_display
    for pg in res["pages"]:
        pg["text"] = "\n".join(get_display(line, base_dir="R")
                               for line in pg["text"].splitlines())
    res["parser"] = "pdfplumber-bidi"
    return res


LIGHT_EXTRACTORS = {
    "pypdf": extract_pypdf,
    "pymupdf": extract_pymupdf,
    "pdfplumber": extract_pdfplumber,
    "pdfplumber-bidi": extract_pdfplumber_bidi,
}
