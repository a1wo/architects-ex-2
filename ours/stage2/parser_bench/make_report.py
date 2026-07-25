"""Build a self-contained HTML side-by-side comparison from out/<parser>/*.json.

Usage: python ours/stage2/parser_bench/make_report.py
Output: ours/stage2/parser_bench/out/report.html
"""

import html
import json
import re
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
OUT = BENCH_DIR / "out"
PARSER_ORDER = ["pypdf", "pymupdf", "pdfplumber", "pdfplumber-bidi", "docling"]

# Common corpus words; a hit on the reversal is a strong reversed-run signal.
COMMON_WORDS = ["ביטוח", "פוליסה", "הראל", "תביעה", "עמוד", "סעיף", "בריאות", "רכב"]
REVERSED_WORDS = [w[::-1] for w in COMMON_WORDS]
# Common word pairs; the pair appearing in flipped order signals visual-order
# extraction at the WORD level (letters fine, sentence backwards) — docling
# does this inside table cells.
COMMON_PAIRS = [("ימי", "עסקים"), ("תאונת", "רכב"), ("פרטי", "המבוטח"),
                ("מקרה", "הביטוח"), ("דמי", "הביטוח"), ("תקופת", "הביטוח"),
                ("חברת", "הביטוח"), ("מסירת", "הודעה")]
HEB = re.compile(r"[א-ת]")
ALPHA = re.compile(r"[A-Za-zא-ת]")
SPLIT_FINAL = re.compile(r"[א-ת] [םןץףך](?![א-ת])")


def metrics(text):
    alpha = len(ALPHA.findall(text))
    fwd = sum(text.count(w) for w in COMMON_WORDS)
    rev = sum(text.count(w) for w in REVERSED_WORDS)
    pfwd = sum(text.count(f"{a} {b}") for a, b in COMMON_PAIRS)
    prev = sum(text.count(f"{b} {a}") for a, b in COMMON_PAIRS)
    return {
        "chars": len(text),
        "heb_ratio": len(HEB.findall(text)) / alpha if alpha else 0.0,
        "fwd_hits": fwd,
        "rev_hits": rev,
        "rev_score": rev / (fwd + rev) if (fwd + rev) else 0.0,
        "word_rev_score": prev / (pfwd + prev) if (pfwd + prev) else 0.0,
        "split_finals": len(SPLIT_FINAL.findall(text)),
    }


def mark_reversed(escaped_text):
    for w in REVERSED_WORDS:
        escaped_text = escaped_text.replace(w, f"<mark>{w}</mark>")
    return escaped_text


def render_pdf_pages(pdf_path, stem, n_pages):
    """Render pages 1..n_pages to PNGs under out/renders/<stem>/, return rel srcs."""
    import pymupdf
    dest = OUT / "renders" / stem
    dest.mkdir(parents=True, exist_ok=True)
    srcs = {}
    doc = None
    for pno in range(1, n_pages + 1):
        png = dest / f"p{pno}.png"
        if not png.exists():
            if doc is None:
                doc = pymupdf.open(pdf_path)
            if pno > doc.page_count:
                break
            doc[pno - 1].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(png)
        srcs[pno] = f"renders/{stem}/p{pno}.png"
    if doc:
        doc.close()
    return srcs


