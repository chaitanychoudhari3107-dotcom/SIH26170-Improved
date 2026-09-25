"""Stage 20 — the complete four-cell confusion matrix for every headline result.

Most tables in this release report the cells a reader asks for. This one reports all
four, always, for every result the release quotes anywhere — plus every rate derived
from them, plus a reconciliation that the cells sum to the number of components scored.

Why a whole stage for arithmetic: the cells are the only thing measured. Recall,
precision, FPR and F1 are all views of the same four numbers, and quoting one view
without the others is how a result gets oversold. "72% recall" and "65 caught, 25
missed, 13 healthy parts flagged, 1,240 left alone" are the same fact; only the second
tells a reviewer what their day looks like.

Also verifies, on the release's own data rather than on synthetic inputs, that the
implementation agrees with sklearn cell for cell.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix as sklearn_confusion

from _common import PREDICTION, RESULTS, release_arg
from _evaluator import load_truth
from modulea import config
from modulea.cv import leave_one_lot_out
from modulea.dataio import Release
from modulea.metrics import check_identities, confusion
from modulea.scoring import StatisticalCore
from modulea.specs import SpecLimits

MEANING = {
    "tp": "abnormal, and flagged — the screen worked",
    "tn": "healthy, and passed — the screen stayed out of the way",
    "fp": "HEALTHY, but flagged — costs review time, harms nobody",
    "fn": "ABNORMAL, but passed — a real defect reaches the next stage",
}
CELLS = ["tp", "tn", "fp", "fn"]


def row(label: str, scope: str, y: np.ndarray, flag: np.ndarray) -> dict:
    m = confusion(y, flag)
    check_identities(m)
    # Independent cross-check against sklearn, on real data, every run.
    tn, fp, fn, tp = sklearn_confusion(np.asarray(y, int), np.asarray(flag, int),
                                       labels=[0, 1]).ravel()
    if (m["tp"], m["tn"], m["fp"], m["fn"]) != (int(tp), int(tn), int(fp), int(fn)):
        raise AssertionError(
            f"{label}: modulea.metrics.confusion disagrees with sklearn — "
            f"ours {(m['tp'], m['tn'], m['fp'], m['fn'])} vs "
            f"sklearn {(int(tp), int(tn), int(fp), int(fn))}")
    return {"result": label, "scope": scope, **{k: m[k] for k in
            ["tp", "tn", "fp", "fn", "n", "positives", "negatives", "flagged", "passed",
             "recall", "specificity", "fpr", "fnr", "precision", "npv", "accuracy", "f1"]}}


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    args = parser.parse_args()
    release = Release(args.release)
    train, cal, hold = (release.split(s) for s in ["train", "calibration", "holdout"])
    specs = SpecLimits.load(release.specs_path())
    rows = []

    # ---- holdout, every epoch, the frozen predictions ---------------------
    truth_hold = load_truth(args.release, "HOLDOUT")
    for epoch in [0, 24, 96, 168]:
        predictions = pd.read_csv(PREDICTION / f"ModuleA_Final_Holdout_{epoch}h.csv")
        merged = predictions.merge(truth_hold, on="component_id", validate="one_to_one")
        y = merged["is_anomalous"].astype(int).to_numpy()
        flag = merged["module_a_disposition"].eq("MONITOR").to_numpy()
        rows.append(row(f"holdout @ {epoch} h — frozen release", "DIAGNOSTIC", y, flag))
        if epoch == 168:
            tier = merged["module_a_evidence_tier"]
            rows.append(row("holdout 168 h — CONFIRMED tier only", "DIAGNOSTIC",
                            y, tier.eq("CONFIRMED").to_numpy()))
            rows.append(row("holdout 168 h — statistical MONITOR tier only", "DIAGNOSTIC",
                            y, tier.eq("MONITOR").to_numpy()))

    # ---- the datasheet witness, every split ------------------------------
    for split, frame in [("TRAIN", train), ("CALIBRATION", cal), ("HOLDOUT", hold)]:
        truth = load_truth(args.release, split)
        merged = frame[["component_id"]].merge(truth, on="component_id",
                                               validate="one_to_one")
        y = merged["is_anomalous"].astype(int).to_numpy()
        violated, _, _ = specs.violation(frame, 168)
        rows.append(row(f"datasheet limit rule — {split}", "ALL SPLITS", y, violated))

    # ---- calibration, out of fold, the shipped configuration -------------
    y_cal = cal["is_anomalous"].astype(int).to_numpy()
    oof = np.full(len(cal), np.nan)
    for _, tr, va in leave_one_lot_out(cal):
        core = StatisticalCore(config.DEPTHS).fit(train, cal.iloc[tr])
        oof[va] = core.score(cal.iloc[va], config.WEIGHTS)
    violated_cal, _, _ = specs.violation(cal, 168)
    rows.append(row("calibration out-of-fold — shipped configuration",
                    "LEAVE-ONE-LOT-OUT",
                    y_cal, violated_cal | (oof >= config.OPERATING_THRESHOLD)))

    table = pd.DataFrame(rows)
    table.to_csv(RESULTS / "20_confusion_matrices.csv", index=False)

    # ---- reconciliation ---------------------------------------------------
    reconciliation = []
    for _, r in table.iterrows():
        reconciliation.append({
            "result": r["result"],
            "tp+tn+fp+fn": int(r.tp + r.tn + r.fp + r.fn),
            "components_scored": int(r.n),
            "balances": bool(int(r.tp + r.tn + r.fp + r.fn) == int(r.n)),
            "recall+fnr": None if np.isnan(r.recall) else round(r.recall + r.fnr, 12),
            "specificity+fpr": (None if np.isnan(r.specificity)
                                else round(r.specificity + r.fpr, 12)),
        })
    pd.DataFrame(reconciliation).to_csv(RESULTS / "20_reconciliation.csv", index=False)

    summary = {
        "what_each_cell_means": MEANING,
        "results_reported": int(len(table)),
        "all_balance": bool(all(r["balances"] for r in reconciliation)),
        "cross_checked_against": "sklearn.metrics.confusion_matrix, every row, every run",
        "headline": {
            "holdout_168h": {k: int(table[table.result.eq(
                "holdout @ 168 h — frozen release")][k].iloc[0]) for k in CELLS},
            "calibration_out_of_fold": {k: int(table[table.result.eq(
                "calibration out-of-fold — shipped configuration")][k].iloc[0])
                for k in CELLS},
            "datasheet_rule_all_splits": {
                k: int(table[table.result.str.startswith("datasheet limit rule")][k].sum())
                for k in CELLS},
        },
        "the_error_that_matters": (
            "FN. Every other cell costs time; a false negative sends a defective "
            "component onward. The release operates at a 1% false-alarm budget rather "
            "than a looser one because the curve's knee is there, not because false "
            "negatives are cheap — the trade is stated in docs/VALIDATION_SUMMARY.md "
            "and the operating point is a team decision (DECISION_LOG D2)."),
        "note_on_nan": (
            "a rate whose denominator is empty is reported NaN, never 0.0. A lot with "
            "no anomalies has no recall; printing 0.0 there would read as a failure "
            "that never happened."),
    }
    (RESULTS / "20_confusion_matrices.json").write_text(
        json.dumps(summary, indent=2, default=float))

    show = table[["result", "tp", "tn", "fp", "fn", "n", "recall", "precision",
                  "fpr", "fnr"]].copy()
    for c in ["recall", "precision", "fpr", "fnr"]:
        show[c] = show[c].astype(float).round(4)
    print(show.to_string(index=False))
    print(f"\nall {len(table)} matrices balance: "
          f"{all(r['balances'] for r in reconciliation)}")
    print("every row cross-checked against sklearn.metrics.confusion_matrix")


if __name__ == "__main__":
    main()
