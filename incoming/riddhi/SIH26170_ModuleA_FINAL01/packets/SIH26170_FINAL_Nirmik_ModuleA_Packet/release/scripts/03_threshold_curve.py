"""Stage 3 — the recall/workload curve, and the thresholds the release freezes.

Calibration only. The holdout is not opened here.

Leave-one-lot-out, rank reference refitted per held-out lot, uncertainty from a
bootstrap over whole lots. No threshold is *chosen* by this script beyond the one
the declared budget implies; the point is to put the whole curve in front of the
team, because there is no agreed cost ratio between a missed defect and a review
flag and the 3% figure was a development budget, not a requirement.

Also fits the early-epoch thresholds, on calibration NORMALS only. No early
classifier is trained against a final label — at 0 h a defect that has not begun
is not detectable, and a model taught otherwise has learned the lot, not the part.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from _common import RESULTS, release_arg
from modulea import config, evidence
from modulea.cv import leave_one_lot_out
from modulea.dataio import Release
from modulea.evidence import observed_evidence_score
from modulea.metrics import confusion, lot_bootstrap
from modulea.scoring import StatisticalCore
from modulea.specs import SpecLimits

BUDGETS = [0.005, 0.01, 0.02, 0.03, 0.05, 0.10]


def loosest_threshold(y, score, cap) -> float:
    normals = np.sort(np.asarray(score)[np.asarray(y) == 0])
    allowed = int(np.floor(cap * len(normals)))
    if allowed <= 0:
        return float(np.nextafter(normals[-1], np.inf))
    return float(np.nextafter(normals[-allowed - 1], np.inf))


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    parser.add_argument("--bootstrap", type=int, default=2000)
    args = parser.parse_args()

    release = Release(args.release)
    train, cal = release.split("train"), release.split("calibration")
    y = cal["is_anomalous"].astype(int).to_numpy()
    lots = cal["lot_id"].to_numpy()
    specs = SpecLimits.load(release.specs_path())

    score = np.full(len(cal), np.nan)
    for _, tr_idx, va_idx in leave_one_lot_out(cal):
        core = StatisticalCore(config.DEPTHS).fit(train, cal.iloc[tr_idx])
        score[va_idx] = core.score(cal.iloc[va_idx], config.WEIGHTS)
    assert np.isfinite(score).all()
    np.save(RESULTS / "03_oof_scores.npy", score)

    grid = np.unique(np.quantile(score, np.linspace(0.50, 1.0, 400)))
    curve = pd.DataFrame([{"threshold": float(t), **confusion(y, score >= t)}
                          for t in grid])
    bands = lot_bootstrap(y, score, lots, curve["threshold"].to_numpy(), args.bootstrap)
    for key, values in bands.items():
        curve[key] = values
    curve.to_csv(RESULTS / "03_threshold_curve.csv", index=False)

    points = []
    for cap in BUDGETS:
        t = loosest_threshold(y, score, cap)
        row = {"fpr_budget": cap, "threshold": t, **confusion(y, score >= t)}
        nearest = int(np.argmin(np.abs(curve["threshold"].to_numpy() - t)))
        row.update({k: float(curve.iloc[nearest][k]) for k in bands})
        points.append(row)
    operating = loosest_threshold(y, score, config.OPERATING_FPR_BUDGET)

    # --- the zero-false-positive point, for comparison ---------------------
    normals = np.sort(score[y == 0])
    zero_fp_threshold = float(np.nextafter(normals[-1], np.inf))
    zero_fp = confusion(y, score >= zero_fp_threshold)
    points.append({"fpr_budget": 0.0, "threshold": zero_fp_threshold, **zero_fp})
    pd.DataFrame(points).to_csv(RESULTS / "03_operating_points.csv", index=False)

    # --- early-epoch thresholds, calibration normals only -------------------
    core_full = StatisticalCore(config.DEPTHS).fit(train, cal)
    early = {}
    for epoch in [0, 24, 96]:
        per_parameter = evidence.per_parameter(cal, epoch, core_full.reference)
        early_score = observed_evidence_score(per_parameter)
        early[str(epoch)] = loosest_threshold(y, early_score, config.EARLY_FPR_BUDGET)
    (RESULTS / "03_early_thresholds.json").write_text(json.dumps(early, indent=2))

    summary = {
        "protocol": "leave-one-lot-out over 12 calibration lots; rank reference "
                    "refitted per held-out lot; lot bootstrap for intervals",
        "weights": config.WEIGHTS,
        "operating_fpr_budget": config.OPERATING_FPR_BUDGET,
        "operating_threshold": operating,
        "zero_false_positive_threshold": zero_fp_threshold,
        "zero_false_positive_recall": zero_fp["recall"],
        "early_thresholds": early,
        "operating_points": points,
        "note": "A statistical threshold tuned to zero false positives on 852 "
                "calibration normals is a fitted quantity and will not stay at zero "
                "on an unseen lot. The CONFIRMED tier does not come from this curve; "
                "it comes from the datasheet limits in stage 2.",
    }
    (RESULTS / "03_threshold_curve.json").write_text(json.dumps(summary, indent=2, default=float))

    show = pd.DataFrame(points)[["fpr_budget", "threshold", "tp", "fp", "fn",
                                 "recall", "precision", "fpr", "flagged"]]
    for c in ["recall", "precision", "fpr"]:
        show[c] = show[c].astype(float).round(4)
    print(show.to_string(index=False))
    print(f"\noperating threshold at the {config.OPERATING_FPR_BUDGET:.0%} budget: {operating:.10f}")
    print(f"early thresholds: {json.dumps(early)}")


if __name__ == "__main__":
    main()
