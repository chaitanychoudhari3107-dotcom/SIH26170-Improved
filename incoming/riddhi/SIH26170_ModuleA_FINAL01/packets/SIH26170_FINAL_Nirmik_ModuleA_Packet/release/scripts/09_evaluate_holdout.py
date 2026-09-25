"""Stage 9 — DIAGNOSTIC. Open the labels, against predictions already on disk.

The predictions were written and hashed by stage 8 before this ran. This script
re-hashes them and refuses to report if they have changed, so a score can never
be produced against a prediction file that was touched after the fact.

Everything here is diagnostic. The holdout has shaped RC1, RC2 and RC3 design
discussions; it is not an independent test and no number from it is a
generalisation claim.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from sklearn.metrics import average_precision_score, roc_auc_score

from _common import PREDICTION, RESULTS, release_arg
from _evaluator import evaluate, load_truth
from modulea import config
from modulea.dataio import Release
from modulea.freeze import sha256_file
from modulea.scoring import StatisticalCore


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    args = parser.parse_args()
    receipt = json.loads((PREDICTION / "HOLDOUT_PREDICTION_RECEIPT.json").read_text())

    truth = load_truth(args.release, "HOLDOUT")
    report = {"status": "DIAGNOSTIC", "receipt_config_digest": receipt["config_digest"]}
    for epoch, recorded in receipt["outputs"].items():
        path = PREDICTION / recorded["file"]
        actual = sha256_file(path)
        if actual != recorded["sha256"]:
            raise SystemExit(
                f"{recorded['file']} changed after stage 8 wrote it "
                f"({recorded['sha256'][:12]} -> {actual[:12]}); refusing to score it")
        report[epoch] = evaluate(pd.read_csv(path), truth)

    report["warning"] = (
        "The holdout informed earlier redesign. These are comparisons against prior "
        "runs, not evidence of generalisation. A fresh lot-grouped test set after "
        "design freeze is still required.")
    (RESULTS / "09_holdout_diagnostic.json").write_text(json.dumps(report, indent=2, default=float))

    rows = []
    for epoch in ["0", "24", "96", "168"]:
        rows.append({"epoch_h": int(epoch), **report[epoch]["overall"]})
    table = pd.DataFrame(rows)
    table.to_csv(RESULTS / "09_holdout_metrics.csv", index=False)
    print(table.to_string(index=False))

    tiers = pd.DataFrame(report["168"]["tiers"])
    tiers.to_csv(RESULTS / "09_holdout_tiers.csv", index=False)
    print("\n168 h tiers:\n" + tiers.to_string(index=False))
    behaviour = pd.DataFrame(report["168"]["breakdowns"]["defect_behavior"])
    behaviour.to_csv(RESULTS / "09_holdout_by_behaviour.csv", index=False)
    print("\n168 h by behaviour:\n" + behaviour.to_string(index=False))

    ranking_comparison(args.release, truth)


def ranking_comparison(release_root, truth) -> None:
    """The shipped weights against the ones they replaced, on the holdout.

    This is the result that went the wrong way, so it is produced by a stage rather
    than by hand — a number nobody can regenerate is a number nobody can check, and a
    clean re-run must reproduce it like everything else.
    """
    release = Release(release_root)
    train, cal, hold = (release.split(s) for s in ["train", "calibration", "holdout"])
    labels = hold[["component_id"]].merge(truth[["component_id", "is_anomalous"]],
                                          on="component_id", validate="one_to_one")
    y = labels["is_anomalous"].astype(int).to_numpy()

    core = StatisticalCore(config.DEPTHS).fit(train, cal)
    shipped = core.score(hold, config.WEIGHTS)
    inherited = core.score(hold, config.LEGACY_WEIGHTS)

    matched = {}
    for n in [73, 78, 90, 100, 125]:
        matched[str(n)] = {
            "shipped": int(y[np.argsort(-shipped)[:n]].sum()),
            "inherited": int(y[np.argsort(-inherited)[:n]].sum())}

    out = {
        "status": "DIAGNOSTIC",
        "holdout_pr_auc_final01": float(average_precision_score(y, shipped)),
        "holdout_pr_auc_inherited": float(average_precision_score(y, inherited)),
        "holdout_roc_auc_final01": float(roc_auc_score(y, shipped)),
        "holdout_roc_auc_inherited": float(roc_auc_score(y, inherited)),
        "matched_workload": matched,
        "reading": "the shipped weights rank slightly WORSE here than the ones they "
                   "replaced. Within the noise the calibration bootstrap described, and "
                   "deliberately not acted on - see DECISION_LOG D6. A configuration "
                   "chosen before the holdout was seen cannot be rewritten by it.",
    }
    (RESULTS / "09_ranking_comparison.json").write_text(json.dumps(out, indent=2))
    print(f"\nranking on the holdout (DIAGNOSTIC): shipped PR AUC "
          f"{out['holdout_pr_auc_final01']:.4f}, inherited "
          f"{out['holdout_pr_auc_inherited']:.4f}")


if __name__ == "__main__":
    main()
