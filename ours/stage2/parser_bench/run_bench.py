"""Run all candidate parsers over the sample documents.

Usage (from repo root, with the main .venv active or via its python):
    .venv/bin/python ours/stage2/parser_bench/run_bench.py [--with-docling] [--max-pages N]

Writes ours/stage2/parser_bench/out/<parser>/<doc-stem>.json
Then run make_report.py to build the HTML comparison.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parents[2]
CORPUS = REPO_ROOT / "corpus"
OUT = BENCH_DIR / "out"
DOCLING_PY = BENCH_DIR / ".venv-docling" / "bin" / "python"

sys.path.insert(0, str(BENCH_DIR))
from extractors import LIGHT_EXTRACTORS  # noqa: E402

# Hand-picked for coverage: reversal-prone form, dense table, long policy,
# English content, mixed layout, mid-length policy.
SAMPLES = [
    "car/files/הודעה-על-תאונת-רכב.pdf",
    "car/files/טבלת-המועדים-והתקופות-צד-ג-ביטוח-רכב.pdf",
    "business/files/פוליסת-מכלול-לחבר-מושב-מהדורת-ינואר-2023.pdf",
    "apartment/files/פוליסת-אדירה-זהב-מהדורת-נובמבר-2019-באנגלית.pdf",
    "health/files/כתב-שירות-רפואה-אישית-onlineplus.pdf",
    "life/files/תנאי-הכנסה-למשפחה.pdf",
]


def run_docling(pdf: Path, max_pages: int) -> dict:
    if not DOCLING_PY.exists():
        return {"parser": "docling", "file": str(pdf), "n_pages": 0, "seconds": 0,
                "error": f"docling venv not found at {DOCLING_PY}", "pages": []}
    proc = subprocess.run(
        [str(DOCLING_PY), str(BENCH_DIR / "docling_worker.py"), str(pdf), str(max_pages)],
        capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        return {"parser": "docling", "file": str(pdf), "n_pages": 0, "seconds": 0,
                "error": f"worker failed (rc={proc.returncode}):\n{proc.stderr[-2000:]}",
                "pages": []}
    return json.loads(proc.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-docling", action="store_true")
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--only-docling", action="store_true",
                    help="skip light parsers (e.g. rerun after docling install)")
    args = ap.parse_args()

    parsers = {} if args.only_docling else dict(LIGHT_EXTRACTORS)

    for rel in SAMPLES:
        pdf = CORPUS / rel
        stem = pdf.stem
        for name, fn in parsers.items():
            print(f"[{name}] {rel} ...", flush=True)
            res = fn(pdf, max_pages=args.max_pages)
            res["rel_path"] = rel
            dest = OUT / name / f"{stem}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(res, ensure_ascii=False, indent=1))
            status = "ERROR" if res["error"] else f"{res['seconds']}s, {len(res['pages'])} pages"
            print(f"    -> {status}")

        if args.with_docling or args.only_docling:
            print(f"[docling] {rel} ...", flush=True)
            res = run_docling(pdf, args.max_pages)
            res["rel_path"] = rel
            dest = OUT / "docling" / f"{stem}.json"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(json.dumps(res, ensure_ascii=False, indent=1))
            status = "ERROR" if res["error"] else f"{res['seconds']}s, {len(res['pages'])} pages"
            print(f"    -> {status}")

    print(f"\nDone. JSON in {OUT}. Now run make_report.py")


if __name__ == "__main__":
    main()
