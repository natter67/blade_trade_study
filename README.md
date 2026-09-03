# Cutterhead Blade Trade Study & Layout Statistics

This repo has two parts, using two different kinds of data:

- `trade_study.py` — a **materials selection** trade study (which alloy?), using single literature property values per candidate.
- `layout_study.py` — a **statistical analysis** of real repeated-trial test data (which layout/blade geometry?), with multiple trials per configuration, standard deviations, and a real significance test.

They answer different questions and shouldn't be merged into one model — see each section below.

---

## Part 1: Materials Trade Study

A small Python tool that formalizes a real materials selection decision as a
weighted multi-criteria decision matrix — the same underlying method behind
professional engineering trade studies (and, at a much more rigorous level,
how design allowables and material qualification decisions get made in
aerospace).

## Background

For Boring Illini's tunnel boring machine, the cutterhead subteam compared
four tool steels (S7, A2, D2, M2) against three alloy steels (4140, 4130,
4340) across hardness, toughness, machinability, and heat-treatment
stability, and selected 4140 for the build. That comparison happened
informally. This project rebuilds it as code: a reusable tool that scores
and ranks candidate materials against weighted criteria, and — the more
useful part — shows how the "right" answer changes depending on what you're
optimizing for.

## Method

1. **Data**: each candidate alloy's properties live in
   `data/steel_candidates.csv` (hardness, toughness, machinability, relative
   cost).
2. **Normalization**: every criterion is min-max scaled to 0–1 so that
   dissimilar units (Rockwell hardness vs. a cost index) can be combined
   fairly. Cost is inverted so "cheaper" always scores higher.
3. **Weighting**: each criterion gets a weight representing how much it
   matters for a given application. `trade_study.py` ships with four
   named scenarios (`balanced`, `toughness_priority`, `cost_priority`,
   `wear_priority`) so you can see how the winner shifts.
4. **Scoring**: `weighted_total = sum(normalized_value * weight)` per
   alloy, ranked highest to lowest.

## Running it

```bash
pip install -r requirements.txt

python trade_study.py                     # runs all four scenarios + a sensitivity summary
python trade_study.py --scenario cost_priority
python trade_study.py --list-scenarios
```

## Data provenance

The values in `data/steel_candidates.csv` are sourced from manufacturer and
technical reference datasheets (Hudson Tool Steel, Speedy Metals,
TheWorldMaterial, ASTM/AZoM, Wikipedia's cited 4340 entry) — every row's
`notes_source` column names the source and states, explicitly, which
individual values were directly published there versus estimated /
converted (e.g. a couple of post-heat-treat hardness figures and
machinability percentages weren't published for every alloy and are
flagged "ESTIMATE, verify" rather than presented as fact). Check that flag
before treating any specific number as a directly-published fact.

## A real finding worth knowing about

Even with sourced data, none of the four scenarios pick 4140 — the alloy
Boring Illini actually selected. That's not a bug to hide; it's the
interesting result, and it held up after replacing placeholder numbers
with real cited ones, which makes it more credible, not less. It means one
of three things: the datasheet values here still don't match the specific
mill certs the team used, the team was weighting a criterion this model
doesn't capture (like a specific post-heat-treatment cutting test), or the
real decision weighted things differently than these four scenarios
assume. Tracking down which one it is — by comparing against the mill
cert or supplier datasheet the team actually used — is the legitimate next
step, not a discrepancy to explain away.

## Next steps / extensions

- Track down the mismatch above — get the actual mill cert or supplier
  datasheet the team used for the 4140 stock and compare it to the
  literature value here.
- Extend `SCENARIOS` in `trade_study.py` with a weighting that matches
  what the team actually prioritized, and see if it reproduces the 4140
  decision.
- Longer-term: implement an A-basis/B-basis statistical allowables
  calculation (per MIL-HDBK-5H Ch. 9) on this kind of data once you have
  repeated test data for a single alloy, not just single point values
  across different alloys — Part 2 below is the first step in that
  direction, on layout data rather than material data.

---

## Part 2: Layout / Blade Geometry Statistics

`layout_study.py` analyzes real repeated-trial data from actual Boring
Illini cutterhead testing (`data/layout_trials.csv`, extracted from
`Cutterhead_Blade_Testing.xlsx`) — how many revolutions it took the
cutterhead to climb through conditioned clay, across different layouts
(`layout_2`, `control_offset`, `no_outside_flange`) and blade designs
(1, 2, 3), with 2-4 repeated trials per configuration.

This is a genuinely different kind of dataset than Part 1's, and it's
treated differently on purpose. The materials CSV has one literature value
per alloy — no repeats, so no way to compute a real standard deviation or
run a significance test. The layout CSV has actual repeated trials, which
means it's possible to ask "is this difference real, or could it be
noise?" instead of just comparing point estimates. That's a meaningfully
more rigorous kind of analysis, and it's the closer analog to how a real
design allowable gets built from a batch of test coupons.

**Run it:**

```bash
python layout_study.py
```

**What it does, and why it's built this way:**

- Reports every configuration's mean, standard deviation, and coefficient
  of variation **both with and without flagged trials included**, rather
  than silently cleaning the data. The team's own notes at collection time
  already flagged a suspected measurement error, an inconsistent baseline
  reading, and two trials that stalled before reaching the target height.
  Hiding those would make the numbers look cleaner than the underlying
  data actually is.
- Changes exactly one variable per comparison, never two at once:
  - **Layout effect** — layout_2 vs. control_offset, blade design held
    constant at 1. Once the flagged trial is excluded, this shows a real,
    statistically significant effect (~53% reduction, p ≈ 0.002 by Welch's
    t-test).
  - **Blade design effect** — blade 1 vs. 2 vs. 3, layout held constant at
    control_offset. A one-way ANOVA across all three groups (p ≈ 0.70,
    followed by pairwise Welch's t-tests) finds no statistically
    significant difference between blade designs at this sample size.
  - layout_2 / blade 1 vs. control_offset / blade 3 changes both layout
    and blade design at once, so it's confounded — any difference in that
    pairing could come from either factor, or their interaction — and
    isn't reported as a single effect anywhere in this analysis.
- Runs each comparison through a Welch's t-test (or, for the three-way
  blade comparison, an ANOVA followed by pairwise t-tests) and prints an
  explicit small-sample caveat (n=3-4 per group) rather than reporting a
  p-value without context. A p-value from three or four trials is a
  directional signal, not proof, and the script says so instead of
  implying more confidence than the data supports.
- Reports the `no_outside_flange` trials separately with a clear note that
  they never reached the same target height as every other configuration,
  so they're excluded from the statistical comparisons rather than being
  averaged in as if they were equivalent.

Together, the two single-variable results say something specific: the
layout change (layout_2 → control_offset) is the effect that's actually
supported by the data at this sample size; the blade design change (1 → 2
→ 3, within control_offset) is not distinguishable from noise here. That's
a more useful and more honest result than a single combined percentage
that can't be attributed to either factor.
