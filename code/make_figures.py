"""
Paper figures from results/analysis/*.csv  ->  paper/figures/*.pdf (+ .png previews)

fig_accuracy:  accuracy per model and question form (dot plot)
fig_gaps:      paired gaps with 95% CIs: script, natural typing, net (forest plot, 3 panels)
fig_locality:  English - natural Hinglish and English - Devanagari, India-specific vs global questions

Colours: reference categorical slots 1-3 (validated all-pairs, light), English as neutral grey;
every form also has its own marker shape, so colour is never the only cue (print / colour-blind safe).
"""

import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
A = ROOT / "results" / "analysis"
OUT = ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df"
FORMS = [  # key, label, colour, marker, filled
    ("en", "English", "#8a8984", "o", False),
    ("hi_rom_natural", "Natural Hinglish", "#1baf7a", "D", True),
    ("hi_dev", "Devanagari", "#2a78d6", "s", True),
    ("hi_rom_std", "Rule-based Roman", "#eb6834", "^", True),
]
MAIN = ["Aya-Expanse-8B", "Gemma-2-9B (4-bit)", "Llama-3.1-8B", "Qwen2.5-7B", "Nemotron-Hindi-4B",
        "Gajendra-7B", "Airavata-7B"]

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.labelsize": 8, "xtick.labelsize": 7.5,
    "ytick.labelsize": 8, "legend.fontsize": 7.5, "axes.edgecolor": INK2, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK, "axes.linewidth": 0.6, "xtick.major.width": 0.6,
    "ytick.major.size": 0, "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.dpi": 300,
})


def read(name):
    return list(csv.DictReader(open(A / name, encoding="utf-8")))


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{name}.png", bbox_inches="tight", dpi=200)
    plt.close(fig)


def fig_accuracy():
    acc = {(r["model"], r["form"]): float(r["accuracy"]) * 100 for r in read("accuracy.csv")}
    models = sorted(MAIN, key=lambda m: acc[(m, "en")])  # bottom -> top, best English on top
    fig, ax = plt.subplots(figsize=(3.35, 2.75))
    for y, m in enumerate(models):
        xs = [acc[(m, f[0])] for f in FORMS]
        ax.plot([min(xs), max(xs)], [y, y], color=GRID, linewidth=2.2, solid_capstyle="round", zorder=1)
        off = {f[0]: 0.0 for f in FORMS}
        keys = [f[0] for f in FORMS]
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                if abs(acc[(m, a)] - acc[(m, b)]) < 2.5 and off[a] == off[b] == 0:
                    off[a], off[b] = 0.17, -0.17
        for key, _, col, mk, filled in FORMS:
            ax.scatter(acc[(m, key)], y + off[key], s=30 if mk != "D" else 24, marker=mk, zorder=3,
                       facecolor=col if filled else "white", edgecolor=col if filled else INK2,
                       linewidth=1.0 if not filled else 0.9)
    ax.set_yticks(range(len(models)), models)
    ax.set_xlim(0, 85)
    ax.set_ylim(-0.6, len(models) - 0.4)
    ax.set_xlabel("Accuracy (%)")
    style(ax)
    handles = [Line2D([], [], linestyle="", marker=mk, markersize=5.5 if mk != "D" else 4.8,
                      markerfacecolor=col if filled else "white", markeredgecolor=col if filled else INK2,
                      markeredgewidth=1.0, label=lab) for _, lab, col, mk, filled in FORMS]
    ax.legend(handles=handles, ncol=2, frameon=False, loc="lower center", bbox_to_anchor=(0.38, 1.0),
              handletextpad=0.3, columnspacing=1.0)
    save(fig, "fig_accuracy")


