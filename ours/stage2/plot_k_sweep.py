"""Latency/quality trade-off plots for the k sweep. Reads every judged
ours/results/rag_topk<K>_*/metrics.json (plus bare Kimi as context), computes
the composite via stage23/score.py, and writes ours/results/k_sweep.png with
two panels: p50 latency vs composite score, and p50 latency vs correct%.

Rerunnable — new k runs appear automatically once judged:
    .venv/bin/python ours/stage2/plot_k_sweep.py
"""

import importlib.util
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS = REPO_ROOT / "ours" / "results"

_spec = importlib.util.spec_from_file_location(
    "s23score", REPO_ROOT / "ours" / "stage23" / "score.py")
score = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score)

BLUE, GRAY, INK, MUTED = "#2a78d6", "#898781", "#0b0b0b", "#52514e"
GRID, SURFACE = "#e1e0d9", "#fcfcfb"


def load_points():
    pts = []
    for d in sorted(RESULTS.glob("rag_topk*_moonshotai_Kimi-K2.6")):
        mp = d / "metrics.json"
        if not mp.exists():
            continue
        k = int(re.search(r"topk(\d+)", d.name).group(1))
        m = json.loads(mp.read_text())
        s = score.compute(mp)
        pts.append({"label": f"k={k}", "k": k,
                    "lat": m["latency_ms"]["p50"] / 1000,
                    "total": s["total"],
                    "correct": m["relevance"]["correct"] * 100, "rag": True})
    bare = RESULTS / "bare_moonshotai_Kimi-K2.6" / "metrics.json"
    if bare.exists():
        m = json.loads(bare.read_text())
        s = score.compute(bare)
        pts.append({"label": "bare", "k": None,
                    "lat": m["latency_ms"]["p50"] / 1000, "total": s["total"],
                    "correct": m["relevance"]["correct"] * 100, "rag": False})
    return pts


def panel(ax, pts, ykey, ylabel):
    rag = sorted([p for p in pts if p["rag"]], key=lambda p: p["k"])
    ax.plot([p["lat"] for p in rag], [p[ykey] for p in rag],
            color=BLUE, lw=1.6, alpha=.45, zorder=1)
    for p in pts:
        c = BLUE if p["rag"] else GRAY
        ax.scatter(p["lat"], p[ykey], s=90, color=c, zorder=3,
                   edgecolors=SURFACE, linewidths=2)
        ax.annotate(p["label"], (p["lat"], p[ykey]),
                    xytext=(0, 11), textcoords="offset points",
                    ha="center", fontsize=10,
                    color=INK if p["rag"] else MUTED,
                    fontweight="bold" if p["rag"] else "normal")
    # zoom to the data, with headroom for the point labels
    ys = [p[ykey] for p in pts]
    xs = [p["lat"] for p in pts]
    ypad = (max(ys) - min(ys)) * .18 + 1
    xpad = (max(xs) - min(xs)) * .10 + .5
    ax.set_ylim(min(ys) - ypad, max(ys) + ypad * 1.6)
    # reversed x: faster (lower latency) sits on the right → upper-right = better
    ax.set_xlim(max(xs) + xpad, min(xs) - xpad)
    ax.set_xlabel("p50 latency (s) — faster →", color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.grid(color=GRID, lw=.7)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.set_facecolor(SURFACE)


def main():
    pts = load_points()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    panel(a1, pts, "total", "composite score (/100)")
    a1.set_title("Latency vs composite score  (upper-right = better)",
                 fontsize=11, color=INK, loc="left", fontweight="bold")
    panel(a2, pts, "correct", "correct answers (%)")
    a2.set_title("Latency vs correct rate  (upper-right = better)",
                 fontsize=11, color=INK, loc="left", fontweight="bold")
    fig.suptitle("topk-context-stuffing k sweep — Kimi-K2.6, "
                 "docling__bge-m3__para300-1400 (48 dev questions)",
                 fontsize=10, color=MUTED, x=0.01, ha="left", y=0.99)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    out = RESULTS / "k_sweep.png"
    fig.savefig(out, facecolor=SURFACE)
    print(f"wrote {out} with {len(pts)} points: "
          + ", ".join(p['label'] for p in pts))


if __name__ == "__main__":
    main()
