"""
moduleb.dataio — loading, hashing and the one place file paths are written down.

Every load goes through `load_split`, so no stage can quietly read a file that
skipped the guards. The SHA-256 of each file is recorded and carried into the
freeze manifest: if Chaitany reissues a CSV, the manifest stops matching and the
frozen model is provably stale.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from . import guards
from .constants import DATASET_ID, PARAMS

# Paths are relative to the project root so the same call works from a script,
# a notebook or a test.
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"

PATHS = dict(
    train=DATA / "01_BUILD" / "ModuleB_Train.csv",
    calibration=DATA / "02_CALIBRATE" / "ModuleB_Calibration.csv",
    holdout=DATA / "03_HOLDOUT_AFTER_FREEZE" / "ModuleB_Holdout.csv",
    specs=DATA / "REFERENCE" / "Device_Specs.csv",
    dictionary=DATA / "REFERENCE" / "Schema_Data_Dictionary.csv",
    contract=DATA / "REFERENCE" / "ModuleB_Output_Contract.csv",
    version=DATA / "REFERENCE" / "Dataset_Version_Safe.json",
)

# allow_target per split. The holdout is False and there is no switch to make it
# True: a holdout file with answers in it is a data bug, not a convenience.
_ALLOW_TARGET = dict(train=True, calibration=True, holdout=False)


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Split:
    name: str
    path: Path
    frame: pd.DataFrame
    sha256: str
    has_targets: bool

    @property
    def n_rows(self) -> int:
        return len(self.frame)

    @property
    def n_lots(self) -> int:
        return int(self.frame.lot_id.nunique())

    def describe(self) -> str:
        return (f"{self.name}: {self.n_rows} rows, {self.n_lots} lots, "
                f"{self.frame.device_variant.nunique()} variants, "
                f"targets={'yes' if self.has_targets else 'no'}, sha256={self.sha256[:16]}")


def load_split(name: str, path: str | Path | None = None) -> Split:
    """Read one split and run every guard before returning it."""
    if name not in _ALLOW_TARGET:
        raise ValueError(f"unknown split {name!r}; expected one of {sorted(_ALLOW_TARGET)}")
    p = Path(path) if path is not None else PATHS[name]
    if not p.exists():
        raise FileNotFoundError(f"{name} split not found at {p}")
    df = pd.read_csv(p)
    allow = _ALLOW_TARGET[name]
    guards.assert_input_clean(df, allow_target=allow, name=name)
    guards.assert_data_quality(df, name=name, expect_targets=allow)
    return Split(name=name, path=p, frame=df.reset_index(drop=True),
                 sha256=file_sha256(p), has_targets=allow)


def load_specs(path: str | Path | None = None):
    """Device_Specs.csv -> (baselines, limits), both indexed by device_variant.

    `limits` deliberately keeps NaN where Device_Specs has no `static_spec_max`.
    Seven of the eighteen variant x parameter cells have none, and per decision
    D1 no limit is invented for them: the limit-based reason codes simply never
    fire there. Filling a zero or a guess would manufacture false positives.
    """
    p = Path(path) if path is not None else PATHS["specs"]
    s = pd.read_csv(p)
    base = s.pivot_table(index="device_variant", columns="parameter",
                         values="synthetic_baseline_0h")
    lim = s.pivot_table(index="device_variant", columns="parameter",
                        values="static_spec_max", dropna=False)
    for prm in PARAMS:
        if prm not in base.columns or base[prm].isna().any():
            raise guards.DataQualityError(
                f"Device_Specs.csv has no usable 0h baseline for {prm}")
        if prm not in lim.columns:
            lim[prm] = np.nan
    return base, lim[PARAMS]


def load_dataset_version(path: str | Path | None = None) -> dict:
    p = Path(path) if path is not None else PATHS["version"]
    meta = json.loads(Path(p).read_text())
    if meta.get("dataset_id") != DATASET_ID:
        raise guards.DataQualityError(
            f"dataset id is {meta.get('dataset_id')!r}, this package targets {DATASET_ID!r}. "
            "Mixing results across dataset versions is how a stale number gets quoted.")
    return meta


def expected_contract_columns(path: str | Path | None = None) -> list[str]:
    """Read the contract header from the REFERENCE CSV rather than trusting code."""
    p = Path(path) if path is not None else PATHS["contract"]
    return pd.read_csv(p, nrows=0).columns.tolist()


def write_result(df: pd.DataFrame, filename: str, *, subdir: str = "") -> Path:
    out = RESULTS / subdir if subdir else RESULTS
    out.mkdir(parents=True, exist_ok=True)
    dest = out / filename
    df.to_csv(dest, index=False)
    return dest
