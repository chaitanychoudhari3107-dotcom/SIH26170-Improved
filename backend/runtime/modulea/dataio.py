"""Reading the release. The only module that knows the folder layout.

The hidden ground truth is not reachable from here. It has exactly one door,
`scripts/_evaluator.py`, and that door is never imported by a fitting path.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

EXPECTED_HASHES = {
    "train": "8f818f1b2ed5799904ea969d1bde3e3bafef09bf17bda04ce2e47f76a3b33e45",
    "calibration": "1b7d6c4ac457c421136ef9ebc7c11f52bf6255cc052a39669149e465bed23611",
    "holdout": "2030d38ef72ca2878ef4defaf2f9668d77eb73f2487490e679ecaedfeb3659a1",
}
FILES = {
    "train": "module_a/ModuleA_Train.csv",
    "calibration": "module_a/ModuleA_Calibration.csv",
    "holdout": "module_a/ModuleA_Holdout.csv",
}
SPECS = "integration_safe/Device_Specs.csv"
MANIFEST = "integration_safe/Safe_Lot_Split_Manifest.csv"
CONTRACT = "integration_safe/ModuleA_Output_Contract.csv"


def sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class Release:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        if not (self.root / FILES["train"]).exists():
            raise FileNotFoundError(
                f"{self.root} does not look like SIH26170_FINAL_RELEASE_01 "
                f"(expected {FILES['train']})")

    def path(self, split: str) -> Path:
        return self.root / FILES[split]

    def split(self, name: str) -> pd.DataFrame:
        return pd.read_csv(self.path(name))

    def hashes(self) -> dict[str, str]:
        return {name: sha256(self.path(name)) for name in FILES}

    def verify_hashes(self) -> dict[str, bool]:
        observed = self.hashes()
        return {k: observed[k] == v for k, v in EXPECTED_HASHES.items()}

    def lot_manifest(self) -> pd.DataFrame:
        return pd.read_csv(self.root / MANIFEST)

    def expected_lot_sizes(self, split: str | None = None) -> dict[str, int]:
        manifest = self.lot_manifest()
        if split is not None:
            manifest = manifest[manifest["split"].str.upper().eq(split.upper())]
        return dict(zip(manifest["lot_id"], manifest["component_count"].astype(int)))

    def specs_path(self) -> Path:
        return self.root / SPECS

    def contract_columns(self) -> list[str]:
        return list(pd.read_csv(self.root / CONTRACT).columns)
