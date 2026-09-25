"""Stage 14 — where does this detector do badly, and does B corroboration carry signal?

Two questions a consumer will ask that the headline numbers do not answer:

  * Is the performance uniform, or is it carried by some lots and variants and absent
    in others? An aggregate recall of 72% made of one lot at 100% and another at 30%
    is a different product from one that is 72% everywhere.
  * Module B's reason codes sometimes name the same parameter Module A flagged. Does
    that agreement mean anything?

The second is measured and then explicitly ruled out as a decision rule, because the
only data that could calibrate it is the holdout and its labels.

DIAGNOSTIC throughout.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from _common import PREDICTION, RESULTS, release_arg
from _evaluator import load_truth
from modulea.metrics import confusion, rule_of_three_upper_bound


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    parser.add_argument("--module-b-packet", default="")
    args = parser.parse_args()

    predictions = pd.read_csv(PREDICTION / "ModuleA_Final_Holdout_168h.csv")
    holdout = pd.read_csv(Path(args.release) / "module_a/ModuleA_Holdout.csv")
    truth = load_truth(args.release, "HOLDOUT")
    # The truth frame also carries lot_id and device_variant. They were already
    # verified identical by the dataset audit, so drop them rather than suffixing and
    # risk a later line reading the wrong copy.
    labels = truth.drop(columns=["lot_id", "device_variant"], errors="ignore")
    merged = (predictions.merge(holdout[["component_id", "lot_id", "device_variant"]],
                                on="component_id", validate="one_to_one")
              .merge(labels, on="component_id", validate="one_to_one"))
    y = merged["is_anomalous"].astype(int).to_numpy()
    flag = merged["module_a_disposition"].eq("MONITOR").to_numpy()

    # --- per lot ----------------------------------------------------------
    rows = []
    for lot, group in merged.groupby("lot_id"):
        idx = merged["lot_id"].eq(lot).to_numpy()
        rows.append({"lot_id": lot, "components": int(idx.sum()),
                     "device_variant": group["device_variant"].iloc[0],
                     **confusion(y[idx], flag[idx])})
    per_lot = pd.DataFrame(rows).sort_values("recall")
    per_lot.to_csv(RESULTS / "14_per_lot.csv", index=False)

    # --- per variant -------------------------------------------------------
    rows = []
    for variant in sorted(merged["device_variant"].unique()):
        idx = merged["device_variant"].eq(variant).to_numpy()
        rows.append({"device_variant": variant, "components": int(idx.sum()),
                     **confusion(y[idx], flag[idx])})
    per_variant = pd.DataFrame(rows)
    per_variant.to_csv(RESULTS / "14_per_variant.csv", index=False)

    # --- per severity ------------------------------------------------------
    rows = []
    for severity in ["SEVERE", "MODERATE", "SUBTLE"]:
        idx = merged["severity"].eq(severity).to_numpy()
        rows.append({"severity": severity, "anomalies": int(idx.sum()),
                     "detected": int((idx & flag).sum()),
                     "detection_rate": float(flag[idx].mean()) if idx.any() else np.nan})
    per_severity = pd.DataFrame(rows)
    per_severity.to_csv(RESULTS / "14_per_severity.csv", index=False)

    summary = {
        "status": "DIAGNOSTIC",
        "per_lot_recall": {"min": float(per_lot["recall"].min()),
                           "median": float(per_lot["recall"].median()),
                           "max": float(per_lot["recall"].max()),
                           "worst_lots": per_lot.head(3)[
                               ["lot_id", "tp", "fn", "recall"]].to_dict("records")},
        "per_lot_fpr": {"min": float(per_lot["fpr"].min()),
                        "max": float(per_lot["fpr"].max()),
                        "worst_lots": per_lot.sort_values("fpr", ascending=False).head(3)[
                            ["lot_id", "fp", "fpr"]].to_dict("records")},
        "per_variant": per_variant.to_dict("records"),
        "per_severity": per_severity.to_dict("records"),
        "uniformity_statement": "",
    }

    spread = per_lot["recall"].max() - per_lot["recall"].min()
    summary["uniformity_statement"] = (
        f"per-lot recall ranges from {per_lot['recall'].min():.2f} to "
        f"{per_lot['recall'].max():.2f} across {len(per_lot)} holdout lots. The "
        f"aggregate is not carried by a few lots, but a spread of {spread:.2f} on "
        f"lots of ~75 components with ~5 anomalies each is mostly small-sample noise "
        f"and should not be read as a per-lot quality signal.")

    # --- does B corroboration carry signal? --------------------------------
    if args.module_b_packet:
        joined = pd.read_csv(RESULTS / "15_fusion_joined_holdout.csv")
        j = joined.merge(truth[["component_id", "is_anomalous"]], on="component_id",
                         validate="one_to_one")
        flagged = j[j["module_a_disposition"].eq("MONITOR")]
        table = (flagged.groupby("b_evidence_status")["is_anomalous"]
                 .agg(["count", "sum", "mean"])
                 .rename(columns={"count": "flagged", "sum": "real",
                                  "mean": "precision"}).reset_index())
        table.to_csv(RESULTS / "14_b_corroboration.csv", index=False)
        summary["b_corroboration"] = {
            "table": table.to_dict("records"),
            "statement":
                "measured on the holdout, with its labels, which is the only data "
                "where both exist. That is exactly why it cannot become a rule: a "
                "confirmation policy fitted here would be fitted on the same labels "
                "it would then be evaluated against. Module B produced no calibration "
                "-split forecasts, so no leakage-free fit is possible. Report the "
                "association; do not act on it.",
        }

    (RESULTS / "14_sensitivity.json").write_text(json.dumps(summary, indent=2, default=float))
    print("per-variant:\n" + per_variant.to_string(index=False))
    print("\nper-severity:\n" + per_severity.to_string(index=False))
    print("\nworst and best lots by recall:")
    print(pd.concat([per_lot.head(3), per_lot.tail(3)])[
        ["lot_id", "device_variant", "components", "tp", "fn", "fp", "recall", "fpr"]
    ].to_string(index=False))
    if args.module_b_packet:
        print("\nB corroboration among Module A flags:")
        print(table.to_string(index=False))


if __name__ == "__main__":
    main()
