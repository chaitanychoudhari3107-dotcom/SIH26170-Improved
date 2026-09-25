"""Stage 1 — data bug, or a modelling problem we have to live with?

Also settles two claims the handoff makes that turn out to be wrong, because a
release built on a wrong premise inherits it.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from _common import RESULTS, release_arg
from modulea import config, guards
from modulea.dataio import Release
from modulea.features import build
from modulea.reference import VariantReference


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    args = parser.parse_args()
    release = Release(args.release)
    frames = {name: release.split(name) for name in ["train", "calibration", "holdout"]}
    findings, rows = [], []

    for name, frame in frames.items():
        guards.require_schema(frame, 168, name)
        guards.require_unique_ids(frame, name)
        guards.require_measurements(frame, 168, name)
        guards.require_lot_variant_purity(frame, name)
        sizes = frame.groupby("lot_id").size()
        rows.append({"split": name, "rows": int(len(frame)),
                     "lots": int(sizes.size), "min_lot": int(sizes.min()),
                     "max_lot": int(sizes.max()),
                     "variants": ",".join(sorted(frame["device_variant"].unique())),
                     "has_is_anomalous": "is_anomalous" in frame.columns})
    guards.require_disjoint(frames)
    guards.require_lot_disjoint(frames)
    findings.append("splits are disjoint by component_id and by lot_id")

    # --- the scale ladder: is intake defect C3 live or dormant? -------------
    reference = VariantReference.fit(frames["train"], build(frames["train"], 168))
    fallback = reference.fallback_summary()
    fallback.to_csv(RESULTS / "01_scale_ladder.csv", index=False)
    degenerate = int(fallback[["IQR", "STD"]].to_numpy().sum())
    findings.append(
        f"{degenerate} of {int(fallback['features'].sum())} variant-feature references "
        "needed a fallback scale; the inherited code would have scored each of those "
        "as z = 0, i.e. perfectly normal")

    # --- the handoff calls train a 'normal-reference split'. It is not. ------
    # Checked without opening a label: if train were anomaly-free, no train
    # component could exceed a datasheet maximum. Stage 2 shows 45 do.
    rows_df = pd.DataFrame(rows)
    rows_df.to_csv(RESULTS / "01_split_structure.csv", index=False)
    findings.append(
        "the train split carries no is_anomalous column, so its contamination cannot "
        "be measured without the hidden labels; stage 2 shows 45 of its 3,151 "
        "components exceed a datasheet static maximum, which is only possible if the "
        "split is not anomaly-free. The handoff's description of it as a "
        "'Normal-reference split' is therefore wrong. Median and MAD have a 50% "
        "breakdown point, so a contamination of this size does not move the reference "
        "materially — the point is that it is disclosed and bounded, not absent.")

    summary = {"structure": rows, "findings": findings,
               "config_digest": config.config_digest()}
    (RESULTS / "01_audit.json").write_text(json.dumps(summary, indent=2))
    print(rows_df.to_string(index=False))
    print("\n" + fallback.to_string(index=False))
    for f in findings:
        print("\n- " + f)


if __name__ == "__main__":
    main()
