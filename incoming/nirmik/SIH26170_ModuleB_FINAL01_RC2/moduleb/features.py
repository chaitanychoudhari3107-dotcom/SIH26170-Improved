"""
moduleb.features — derived columns, all of them computable at prediction time.

The rule every feature here obeys: it is a function of (a) this component's own
0h and 24h measurements, (b) the 0h/24h measurements of the other components in
THIS component's own lot, and (c) the fixed Device_Specs 0h baseline for the
variant. Nothing else.

Why that matters, concretely:

* lot medians are computed within the component's own lot, so they are available
  for an unseen holdout lot with no information from any training lot. They
  therefore cannot leak across a whole-lot fold boundary either — the fold is
  the lot, and the statistic never crosses it.
* the Device_Specs baseline is an external constant fixed before the data
  existed. Using it to normalise scale is not learning anything from the fold.
* no feature reads a 96h column, a 168h column, or any generator label. That is
  enforced by guards.assert_feature_matrix_clean on the actual matrix.

A subtlety that bit the Candidate V1 benchmark and is called out here so it is
not reintroduced: delta = x24 - x0 and dev = x - lot_median are EXACT linear
combinations of the level terms. Handing all of them to OLS/Ridge/Huber at once
is exact collinearity. featureset.py keeps a full-rank basis for the linear
models and gives the redundant forms only to the tree, which cannot build linear
combinations itself.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .constants import PARAMS, PREDICTOR_EPOCHS
from .guards import DataQualityError


def add_features(df: pd.DataFrame, base: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of `df` with the derived columns appended.

    `base` is the variant x parameter table of Device_Specs 0h baselines.
    """
    d = df.copy().reset_index(drop=True)
    g = d.groupby("lot_id")

    for p in PARAMS:
        x0 = d[f"{p}_0h"].to_numpy(float)
        x24 = d[f"{p}_24h"].to_numpy(float)
        if (x0 <= 0).any() or (x24 <= 0).any():
            # guards.assert_data_quality should have caught this already; the
            # duplicate check is cheap and the alternative is a silent inf.
            raise DataQualityError(
                f"{p}: non-positive 0h/24h value would divide by zero in a relative feature")

        # lot context, own lot only
        for e in PREDICTOR_EPOCHS:
            d[f"lotmed_{p}_{e}"] = g[f"{p}_{e}"].transform("median")

        # fixed external scale
        d[f"spec_{p}"] = d.device_variant.map(base[p])
        if d[f"spec_{p}"].isna().any():
            miss = sorted(d.loc[d[f"spec_{p}"].isna(), "device_variant"].unique())
            raise DataQualityError(f"no Device_Specs 0h baseline for {p} / variants {miss}")

        lm0 = d[f"lotmed_{p}_0h"].to_numpy(float)
        lm24 = d[f"lotmed_{p}_24h"].to_numpy(float)

        # how much the whole lot moved early — a lot-level ageing signal
        d[f"lotdrift_{p}"] = (lm24 - lm0) / lm0
        # how much this component moved early, scale-free
        d[f"reldelta_{p}"] = (x24 - x0) / x0
        # how far this component sits from its own lot, at each epoch
        d[f"reldev_{p}_0h"] = x0 / lm0 - 1.0
        d[f"reldev_{p}_24h"] = x24 / lm24 - 1.0

    derived = [c for c in d.columns if c.startswith(("lotmed_", "spec_", "lotdrift_",
                                                     "reldelta_", "reldev_"))]
    bad = d[derived].to_numpy(float)
    if not np.isfinite(bad).all():
        cols = [c for c in derived if not np.isfinite(d[c].to_numpy(float)).all()]
        raise DataQualityError(f"derived features are non-finite in {cols}")
    return d


def make_folds(df: pd.DataFrame, n_folds: int) -> pd.Series:
    """Whole-lot folds, balanced across variants, fully deterministic.

    Lots are sorted by name and dealt round-robin within each variant, so every
    fold holds out complete lots from all three variants where the counts allow.
    No randomness: the same file always produces the same fold map, which is what
    makes a benchmark rerun comparable rather than merely similar.
    """
    if n_folds < 2:
        raise ValueError("n_folds must be at least 2")
    fold_of: dict[str, int] = {}
    for _, g in df.groupby("device_variant", sort=True):
        for i, lot in enumerate(sorted(g.lot_id.unique())):
            fold_of[lot] = i % n_folds
    folds = df.lot_id.map(fold_of)
    if folds.isna().any():
        raise DataQualityError("fold assignment left some lots unmapped")
    return folds.astype(int)
