"""
Cutterhead Layout / Blade Geometry Statistical Analysis
---------------------------------------------------------
Real repeated-trial data from Boring Illini cutterhead testing
(data/layout_trials.csv, extracted from Cutterhead_Blade_Testing.xlsx).

Unlike the material trade study (trade_study.py), which uses single
literature values per alloy, this dataset has multiple trials (T1-T4) per
configuration -- meaning we can actually compute a mean, a standard
deviation, and run a real statistical comparison instead of just ranking
point estimates. That's a meaningfully different (and more rigorous) kind
of analysis, and it's the closer analog to what "statistical basis for a
design value" means in practice.

Two things this script does deliberately, on purpose:

1. It reports results BOTH with and without flagged trials included, rather
   than silently cleaning the data. The dataset has real data-quality
   issues the team already noted at collection time (a suspected measurement
   error, an inconsistent baseline reading, two trials that stalled before
   reaching the target height). Hiding those would make the numbers look
   cleaner than the underlying data actually is.

2. Every comparison changes exactly one variable at a time: layout is
   compared with blade design held constant at 1, and blade design is
   compared with layout held constant at control_offset. layout_2 / blade 1
   vs. control_offset / blade 3 changes both variables at once, so it's
   confounded -- any difference could come from either factor, or their
   interaction -- and isn't reported as a single effect anywhere below.
"""

from pathlib import Path

import pandas as pd
from scipy import stats

DATA_PATH = Path(__file__).parent / "data" / "layout_trials.csv"


def load_trials(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["flagged"] = df["flagged"].astype(bool)
    return df


def summarize(df: pd.DataFrame, layout: str, blade_design: int, exclude_flagged: bool):
    subset = df[(df["layout"] == layout) & (df["blade_design"] == blade_design)]
    if exclude_flagged:
        subset = subset[~subset["flagged"]]
    n = len(subset)
    if n == 0:
        return None
    mean = subset["revs"].mean()
    std = subset["revs"].std(ddof=1) if n > 1 else float("nan")
    cv = (std / mean * 100) if n > 1 else float("nan")
    return {
        "layout": layout,
        "blade_design": blade_design,
        "n": n,
        "mean_revs": round(mean, 3),
        "std_revs": round(std, 3) if n > 1 else None,
        "cv_pct": round(cv, 1) if n > 1 else None,
    }


def print_group_summaries(df: pd.DataFrame):
    groups = df[["layout", "blade_design"]].drop_duplicates().values.tolist()
    print("=== Per-configuration summary ===")
    print(f"{'layout':18s} {'blade':6s} {'all trials':40s} {'flagged excluded':40s}")
    for layout, blade in groups:
        all_s = summarize(df, layout, blade, exclude_flagged=False)
        clean_s = summarize(df, layout, blade, exclude_flagged=True)
        all_str = (f"n={all_s['n']} mean={all_s['mean_revs']} "
                   f"std={all_s['std_revs']} cv={all_s['cv_pct']}%")
        clean_str = (f"n={clean_s['n']} mean={clean_s['mean_revs']} "
                     f"std={clean_s['std_revs']} cv={clean_s['cv_pct']}%") if clean_s else "no clean trials"
        print(f"{layout:18s} {blade:<6} {all_str:40s} {clean_str:40s}")


def compare_groups(df: pd.DataFrame, label: str, layout: str, blade_designs, exclude_flagged=True):
    """One-way comparison across >=2 blade designs with layout held constant.
    Reports group stats, a one-way ANOVA across all groups, and pairwise
    Welch's t-tests as a follow-up (no multiple-comparison correction applied
    -- treat pairwise p-values as exploratory, not confirmatory)."""
    groups = {}
    for bd in blade_designs:
        subset = df[(df["layout"] == layout) & (df["blade_design"] == bd)]
        if exclude_flagged:
            subset = subset[~subset["flagged"]]
        groups[bd] = subset["revs"].values

    print(f"\n=== {label} ===")
    for bd, vals in groups.items():
        std = vals.std(ddof=1) if len(vals) > 1 else float("nan")
        print(f"  blade {bd}  (n={len(vals)}, mean={vals.mean():.2f} revs, std={std:.2f})")

    f_stat, p_value = stats.f_oneway(*groups.values())
    print(f"  One-way ANOVA across all groups: F={f_stat:.2f}, p={p_value:.4f}")
    if any(len(vals) < 5 for vals in groups.values()):
        print("  CAVEAT: n < 5 per group -- this is a directional signal from a small "
              "sample, not a statistically robust result.")

    print("  Pairwise Welch's t-tests (exploratory, uncorrected for multiple comparisons):")
    bds = list(groups.keys())
    for i in range(len(bds)):
        for j in range(i + 1, len(bds)):
            a_vals, b_vals = groups[bds[i]], groups[bds[j]]
            t_stat, p = stats.ttest_ind(a_vals, b_vals, equal_var=False)
            print(f"    blade {bds[i]} vs blade {bds[j]}: t={t_stat:.2f}, p={p:.4f}")


def compare(df: pd.DataFrame, label: str, group_a, group_b, exclude_flagged=True):
    """group_a / group_b are (layout, blade_design) tuples."""
    a = df[(df["layout"] == group_a[0]) & (df["blade_design"] == group_a[1])]
    b = df[(df["layout"] == group_b[0]) & (df["blade_design"] == group_b[1])]
    if exclude_flagged:
        a = a[~a["flagged"]]
        b = b[~b["flagged"]]

    a_vals, b_vals = a["revs"].values, b["revs"].values
    t_stat, p_value = stats.ttest_ind(a_vals, b_vals, equal_var=False)  # Welch's t-test
    pct_change = (b_vals.mean() - a_vals.mean()) / a_vals.mean() * 100

    print(f"\n=== {label} ===")
    print(f"  A = {group_a[0]} / blade {group_a[1]}  (n={len(a_vals)}, mean={a_vals.mean():.2f} revs)")
    print(f"  B = {group_b[0]} / blade {group_b[1]}  (n={len(b_vals)}, mean={b_vals.mean():.2f} revs)")
    print(f"  Change A->B: {pct_change:+.1f}%")
    print(f"  Welch's t-test: t={t_stat:.2f}, p={p_value:.4f}")
    if len(a_vals) < 5 or len(b_vals) < 5:
        print("  CAVEAT: n < 5 per group -- this is a directional signal from a small "
              "sample, not a statistically robust result. Treat the p-value as "
              "suggestive, not conclusive, and say so if asked about it.")


def main():
    df = load_trials()
    print_group_summaries(df)

    compare(
        df,
        "Layout effect: layout_2 vs control_offset, blade design held constant at 1",
        group_a=("layout_2", 1),
        group_b=("control_offset", 1),
    )

    compare_groups(
        df,
        "Blade design effect: blade 1 vs 2 vs 3, layout held constant at control_offset",
        layout="control_offset",
        blade_designs=[1, 2, 3],
    )

    print("\n=== Data quality notes (no_outside_flange / Layout 1) ===")
    nf = df[df["layout"] == "no_outside_flange"]
    print(nf[["trial_id", "height_in", "revs", "flag_note"]].to_string(index=False))
    print("Only 2 of an expected 4 trials completed, and neither reached the 1.5in "
          "target height used everywhere else (both stalled around 1.0in). Revs are "
          "reported as-is but are NOT directly comparable to the other configurations "
          "-- excluded from both comparisons above for that reason.")


if __name__ == "__main__":
    main()
