"""Stage 6 — rehearse freeze and serving on a stand-in, before spending the real one."""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import pandas as pd

from _common import RESULTS, release_arg
from modulea import config, contract
from modulea.dataio import Release
from modulea.freeze import freeze, load
from modulea.predict import ModuleA
from modulea.scoring import StatisticalCore
from modulea.specs import SpecLimits


def build_model(release: Release) -> ModuleA:
    train, cal = release.split("train"), release.split("calibration")
    core = StatisticalCore(config.DEPTHS).fit(train, cal)
    early = json.loads((RESULTS / "03_early_thresholds.json").read_text())
    return ModuleA(core, SpecLimits.load(release.specs_path()), config.WEIGHTS,
                   config.OPERATING_THRESHOLD, {int(k): v for k, v in early.items()},
                   release.expected_lot_sizes(), config.MODEL_VERSION, config.DATASET_ID)


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    args = parser.parse_args()
    release = Release(args.release)
    model = build_model(release)

    # The stand-in is the calibration split — already seen, so nothing is spent.
    stand_in = release.split("calibration")
    results = {}
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "dryrun.joblib"
        receipt = freeze(model, path, "Dry run — rehearsal only, not a release sign-off "
                                      "and never used to serve.",
                         {k: v for k, v in release.hashes().items()
                          if k in ("train", "calibration")})
        reloaded, _ = load(path)
        for epoch in [0, 24, 96, 168]:
            before = model.predict(stand_in, epoch)
            after = reloaded.predict(stand_in, epoch)
            pd.testing.assert_frame_equal(before, after)
            contract.validate_output(after, model.operating_threshold if epoch == 168
                                     else model.early_thresholds[epoch])
            results[str(epoch)] = {
                "rows": int(len(after)),
                "monitor": int(after["module_a_disposition"].eq("MONITOR").sum()),
                "confirmed": int(after["module_a_evidence_tier"].eq("CONFIRMED").sum()),
                "reload_identical": True}
        results["preflight_checks"] = receipt["preflight_checks_passed"]
    (RESULTS / "06_dryrun.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