def fig_gaps():
    rows = read("gaps.csv")
    g = {(r["model"], r["gap"]): r for r in rows}
    panels = [("script gap (Devanagari - rule-based Roman)", "(a) Script\nDevanagari − rule-based Roman"),
              ("code-mixing gain (natural Hinglish - rule-based Roman)", "(b) Natural typing\nHinglish − rule-based Roman"),
              ("natural Hinglish - Devanagari", "(c) Net\nHinglish − Devanagari")]
    acc = {(r["model"], r["form"]): float(r["accuracy"]) for r in read("accuracy.csv")}
    models = sorted(MAIN, key=lambda m: acc[(m, "en")])
    fig, axes = plt.subplots(1, 3, figsize=(6.9, 2.4), sharey=True)
    for ax, (gap, title) in zip(axes, panels):
        for y, m in enumerate(models):
            r = g[(m, gap)]
            d, lo, hi = (100 * float(r[k]) for k in ("diff", "ci_low", "ci_high"))
            sig = float(r["p_holm"]) < 0.05
            ax.plot([lo, hi], [y, y], color=INK2, linewidth=1.0, solid_capstyle="round", zorder=2)
            ax.scatter(d, y, s=26, marker="o", zorder=3, facecolor=INK if sig else "white", edgecolor=INK, linewidth=1.0)
            ax.annotate(f"{d:+.0f}", (hi, y), xytext=(4, 0), textcoords="offset points", va="center",
                        fontsize=6.8, color=INK2)
        ax.axvline(0, color=INK2, linewidth=0.8, zorder=1)
        ax.set_title(title, fontsize=7.4, color=INK, loc="left")
        ax.set_xlim(-10, 66)
        ax.set_xlabel("Percentage points")
        style(ax)
    axes[0].set_yticks(range(len(models)), models)
    axes[0].set_ylim(-0.6, len(models) - 0.4)
    handles = [Line2D([], [], linestyle="", marker="o", markersize=5, markerfacecolor=INK, markeredgecolor=INK,
                      label="Holm-adjusted p < 0.05"),
               Line2D([], [], linestyle="", marker="o", markersize=5, markerfacecolor="white", markeredgecolor=INK,
                      label="not significant")]
    fig.legend(handles=handles, ncol=2, frameon=False, loc="lower right", bbox_to_anchor=(0.99, -0.07))
    fig.tight_layout(w_pad=1.2)
    save(fig, "fig_gaps")


def fig_locality():
    rows = [r for r in read("locality.csv") if r["model"] in MAIN]
    acc = {(r["model"], r["form"]): float(r["accuracy"]) for r in read("accuracy.csv")}
    models = sorted(MAIN, key=lambda m: acc[(m, "en")])
    loc = {(r["model"], r["locality"]): r for r in rows}
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 2.3), sharey=True)
    specs = [("en_minus_dev", "English − Devanagari"), ("en_minus_natural", "English − natural Hinglish")]
    COL = {"global": ("#2a78d6", "o", "Global questions"), "india": ("#eb6834", "s", "India-specific questions")}
    for ax, (k, title) in zip(axes, specs):
        for y, m in enumerate(models):
            v = {l: 100 * float(loc[(m, l)][k]) for l in ("global", "india")}
            ax.plot([v["global"], v["india"]], [y, y], color=GRID, linewidth=2.2, solid_capstyle="round", zorder=1)
            for l, (col, mk, _) in COL.items():
                ax.scatter(v[l], y, s=28, marker=mk, facecolor=col, edgecolor=col, zorder=3)
        ax.axvline(0, color=INK2, linewidth=0.8, zorder=1)
        ax.set_title(title, fontsize=7.8, color=INK, loc="left")
        ax.set_xlabel("Percentage points (positive = English better)")
        ax.set_xlim(-25, 60)
        style(ax)
    axes[0].set_yticks(range(len(models)), models)
    axes[0].set_ylim(-0.6, len(models) - 0.4)
    handles = [Line2D([], [], linestyle="", marker=mk, markersize=5, markerfacecolor=col, markeredgecolor=col, label=lab)
               for col, mk, lab in COL.values()]
    fig.legend(handles=handles, ncol=2, frameon=False, loc="lower right", bbox_to_anchor=(0.99, -0.08))
    fig.tight_layout(w_pad=1.2)
    save(fig, "fig_locality")


if __name__ == "__main__":
    fig_accuracy()
    fig_gaps()
    fig_locality()
    print("wrote", sorted(p.name for p in OUT.glob("*.pdf")))
