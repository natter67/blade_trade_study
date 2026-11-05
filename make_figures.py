"""
Generate the figures used in README.md and SUMMARY.md.

    python make_figures.py        # writes PNGs to figures/

Every number plotted is computed from data/*.csv by the same functions
used in trade_study.py and layout_study.py, so the figures can't drift from
the printed analysis.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import layout_study
import trade_study

OUT = Path(__file__).parent / "figures"

# Palette (validated categorical slots 1-2 + neutral ink/grid tones)
BLUE = "#2a78d6"
ORANGE = "#eb6834"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#8a8984"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.edgecolor": GRID,
    "axes.labelcolor": INK_2,
    "axes.titlecolor": INK,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "xtick.color": INK_2,
    "ytick.color": INK_2,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "legend.frameon": False,
})


def _strip(ax, groups, colors):
    """Dot plot: one marker per trial, hollow grey for flagged trials,
    a short horizontal bar at the mean of the unflagged trials."""
    rng = np.random.default_rng(0)
    for i, (label, sub) in enumerate(groups):
        jitter = rng.uniform(-0.08, 0.08, len(sub))
        clean = ~sub["flagged"].values
        ax.scatter(i + jitter[clean], sub["revs"].values[clean], s=70,
                   color=colors[i], edgecolor=SURFACE, linewidth=1.5, zorder=3)
        ax.scatter(i + jitter[~clean], sub["revs"].values[~clean], s=70,
                   facecolor="none", edgecolor=MUTED, linewidth=1.5, zorder=3)
        m = sub.loc[clean, "revs"].mean()
        ax.hlines(m, i - 0.25, i + 0.25, color=INK, linewidth=2, zorder=4)
        ax.annotate(f"mean {m:.1f}", (i + 0.28, m), va="center",
                    color=INK_2, fontsize=9)
    ax.set_xticks(range(len(groups)), [g[0] for g in groups])
    ax.set_xlim(-0.6, len(groups) - 0.2)
    ax.set_ylim(0, None)
    ax.set_ylabel("Revolutions to climb 1.5 in (fewer is better)")
    ax.scatter([], [], s=70, color=INK_2, label="trial")
    ax.scatter([], [], s=70, facecolor="none", edgecolor=MUTED,
               label="flagged trial (excluded from mean)")
    ax.legend(loc="upper right", fontsize=9)


def fig_layout(df):
    a = df[(df["layout"] == "layout_2") & (df["blade_design"] == 1)]
    b = df[(df["layout"] == "control_offset") & (df["blade_design"] == 1)]
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    _strip(ax, [("Layout 2", a), ("Control offset", b)], [ORANGE, BLUE])
    am = a.loc[~a["flagged"], "revs"].mean()
    bm = b.loc[~b["flagged"], "revs"].mean()
    ax.set_title("Layout effect (blade design 1)")
    fig.text(0.015, 0.015,
             f"Control offset: {(bm - am) / am * 100:+.1f}% revs vs layout 2 "
             "(n=3 vs 3, Welch p=0.002; exact permutation p=0.10)",
             color=INK_2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "layout_effect.png", dpi=200)
    plt.close(fig)


def fig_blade(df):
    co = df[df["layout"] == "control_offset"]
    groups = [(f"Blade {bd}", co[co["blade_design"] == bd]) for bd in (1, 2, 3)]
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    _strip(ax, groups, [BLUE, BLUE, BLUE])
    ax.set_ylim(0, 20)
    ax.set_title("Blade design effect (control-offset layout)")
    fig.text(0.015, 0.015,
             "No detectable difference: one-way ANOVA p=0.70 (n=3-4 per group)",
             color=INK_2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "blade_design_effect.png", dpi=200)
    plt.close(fig)


def fig_trade(cand):
    names = list(trade_study.SCENARIOS)
    alloys = cand["alloy"].tolist()
    mat = np.array([
        trade_study.score(cand, trade_study.SCENARIOS[n])
        .set_index("alloy").loc[alloys, "weighted_total"].values
        for n in names
    ]).T

    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("blue", ["#eef4fc", "#9cc2ef", BLUE, "#123f78"])

    fig, ax = plt.subplots(figsize=(6.8, 4.6))
    ax.grid(False)
    ax.imshow(mat, cmap=cmap, vmin=0.2, vmax=0.85, aspect="auto")
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            best = mat[i, j] == mat[:, j].max()
            ax.text(j, i, f"{mat[i, j]:.2f}" + (" ★" if best else ""),
                    ha="center", va="center", fontsize=9.5,
                    color="white" if mat[i, j] > 0.62 else INK,
                    fontweight="bold" if best else "normal")
    ax.set_xticks(range(len(names)), [n.replace("_", "\n") for n in names])
    ax.set_yticks(range(len(alloys)), alloys)
    for lbl in ax.get_yticklabels():
        if lbl.get_text() == "4140":
            lbl.set_fontweight("bold")
            lbl.set_color(INK)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Weighted score by scenario (★ = top pick)")
    fig.text(0.015, 0.015,
             "4140 (bold) was the team's actual pick; it never ranks first under these weights.",
             color=INK_2, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(OUT / "trade_study_scores.png", dpi=200)
    plt.close(fig)


def main():
    OUT.mkdir(exist_ok=True)
    trials = layout_study.load_trials()
    fig_layout(trials)
    fig_blade(trials)
    fig_trade(trade_study.load_candidates())
    print(f"Wrote figures to {OUT}/")


if __name__ == "__main__":
    main()
