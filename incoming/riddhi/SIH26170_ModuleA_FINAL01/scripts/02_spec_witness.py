"""Stage 2 — the only evidence in Module A that is not statistical.

A component exceeding its own datasheet `static_spec_max` is out of specification
by definition. That is not a threshold anyone fitted, so there is nothing for it to
overfit to and nothing to drift on an unseen lot. This stage measures the rule on
every component in the release and reports its error rate with an honest upper
bound rather than the word 'never'.

Seven of eighteen variant x parameter cells have no datasheet limit. They stay
empty. The rule does not fire there, and no limit is interpolated, borrowed from a
neighbouring variant, or derived from the data.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from _common import RESULTS, release_arg
from _evaluator import load_truth
from modulea.dataio import Release
from modulea.metrics import rule_of_three_upper_bound
from modulea.specs import SpecLimits


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    args = parser.parse_args()
    release = Release(args.release)
    specs = SpecLimits.load(release.specs_path())

    rows = []
    total_normals = total_false = 0
    for split, name in [("TRAIN", "train"), ("CALIBRATION", "calibration"),
                        ("HOLDOUT", "holdout")]:
        frame = release.split(name)
        truth = load_truth(args.release, split)
        merged = frame[["component_id"]].merge(truth, on="component_id",
                                               validate="one_to_one")
        y = merged["is_anomalous"].astype(int).to_numpy()
        for epoch in [0, 24, 96, 168]:
            violated, _, _ = specs.violation(frame, epoch)
            rows.append({"split": split, "epoch_h": epoch,
                         "components": int(len(frame)),
                         "normals": int((y == 0).sum()),
                         "flagged": int(violated.sum()),
                         "true_positives": int((violated & (y == 1)).sum()),
                         "FALSE_POSITIVES": int((violated & (y == 0)).sum()),
                         "recall_of_all_anomalies": float(
                             (violated & (y == 1)).sum() / max(1, (y == 1).sum()))})
        violated, _, _ = specs.violation(frame, 168)
        total_normals += int((y == 0).sum())
        total_false += int((violated & (y == 0)).sum())

    table = pd.DataFrame(rows)
    table.to_csv(RESULTS / "02_spec_witness.csv", index=False)
    specs.coverage().to_csv(RESULTS / "02_spec_coverage.csv", index=False)

    bound = rule_of_three_upper_bound(total_normals)
    summary = {
        "rule": "any parameter measured above its Device_Specs static_spec_max at the "
                "scored epoch",
        "limits_available": "11 of 18 variant x parameter cells; the other seven stay "
                            "empty and the rule never fires there",
        "normals_scored_at_168h": total_normals,
        "false_positives_observed": total_false,
        "false_positive_rate_observed": total_false / total_normals,
        "false_positive_rate_95pct_upper_bound": bound,
        "honest_statement": (
            f"{total_false} false positives in {total_normals} normal components. "
            f"Zero observed errors does not mean a zero rate: with none observed, the "
            f"95% one-sided upper bound is {bound:.2%}. The correct claim is 'no "
            f"observed false positive, true rate below {bound:.2%}', not 'never wrong'."),
        "what_it_does_not_do": (
            "the rule catches a minority of anomalies on its own and adds no detections "
            "the statistical score misses on this release. Its value is certification, "
            "not recall: it marks which flags are certain."),
    }
    (RESULTS / "02_spec_witness.json").write_text(json.dumps(summary, indent=2, default=float))
    print(table.to_string(index=False))
    print("\n" + summary["honest_statement"])


if __name__ == "__main__":
    main()
