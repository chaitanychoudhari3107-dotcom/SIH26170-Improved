"""Stage 15 — actually join Module A to Module B, and prove it.

"It should join on component_id" is not the same statement as "it joins". This
performs the join fusion will perform, both ways, and records what a consumer will
find. It reads Module B's packet read-only and takes no position on its numbers.

It also builds the joined frame fusion would start from, so Anushka has a worked
example rather than a description.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from _common import PREDICTION, RESULTS
from modulea.constants import PARAMETERS
from modulea.freeze import sha256_file

A_FIELDS = ["component_id", "module_a_score", "module_a_disposition",
            "module_a_primary_parameter", "module_a_reason_codes"]
B_FIELDS = ["component_id", "module_b_primary_parameter", "module_b_reason_codes"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--module-b-packet", required=True,
                        help="root of the unpacked Module B integration packet")
    parser.add_argument("--epoch", type=int, default=168)
    args = parser.parse_args()
    mb = Path(args.module_b_packet)

    a = pd.read_csv(PREDICTION / f"ModuleA_Final_Holdout_{args.epoch}h.csv")
    b_path = mb / "prediction/ModuleB_Final_Holdout_Predictions.csv"
    b = pd.read_csv(b_path)
    b_receipt = json.loads((mb / "prediction/HOLDOUT_PREDICTION_RECEIPT.json").read_text())

    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL",
                       "detail": str(detail)})

    # --- B's own receipt, verified before anything is joined --------------
    check("Module B's prediction file matches its receipt hash",
          sha256_file(b_path) == b_receipt["prediction_output_sha256"],
          b_receipt["prediction_output_sha256"][:16])
    check("both modules name the same dataset",
          b_receipt["dataset"] == "SIH26170-FINAL-01", b_receipt["dataset"])

    # --- the join ----------------------------------------------------------
    a_ids, b_ids = set(a["component_id"]), set(b["component_id"])
    check("no duplicate component_id on either side",
          not a["component_id"].duplicated().any()
          and not b["component_id"].duplicated().any(),
          f"A {len(a)} rows / {len(a_ids)} ids, B {len(b)} rows / {len(b_ids)} ids")
    check("every Module A component has a Module B forecast",
          a_ids <= b_ids, f"{len(a_ids - b_ids)} missing")
    check("every Module B component has a Module A verdict",
          b_ids <= a_ids, f"{len(b_ids - a_ids)} missing")

    joined = a[A_FIELDS + ["module_a_evidence_tier"]].merge(
        b, on="component_id", how="inner", validate="one_to_one")
    check("the inner join keeps every row", len(joined) == len(a), len(joined))

    # --- column-name collisions, the classic integration bug --------------
    overlap = (set(a.columns) & set(b.columns)) - {"component_id"}
    check("no column name collides between the two contracts except the join key",
          not overlap, sorted(overlap) or "none")

    # --- semantics fusion must not get wrong -------------------------------
    check("Module A emits no REJECT",
          set(a["module_a_disposition"]) <= {"PASS", "MONITOR"},
          sorted(set(a["module_a_disposition"])))
    b_disposition = [c for c in b.columns if "disposition" in c.lower()]
    check("Module B emits no disposition column", not b_disposition,
          b_disposition or "none")

    # --- do the two modules point at the same parameter? -------------------
    both_named = joined[joined["module_a_primary_parameter"].ne("")
                        & joined["module_b_primary_parameter"].notna()]
    agreement = float((both_named["module_a_primary_parameter"]
                       == both_named["module_b_primary_parameter"]).mean()) \
        if len(both_named) else float("nan")

    # --- the corroboration view, built but NOT turned into a rule ----------
    corroborated = []
    for parameter, codes in zip(joined["module_a_primary_parameter"],
                                joined["module_b_reason_codes"].fillna("")):
        corroborated.append(bool(parameter) and
                            f"B_HIGH_FORECAST_DRIFT:{parameter}" in str(codes).split("|"))
    joined["b_evidence_status"] = np.where(
        joined["module_a_disposition"].eq("MONITOR"),
        np.where(corroborated, "SAME_PARAMETER_DRIFT_SUPPORT", "NO_MATCHING_DRIFT_CODE"),
        "NOT_APPLICABLE")

    joined.to_csv(RESULTS / "15_fusion_joined_holdout.csv", index=False)
    joined.head(60).to_csv(RESULTS / "15_fusion_joined_example_60_rows.csv", index=False)

    table = pd.DataFrame(checks)
    table.to_csv(RESULTS / "15_fusion_dryrun.csv", index=False)
    summary = {
        "module_b_release": b_receipt.get("release_candidate"),
        "module_b_prediction_sha256": b_receipt["prediction_output_sha256"],
        "rows_joined": int(len(joined)),
        "checks": checks,
        "failures": int(table.status.eq("FAIL").sum()),
        "primary_parameter_agreement_where_both_name_one": agreement,
        "primary_parameter_note":
            "A and B name the same parameter on a minority of components. That is "
            "expected and is not a defect in either: A names where a deviation is "
            "already observed, B names where drift is forecast. Fusion should treat "
            "agreement as corroboration and disagreement as two separate pieces of "
            "evidence, never as a contradiction to resolve.",
        "b_evidence_status_counts":
            joined["b_evidence_status"].value_counts().to_dict(),
        "warning":
            "b_evidence_status is a VIEW, not a rule. No Module A disposition changes "
            "because of it. A learned confirmation policy needs calibration-split B "
            "predictions made without target leakage, and those do not exist — it "
            "cannot be learned from the holdout forecasts and their labels.",
    }
    (RESULTS / "15_fusion_dryrun.json").write_text(json.dumps(summary, indent=2, default=float))
    print(table.to_string(index=False))
    print(f"\njoined rows: {len(joined)}")
    print(f"primary-parameter agreement where both name one: {agreement:.3f}")
    print(joined["b_evidence_status"].value_counts().to_string())


if __name__ == "__main__":
    main()
