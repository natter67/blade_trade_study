"""
Cutterhead Blade Material Trade Study
--------------------------------------
Formalizes a weighted multi-criteria decision matrix (the same method behind
real engineering trade studies) to rank candidate tool steels and alloy steels
for a cutterhead blade application, based on hardness, toughness,
machinability, and relative cost.

Data source: data/steel_candidates.csv
    Values are sourced from manufacturer/technical reference datasheets, cited
    per-row in notes_source. Some individual values weren't published directly
    and were estimated or unit-converted -- those are flagged "ESTIMATE" in
    notes_source. Check that flag before treating any single number as a
    directly-published fact.

Usage:
    python trade_study.py                  # run with the default weighting
    python trade_study.py --scenario cost  # run a named weighting scenario
    python trade_study.py --list-scenarios # show all available scenarios
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).parent / "data" / "steel_candidates.csv"

# Criteria where a HIGHER raw value is better for the application.
BENEFIT_CRITERIA = ["hardness_hrc", "toughness_1_10", "machinability_1_10"]
# Criteria where a LOWER raw value is better (cost).
COST_CRITERIA = ["cost_index"]

# Named weighting scenarios. Weights must sum to 1.0 across the four criteria:
# hardness, toughness, machinability, cost.
# Swapping these is the point: a trade study's "right answer" depends on what
# you're optimizing for, not just the raw numbers.
SCENARIOS = {
    "balanced": {
        "hardness_hrc": 0.25,
        "toughness_1_10": 0.25,
        "machinability_1_10": 0.25,
        "cost_index": 0.25,
    },
    "toughness_priority": {  # e.g. fracture-critical / shock-loaded application
        "hardness_hrc": 0.20,
        "toughness_1_10": 0.45,
        "machinability_1_10": 0.15,
        "cost_index": 0.20,
    },
    "cost_priority": {  # e.g. budget-constrained student team, like Boring Illini
        "hardness_hrc": 0.20,
        "toughness_1_10": 0.20,
        "machinability_1_10": 0.20,
        "cost_index": 0.40,
    },
    "wear_priority": {  # e.g. high-abrasion soil / long service life
        "hardness_hrc": 0.45,
        "toughness_1_10": 0.15,
        "machinability_1_10": 0.15,
        "cost_index": 0.25,
    },
}


def load_candidates(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"alloy", "category", *BENEFIT_CRITERIA, *COST_CRITERIA}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Data file is missing required columns: {missing}")
    return df


def normalize(df: pd.DataFrame) -> pd.DataFrame:
    """Min-max normalize every criterion to a 0-1 scale where 1 is always
    'best for the application' — benefit criteria go up, cost is inverted."""
    norm = df.copy()
    for col in BENEFIT_CRITERIA:
        lo, hi = df[col].min(), df[col].max()
        norm[col] = (df[col] - lo) / (hi - lo) if hi > lo else 1.0
    for col in COST_CRITERIA:
        lo, hi = df[col].min(), df[col].max()
        # invert: lowest cost -> 1.0 (best), highest cost -> 0.0
        norm[col] = (hi - df[col]) / (hi - lo) if hi > lo else 1.0
    return norm


def score(df: pd.DataFrame, weights: dict) -> pd.DataFrame:
    total_weight = sum(weights.values())
    if abs(total_weight - 1.0) > 1e-6:
        raise ValueError(f"Scenario weights must sum to 1.0 (got {total_weight})")

    norm = normalize(df)
    result = df[["alloy", "category"]].copy()
    for col, w in weights.items():
        result[f"{col}_score"] = (norm[col] * w).round(3)
    result["weighted_total"] = sum(
        norm[col] * w for col, w in weights.items()
    ).round(3)
    return result.sort_values("weighted_total", ascending=False).reset_index(drop=True)


def print_ranking(scenario_name: str, weights: dict, ranking: pd.DataFrame) -> None:
    print(f"\n=== Scenario: {scenario_name} ===")
    print("Weights:", {k: v for k, v in weights.items()})
    print(ranking.to_string(index=False))
    winner = ranking.iloc[0]
    print(f"\n-> Top pick under this scenario: {winner['alloy']} "
          f"(score {winner['weighted_total']:.3f})")


def main():
    parser = argparse.ArgumentParser(description="Cutterhead blade material trade study")
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()) + ["all"],
        default="all",
        help="Which weighting scenario to run (default: all, to show sensitivity)",
    )
    parser.add_argument(
        "--list-scenarios", action="store_true", help="List available scenarios and exit"
    )
    args = parser.parse_args()

    if args.list_scenarios:
        for name, weights in SCENARIOS.items():
            print(f"{name}: {weights}")
        sys.exit(0)

    df = load_candidates()

    scenarios_to_run = SCENARIOS.keys() if args.scenario == "all" else [args.scenario]
    winners = {}
    for name in scenarios_to_run:
        weights = SCENARIOS[name]
        ranking = score(df, weights)
        print_ranking(name, weights, ranking)
        winners[name] = ranking.iloc[0]["alloy"]

    if args.scenario == "all":
        print("\n=== Sensitivity summary: does the winner change with priorities? ===")
        for name, winner in winners.items():
            print(f"  {name:20s} -> {winner}")


if __name__ == "__main__":
    main()
