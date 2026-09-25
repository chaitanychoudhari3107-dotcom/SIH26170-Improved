"""Stage 7 — GATED. Freeze the model.

A freeze needs a real recorded sign-off passed on the command line. The preflight
re-checks every release decision mechanically at this moment; one that no longer
holds stops the freeze. The sign-off is embedded in the artifact before the bytes
are written, so an artifact cannot circulate without it.
"""
from __future__ import annotations

import argparse
import json

from _common import MODELS, RESULTS, release_arg
from modulea import config
from modulea.dataio import Release
from modulea.freeze import freeze

import importlib.util, pathlib
_spec = importlib.util.spec_from_file_location(
    "dryrun", pathlib.Path(__file__).with_name("06_dryrun.py"))
_dryrun = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dryrun)


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    parser.add_argument("--signoff", required=True,
                        help="the recorded team sign-off, verbatim")
    args = parser.parse_args()

    release = Release(args.release)
    if not all(release.verify_hashes().values()):
        raise SystemExit("input hashes do not match the frozen release; refusing to freeze")

    model = _dryrun.build_model(release)
    receipt = freeze(model, MODELS / "module_a_final01.joblib", args.signoff,
                     {k: v for k, v in release.hashes().items()
                      if k in ("train", "calibration")},
                     notes={"holdout_hash_recorded_not_read": release.hashes()["holdout"]})
    (MODELS / "FREEZE_RECEIPT.json").write_text(json.dumps(receipt, indent=2, default=str))
    print(json.dumps(receipt, indent=2, default=str))


if __name__ == "__main__":
    main()
