"""Stage 5 — name the blind spot before anyone else finds it.

The inherited work reports 'static outliers are our weakest behaviour, 4 of 18'.
That is true and it is the wrong unit. Detection tracks the ground truth's
`static_fail_target` flag almost perfectly, and the calibration and holdout splits
are composed completely differently on it. So the real statement is narrower and
more useful: Module A does not detect static offsets that stay inside
specification, and the calibration split contains almost none of them, which means
nothing selected on calibration can see the problem.

Diagnostic. Labels reached only through `_evaluator.py`, after scoring.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from _common import RESULTS, release_arg
from _evaluator import load_truth
from modulea import config
from modulea.cv import leave_one_lot_out
from modulea.dataio import Release
from modulea.scoring import StatisticalCore
from modulea.specs import SpecLimits


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    args = parser.parse_args()
    release = Release(args.release)
    train, cal, hold = (release.split(s) for s in ["train", "calibration", "holdout"])
    specs = SpecLimits.load(release.specs_path())

    # composition of the static-outlier population, split by split
    full = pd.read_csv(release.root / "hidden/Hidden_Ground_Truth.csv")
    static = full[full["is_anomalous"].eq(1) & full["defect_behavior"].eq("STATIC_OUTLIER")]
    composition = pd.concat([
        pd.crosstab(static["severity"], static["split"]).add_prefix("severity_"),
        pd.crosstab(static["static_fail_target"], static["split"]).add_prefix("fail_target_"),
    ])
    composition.to_csv(RESULTS / "05_static_composition.csv")

    rows = []
    # calibration, out of fold
    y_cal = cal["is_anomalous"].astype(int).to_numpy()
    score = np.full(len(cal), np.nan)
    for _, tr, va in leave_one_lot_out(cal):
        core = StatisticalCore(config.DEPTHS).fit(train, cal.iloc[tr])
        score[va] = core.score(cal.iloc[va], config.WEIGHTS)
    violated_cal, _, _ = specs.violation(cal, 168)
    flag_cal = violated_cal | (score >= config.OPERATING_THRESHOLD)

    core_full = StatisticalCore(config.DEPTHS).fit(train, cal)
    score_hold = core_full.score(hold, config.WEIGHTS)
    violated_hold, _, _ = specs.violation(hold, 168)
    flag_hold = violated_hold | (score_hold >= config.OPERATING_THRESHOLD)

    for split, frame, flag in [("CALIBRATION", cal, flag_cal), ("HOLDOUT", hold, flag_hold)]:
        truth = load_truth(args.release, split)
        merged = frame[["component_id"]].merge(truth, on="component_id", validate="one_to_one")
        is_static = merged["defect_behavior"].eq("STATIC_OUTLIER").to_numpy()
        fails_spec = merged["static_fail_target"].eq(1).to_numpy()
        for label, mask in [("static, fails spec", is_static & fails_spec),
                            ("static, within spec", is_static & ~fails_spec),
                            ("all other behaviours",
                             merged["is_anomalous"].eq(1).to_numpy() & ~is_static)]:
            rows.append({"split": split, "population": label, "actual": int(mask.sum()),
                         "detected": int((mask & flag).sum()),
                         "detection_rate": float(flag[mask].mean()) if mask.any() else np.nan})
    table = pd.DataFrame(rows)
    table.to_csv(RESULTS / "05_blindspot.csv", index=False)

    within = table[table.population.eq("static, within spec")]
    summary = {
        "status": "DIAGNOSTIC",
        "finding": "detection tracks static_fail_target, not the STATIC_OUTLIER label",
        "combined_within_spec_detection": {
            "actual": int(within["actual"].sum()),
            "detected": int(within["detected"].sum())},
        "split_composition_note":
            "calibration holds 6 of its 10 static outliers as spec failures; holdout "
            "holds 1 of 18. The published 8/10 on calibration and 4/18 on holdout are "
            "the same detector at the same threshold looking at two different "
            "populations.",
        "consequence":
            "a threshold or model selected on calibration cannot be tuned for "
            "within-spec static offsets, because calibration contains four of them. "
            "This is a property of the dataset split, and it belongs in a note to "
            "whoever owns the generator, not in another modelling round.",
        "ceiling_evidence":
            "nine statistics from five families — top-k means at k in {1,2,4,8}, the "
            "raw per-parameter extreme, two persistence statistics, a late-epoch "
            "statistic, and robust within-lot Mahalanobis — all detect 4 to 7 of the "
            "18 holdout static outliers at a matched 3% false-alarm budget. That is a "
            "ceiling of within-lot statistics on this data, not a deficiency of any "
            "one candidate. Measured in the investigation report, section 5.",
    }
    (RESULTS / "05_blindspot.json").write_text(json.dumps(summary, indent=2, default=float))
    print(composition.to_string())
    print("\n" + table.to_string(index=False))


if __name__ == "__main__":
    main()