CSS = """
:root { color-scheme: light dark; }
body { font-family: system-ui, sans-serif; margin: 1.5rem; }
h1 { font-size: 1.4rem; } h2 { font-size: 1.1rem; margin: 0; }
table.summary { border-collapse: collapse; font-size: 0.85rem; margin-bottom: 2rem; }
table.summary th, table.summary td { border: 1px solid #8884; padding: 4px 8px; text-align: center; }
table.summary td.doc { text-align: right; direction: rtl; font-weight: 600; }
td.bad { background: #d33; color: #fff; }
td.warn { background: #e6a23c66; }
td.err { background: #d33; color: #fff; font-size: 0.75rem; max-width: 22rem; }
details.doc { margin-bottom: 1rem; border: 1px solid #8884; border-radius: 8px; padding: 0.5rem 1rem; }
details.doc > summary { cursor: pointer; font-weight: 600; direction: rtl; text-align: right; }
.pagegrid { display: grid; gap: 8px; margin: 0.8rem 0 1.6rem; align-items: start; }
.cell { border: 1px solid #8883; border-radius: 6px; overflow: hidden; }
.cell .hdr { position: sticky; top: 0; background: #4a5568; color: #fff;
             padding: 3px 8px; font-size: 0.75rem; display: flex; justify-content: space-between; }
.cell .txt { direction: rtl; text-align: right; white-space: pre-wrap; padding: 8px;
             font-size: 0.8rem; max-height: 30rem; overflow-y: auto; }
.cell .md { direction: rtl; text-align: right; white-space: pre-wrap; padding: 8px;
            font-size: 0.72rem; max-height: 14rem; overflow-y: auto;
            border-top: 1px dashed #8886; background: #88888811; font-family: ui-monospace, monospace; }
.cell .mdlabel { font-size: 0.65rem; opacity: 0.7; padding: 2px 8px 0; }
.cell img { width: 100%; display: block; }
.cell.orig { max-height: 32rem; overflow-y: auto; }
summary a { font-weight: 400; font-size: 0.8rem; margin-inline-start: 0.8rem; }
mark { background: #ff5252; color: #fff; }
.pagehdr { font-weight: 700; margin-top: 1rem; border-bottom: 2px solid #8886; }
.legend { font-size: 0.8rem; opacity: 0.8; margin-bottom: 1rem; }
"""


