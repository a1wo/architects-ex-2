# Parser comparison bench

Compares PDF text extractors on 6 representative corpus documents to pick the
Stage 2 ingestion parser. Candidates: **pypdf**, **pymupdf**, **pdfplumber**,
**docling** (spec-recommended).

## Setup

```bash
# light parsers into the main venv (pypdf already there)
uv pip install --python .venv/bin/python pymupdf pdfplumber

# docling in its own venv (drags in ~2GB torch; kept away from the main venv)
uv venv ours/stage2/parser_bench/.venv-docling --python 3.12
uv pip install --python ours/stage2/parser_bench/.venv-docling/bin/python docling
```

## Run

```bash
.venv/bin/python ours/stage2/parser_bench/run_bench.py --max-pages 20   # light parsers
.venv/bin/python ours/stage2/parser_bench/run_bench.py --only-docling   # docling (slow; first run downloads ~0.5GB models)
.venv/bin/python ours/stage2/parser_bench/make_report.py
open ours/stage2/parser_bench/out/report.html
```

The report has a metrics summary (time, chars, Hebrew ratio, reversed-word
score, split-final-letter count, errors) and per-page side-by-side text for
eyeball comparison. Red `rev score` = the parser emits Hebrew in visual
(letter-reversed) order.

## Findings

| parser | verdict |
|---|---|
| **pymupdf** | Best. Correct logical-order Hebrew (rev ≈ 0), fastest by 5–10×, most complete text (most chars on the table doc). Minor: a few split final letters on long policies. |
| pypdf | Close second on quality, but drops ~35% of the dense table doc's text (614 vs 941 chars) and is slower. |
| pdfplumber | Raw output unusable for Hebrew: extracts in visual order — nearly every Hebrew word comes out letter-reversed (rev 0.89–1.0). Also crashes on one sample (malformed font dict, pdfminer strictness). Fine on the English-only policy. |
| pdfplumber-bidi | pdfplumber + per-line `python-bidi` fixup. Recovers logical order almost perfectly (rev ≈ 0 everywhere; 0.11 on the claim form's decorative runs, same as everyone). Minor artifact: mirrored parentheses. Still inherits the crash and is the slowest light parser. |
| docling | Mixed. Only parser that recovers real **table structure** (markdown tables) and never letter-reverses — but **word order inside table cells comes out reversed** ("דרישה מידע ומסמכים נוספים" → "נוספים ומסמכים מידע דרישה"; word-rev 0.67–1.0 on table/form docs, ~0 on prose). ~0.5–1 s/page (100–200× slower than pymupdf) + one-time ~0.5 GB model download. |

(Also: every parser struggles with the scanned/decorative runs on the car claim
form — pypdf rev 0.057, pymupdf 0.162 there; those are footer/watermark runs,
not body text.)

**Conclusion:** use **pymupdf** for bulk per-page text extraction in the Stage 2
ingestion pipeline — correct logical-order Hebrew, fastest, most robust. No
parser wins on tables: pymupdf keeps word order but interleaves columns; docling
keeps column structure but reverses word order within cells. If table fidelity
proves to matter on the dev set, a docling pass with cell-level word-order
fixup is the candidate upgrade, not a wholesale switch.
