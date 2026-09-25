"""Stage 8 — GATED. The one-shot holdout run.

Predictions are written and hashed BEFORE any label is opened. The evaluation in
stage 09 reads that file from disk; it cannot reach back and change it.
"""
from __future__ import annotations

import argparse
import json

from _common import MODELS, PREDICTION, RESULTS, release_arg
from modulea.dataio import Release, sha256
from modulea.freeze import load, sha256_file


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    parser.add_argument("--epochs", type=int, nargs="+", default=[0, 24, 96, 168])
    args = parser.parse_args()

    release = Release(args.release)
    model, payload = load(MODELS / "module_a_final01.joblib")

    written = {}
    for epoch in args.epochs:
        out = model.predict(release.split("holdout"), epoch)
        path = PREDICTION / f"ModuleA_Final_Holdout_{epoch}h.csv"
        out.to_csv(path, index=False)
        written[str(epoch)] = {"file": path.name, "rows": int(len(out)),
                               "sha256": sha256_file(path),
                               "monitor": int(out["module_a_disposition"].eq("MONITOR").sum()),
                               "confirmed": int(out["module_a_evidence_tier"].eq("CONFIRMED").sum())}
    receipt = {
        "receipt": "HOLDOUT_PREDICTION_RECEIPT",
        "module": "A",
        "release_candidate": payload["release_candidate"],
        "dataset_id": payload["dataset_id"],
        "frozen_artifact_sha256": sha256_file(MODELS / "module_a_final01.joblib"),
        "config_digest": payload["config_digest"],
        "runtime_contract_digest": payload["runtime_contract_digest"],
        "team_signoff": payload["team_signoff"],
        "holdout_input_sha256": sha256(release.path("holdout")),
        "monitor_floor": model.monitor_floor,
        "operating_threshold": model.operating_threshold,
        "outputs": written,
        "labels_opened": False,
    }
    (PREDICTION / "HOLDOUT_PREDICTION_RECEIPT.json").write_text(json.dumps(receipt, indent=2))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