def build():
    # docs[stem] -> {parser: result}
    docs = {}
    for pdir in OUT.iterdir():
        if not pdir.is_dir():
            continue
        for j in pdir.glob("*.json"):
            docs.setdefault(j.stem, {})[pdir.name] = json.loads(j.read_text())

    parsers = [p for p in PARSER_ORDER if any(p in v for v in docs.values())]
    parts = ["<meta charset='utf-8'><title>Parser bench — Harel corpus</title>",
             f"<style>{CSS}</style>",
             "<h1>PDF parser comparison — Harel corpus samples</h1>",
             "<p class='legend'>rev = reversed-word score (share of common Hebrew words "
             "appearing letter-reversed; red &gt; 0.05). word-rev = word-ORDER reversal "
             "(common word pairs appearing flipped — letters fine, sentence backwards; "
             "docling does this inside table cells). splits = final-letter split from word "
             "(e.g. 'המבוקשי ם'). Hebrew renders RTL; <mark>marked</mark> = reversed word hit. "
             "Times: docling includes model inference; its first-ever run includes model download.</p>"]

    # ---- summary table ----
    parts.append("<table class='summary'><tr><th>document</th><th>metric</th>"
                 + "".join(f"<th>{p}</th>" for p in parsers) + "</tr>")
    rows = ["time (s)", "pages", "chars", "heb ratio", "rev score", "word-rev", "splits", "error"]
    for stem, results in sorted(docs.items()):
        agg = {}
        for p in parsers:
            r = results.get(p)
            if not r:
                agg[p] = None
                continue
            full = "\n".join(pg["text"] for pg in r["pages"])
            m = metrics(full)
            agg[p] = {"time": r["seconds"], "pages": f"{len(r['pages'])}/{r['n_pages']}",
                      "chars": m["chars"], "heb": f"{m['heb_ratio']:.2f}",
                      "rev": m["rev_score"], "wrev": m["word_rev_score"],
                      "splits": m["split_finals"],
                      "error": (r["error"] or "").strip().splitlines()[-1] if r["error"] else ""}
        for i, row in enumerate(rows):
            cells = []
            for p in parsers:
                a = agg[p]
                if a is None:
                    cells.append("<td>–</td>")
                    continue
                if row == "time (s)":
                    cells.append(f"<td>{a['time']}</td>")
                elif row == "pages":
                    cells.append(f"<td>{a['pages']}</td>")
                elif row == "chars":
                    cells.append(f"<td>{a['chars']:,}</td>")
                elif row == "heb ratio":
                    cells.append(f"<td>{a['heb']}</td>")
                elif row == "rev score":
                    cls = " class='bad'" if a["rev"] > 0.05 else ""
                    cells.append(f"<td{cls}>{a['rev']:.3f}</td>")
                elif row == "word-rev":
                    cls = " class='bad'" if a["wrev"] > 0.3 else (
                        " class='warn'" if a["wrev"] > 0.05 else "")
                    cells.append(f"<td{cls}>{a['wrev']:.2f}</td>")
                elif row == "splits":
                    cls = " class='warn'" if a["splits"] > 5 else ""
                    cells.append(f"<td{cls}>{a['splits']}</td>")
                else:
                    cells.append(f"<td class='err'>{html.escape(a['error'])}</td>"
                                 if a["error"] else "<td></td>")
            doc_cell = (f"<td class='doc' rowspan='{len(rows)}'>{html.escape(stem)}</td>"
                        if i == 0 else "")
            parts.append(f"<tr>{doc_cell}<td>{row}</td>{''.join(cells)}</tr>")
    parts.append("</table>")

    # ---- per-document, per-page side-by-side ----
    for stem, results in sorted(docs.items()):
        n_show = max((len(r["pages"]) for r in results.values()), default=0)
        any_res = next(iter(results.values()))
        pdf_path = Path(any_res["file"])
        rel = any_res.get("rel_path", "")
        try:
            renders = render_pdf_pages(pdf_path, stem, n_show)
        except Exception as e:
            print(f"render failed for {stem}: {e}")
            renders = {}
        pdf_link = (f"<a href='../../../../corpus/{html.escape(rel)}'>פתח PDF מקורי ↗</a>"
                    if rel else "")
        parts.append(f"<details class='doc'><summary>{html.escape(stem)}"
                     f" &nbsp;({n_show} pages shown){pdf_link}</summary>")
        for pno in range(1, n_show + 1):
            parts.append(f"<div class='pagehdr'>page {pno}</div>")
            parts.append(f"<div class='pagegrid' style='grid-template-columns:"
                         f" repeat({len(parsers) + 1}, 1fr);'>")
            src = renders.get(pno)
            img = (f"<a href='{src}' target='_blank'><img src='{src}' "
                   f"alt='page {pno}' loading='lazy'></a>" if src
                   else "<div class='txt' style='opacity:0.4'>(no render)</div>")
            parts.append(f"<div class='cell orig'><div class='hdr'>"
                         f"<span>original (PDF)</span><span>click to zoom</span></div>{img}</div>")
            for p in parsers:
                r = results.get(p)
                pg = next((x for x in r["pages"] if x["page"] == pno), None) if r else None
                if pg is None:
                    body = "<div class='txt' style='opacity:0.4'>(no output)</div>"
                    hdr_right = ""
                else:
                    m = metrics(pg["text"])
                    hdr_right = f"{m['chars']:,} ch"
                    body = f"<div class='txt'>{mark_reversed(html.escape(pg['text']))}</div>"
                    if pg.get("markdown"):
                        body += ("<div class='mdlabel'>markdown (tables):</div>"
                                 f"<div class='md'>{html.escape(pg['markdown'])}</div>")
                parts.append(f"<div class='cell'><div class='hdr'><span>{p}</span>"
                             f"<span>{hdr_right}</span></div>{body}</div>")
            parts.append("</div>")
        parts.append("</details>")

    (OUT / "report.html").write_text("\n".join(parts))
    print(f"Wrote {OUT / 'report.html'}")


if __name__ == "__main__":
    build()
