"""
moduleb.baselines — the transparent alternatives Module B has to beat.

A learned model is only worth its complexity if it beats these on held-out lots,
stably. They are refit inside the same folds as the model so the comparison is
like for like.

  Persistence        x168_hat = x24.                  No drift at all.
  LinExtrap          x168_hat = x24 + (x24 - x0)*6.   Straight-line extrapolation;
                     6 = (168-24)/24, so it assumes the first day's rate continues.
                     Burn-in drift is sub-linear, so this is expected to overshoot —
                     it is kept because overshoot is informative, not because it wins.
  MedianRatio_24h    x168_hat = x24 * median(x168/x24) over the TRAINING rows of the
                     same variant. The strongest of the three and the one that
                     actually matters: a single constant per variant per parameter.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

BASELINE_NAMES = ("Persistence", "LinExtrap", "MedianRatio_24h")

# (168 - 24) / 24
_LINEXTRAP_STEPS = 6.0


def persistence(feat: pd.DataFrame, p: str) -> np.ndarray:
    return feat[f"{p}_24h"].to_numpy(float).copy()


def linear_extrapolation(feat: pd.DataFrame, p: str) -> np.ndarray:
    x0 = feat[f"{p}_0h"].to_numpy(float)
    x24 = feat[f"{p}_24h"].to_numpy(float)
    return x24 + (x24 - x0) * _LINEXTRAP_STEPS


def median_ratio_fit(train: pd.DataFrame, p: str) -> dict[str, float]:
    """One ratio per variant, from training rows only."""
    out: dict[str, float] = {}
    for v, g in train.groupby("device_variant", sort=True):
        ratio = g[f"{p}_168h"].to_numpy(float) / g[f"{p}_24h"].to_numpy(float)
        if len(ratio) == 0 or not np.isfinite(ratio).all():
            raise ValueError(f"{p}/{v}: cannot fit a median ratio from {len(ratio)} rows")
        out[v] = float(np.median(ratio))
    return out


def median_ratio_predict(ratios: dict[str, float], feat: pd.DataFrame, p: str) -> np.ndarray:
    feat = feat.reset_index(drop=True)
    r = feat.device_variant.map(ratios)
    if r.isna().any():
        missing = sorted(feat.loc[r.isna(), "device_variant"].unique())
        raise KeyError(f"no median ratio fitted for variant(s) {missing}")
    return feat[f"{p}_24h"].to_numpy(float) * r.to_numpy(float)


def fold_baselines(feat: pd.DataFrame, p: str, folds: np.ndarray) -> dict[str, np.ndarray]:
    """All three baselines, out-of-fold, on the same whole-lot folds as the model."""
    feat = feat.reset_index(drop=True)
    folds = np.asarray(folds)
    out = {
        "Persistence": persistence(feat, p),
        "LinExtrap": linear_extrapolation(feat, p),
        "MedianRatio_24h": np.full(len(feat), np.nan),
    }
    for f in sorted(set(folds.tolist())):
        te = folds == f
        ratios = median_ratio_fit(feat.loc[~te], p)
        out["MedianRatio_24h"][te] = median_ratio_predict(ratios, feat.loc[te], p)
    if np.isnan(out["MedianRatio_24h"]).any():
        raise RuntimeError(f"median-ratio baseline left {p} rows unpredicted")
    return out
