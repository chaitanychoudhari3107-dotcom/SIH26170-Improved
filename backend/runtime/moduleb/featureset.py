"""
moduleb.featureset — which derived columns each model actually receives.

Three named feature sets, and one flag (`linear`) that decides whether the
redundant forms are included.

  own              the parameter's own 0h and 24h levels
  own+lot          + the same two statistics for the component's own lot
  own+lot+cross    + the other five parameters' 0h/24h levels and lot medians

For a linear model (OLS / Ridge / Huber) only the level terms are supplied,
because the deltas and lot deviations are exact linear combinations of them.
The tree model gets the redundant forms as well, since it cannot construct them.

`pooled=True` normalises every level column by the Device_Specs 0h baseline for
that parameter and variant, then appends a three-way variant one-hot. That is
what lets one model span CMOS_A/B/C: a delay in ns and a current in uA become
comparable multiples of a fixed external constant, and the one-hot carries
whatever variant-specific offset survives.
"""
from __future__ import annotations

import pandas as pd

from .constants import PARAMS, PREDICTOR_EPOCHS, VARIANTS
from .guards import LeakageError

FEATURE_SETS = ("own", "own+lot", "own+lot+cross")


def feature_cols(p: str, kind: str, *, linear: bool) -> list[str]:
    if p not in PARAMS:
        raise ValueError(f"unknown parameter {p!r}")
    own = [f"{p}_{e}" for e in PREDICTOR_EPOCHS]
    lot = [f"lotmed_{p}_{e}" for e in PREDICTOR_EPOCHS]
    cross = [f"{q}_{e}" for q in PARAMS if q != p for e in PREDICTOR_EPOCHS]
    crosslot = [f"lotmed_{q}_{e}" for q in PARAMS if q != p for e in PREDICTOR_EPOCHS]

    if kind == "own":
        f = list(own)
        if not linear:
            f += [f"reldelta_{p}"]
    elif kind == "own+lot":
        f = own + lot
        if not linear:
            f += [f"reldev_{p}_0h", f"reldev_{p}_24h", f"lotdrift_{p}", f"reldelta_{p}"]
    elif kind == "own+lot+cross":
        f = own + lot + cross + crosslot
        if not linear:
            f += ([f"reldev_{p}_0h", f"reldev_{p}_24h", f"lotdrift_{p}"]
                  + [f"reldelta_{q}" for q in PARAMS])
    else:
        raise ValueError(f"unknown feature set {kind!r}; expected one of {FEATURE_SETS}")
    return f


def _is_level(name: str) -> tuple[bool, str]:
    """Is this a raw or lot-median LEVEL column, and of which parameter?"""
    base = name[len("lotmed_"):] if name.startswith("lotmed_") else name
    for p in PARAMS:
        for e in PREDICTOR_EPOCHS:
            if base == f"{p}_{e}":
                return True, p
    return False, ""


def build_X(d: pd.DataFrame, p: str, kind: str, *, linear: bool, pooled: bool,
            keep: list[str] | None = None) -> pd.DataFrame:
    """Assemble the design matrix for one parameter.

    `keep` is the inference path: it reproduces the exact column list seen at fit
    time. A column that was present then and is missing now raises rather than
    being filled with zero — a silent 0.0 in a level column is not a missing
    value, it is a wrong measurement, and it would corrupt the prediction quietly.
    Only the variant one-hot columns may legitimately be absent-and-zero, because
    a batch containing just one variant genuinely has zeros for the others.
    """
    cols = feature_cols(p, kind, linear=linear)
    missing = [c for c in cols if c not in d.columns]
    if missing:
        raise LeakageError(f"feature columns absent from the frame: {missing}")

    X = d[cols].copy().reset_index(drop=True)

    if pooled:
        for c in cols:
            is_level, q = _is_level(c)
            if is_level:
                X[c] = d[c].to_numpy(float) / d[f"spec_{q}"].to_numpy(float)
        oh = pd.get_dummies(d.device_variant, prefix="var").astype(float).reset_index(drop=True)
        for v in VARIANTS:
            if f"var_{v}" not in oh.columns:
                oh[f"var_{v}"] = 0.0
        X = pd.concat([X, oh[[f"var_{v}" for v in VARIANTS]]], axis=1)

    if keep is not None:
        absent = [c for c in keep if c not in X.columns and not c.startswith("var_")]
        if absent:
            raise LeakageError(
                f"feature columns present at fit time are missing at predict time: {absent}")
        return X.reindex(columns=keep, fill_value=0.0)

    nun = X.nunique()
    return X.loc[:, nun[nun > 1].index]   # drop degenerate constant columns
