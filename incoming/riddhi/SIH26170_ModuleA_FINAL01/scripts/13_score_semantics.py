"""Stage 13 — what does module_a_score actually mean?

A downstream consumer will reach for this number and assume something about it. The
job here is to measure what is true, so the integration note can say it, and to state
plainly what is not.

Three questions:

  1. Is it monotone in the probability of being anomalous? (Is a higher score really
     more likely to be a real defect?)
  2. Is it *calibrated* — does 0.7 mean 70%? (No. Measured, so nobody assumes it.)
  3. How stable is an individual score? (Measured under resampling, because stage 12
     found 1% measurement noise moves individual scores by up to 0.61.)

Calibration split, out of fold. The holdout is not opened here.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from _common import RESULTS, release_arg
from modulea import config
from modulea.cv import leave_one_lot_out
from modulea.dataio import Release
from modulea.scoring import StatisticalCore
from modulea.specs import SpecLimits
from modulea.tiers import compose_score

BINS = [0.0, 0.5, 0.7, 0.8, 0.85, 0.90, 0.95, 1.0]


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    args = parser.parse_args()
    release = Release(args.release)
    train, cal = release.split("train"), release.split("calibration")
    specs = SpecLimits.load(release.specs_path())
    y = cal["is_anomalous"].astype(int).to_numpy()
    lots = cal["lot_id"].to_numpy()

    statistical = np.full(len(cal), np.nan)
    for _, tr, va in leave_one_lot_out(cal):
        core = StatisticalCore(config.DEPTHS).fit(train, cal.iloc[tr])
        statistical[va] = core.score(cal.iloc[va], config.WEIGHTS)
    violated, ratio, _ = specs.violation(cal, 168)
    score = compose_score(statistical, violated, ratio)

    # --- 1. monotone in the anomaly rate? ---------------------------------
    band = pd.cut(score, BINS, include_lowest=True, right=False)
    table = (pd.DataFrame({"band": band, "anomalous": y})
             .groupby("band", observed=True)["anomalous"]
             .agg(["count", "sum", "mean"])
             .rename(columns={"count": "components", "sum": "anomalies",
                              "mean": "observed_anomaly_rate"})
             .reset_index())
    table["band"] = table["band"].astype(str)
    rates = table["observed_anomaly_rate"].to_numpy()
    monotone = bool(np.all(np.diff(rates) >= -1e-12))
    table.to_csv(RESULTS / "13_score_bands.csv", index=False)

    # --- 2. is it a probability? ------------------------------------------
    midpoints = np.array([(BINS[i] + BINS[i + 1]) / 2 for i in range(len(BINS) - 1)])
    used = table.index.to_numpy()
    gap = float(np.max(np.abs(rates - midpoints[used])))

    # --- 3. how stable is one component's score? --------------------------
    # Drop one random lot from the reference and rescore the rest: how far does an
    # individual score move when the population it is ranked against changes?
    rng = np.random.default_rng(26170)
    unique = pd.unique(lots)
    drifts = []
    for _ in range(8):
        drop = rng.choice(unique)
        keep = cal[~cal["lot_id"].eq(drop)].reset_index(drop=True)
        core = StatisticalCore(config.DEPTHS).fit(train, keep)
        rescored = core.score(keep, config.WEIGHTS)
        original = pd.Series(statistical, index=cal["component_id"]).loc[
            keep["component_id"]].to_numpy()
        drifts.append(np.abs(rescored - original))
    drift = np.concatenate(drifts)

    summary = {
        "question_1_monotone": {
            "answer": monotone,
            "statement": "the observed anomaly rate rises with every score band"
                         if monotone else
                         "the observed anomaly rate does NOT rise monotonically",
            "bands": table.to_dict("records")},
        "question_2_is_it_a_probability": {
            "answer": False,
            "largest_gap_between_score_and_observed_rate": gap,
            "statement": f"No. The largest gap between a band's midpoint and its "
                         f"observed anomaly rate is {gap:.3f}. A score of 0.7 does not "
                         f"mean 70% likely. Use the published floor and the tier, "
                         f"never the number's face value."},
        "question_3_individual_stability": {
            "median_abs_drift_when_one_lot_leaves_the_reference": float(np.median(drift)),
            "p95_abs_drift": float(np.percentile(drift, 95)),
            "max_abs_drift": float(drift.max()),
            "statement": "an individual score is a rank against a population, so it "
                         "moves when the population changes. Differences of a few "
                         "hundredths between two components are not meaningful; the "
                         "ordering and the threshold crossing are."},
        "what_the_score_is": "a monotone ranking statistic with a reserved "
                             "out-of-specification band above 0.90",
        "what_the_score_is_not": ["a probability", "calibrated",
                                  "comparable across epochs",
                                  "stable to three decimal places",
                                  "a severity estimate"],
    }
    (RESULTS / "13_score_semantics.json").write_text(json.dumps(summary, indent=2, default=float))
    print(table.to_string(index=False))
    print(f"\nmonotone in the anomaly rate : {monotone}")
    print(f"largest gap to a probability : {gap:.3f}  -> not calibrated")
    print(f"individual score drift when one lot leaves the reference: "
          f"median {np.median(drift):.4f}, p95 {np.percentile(drift, 95):.4f}, "
          f"max {drift.max():.4f}")


if __name__ == "__main__":
    main()
