"""
moduleb.cv — whole-lot cross-validation.

One function, and it is the only place a model is scored against data it was
fitted on the complement of. Every number quoted anywhere in this project that
is not a calibration or holdout number comes through here.

The fold is the lot. `guards.assert_folds_are_whole_lots` is called on every
pass, so a future edit that accidentally reintroduces row-level splitting fails
the run rather than producing an optimistic table.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import baselines, guards, models
from .constants import PARAMS
from .metrics import metrics


def out_of_fold_predictions(feat: pd.DataFrame, p: str, cfg: dict) -> np.ndarray:
    """Out-of-fold 168h predictions for one parameter."""
    feat = feat.reset_index(drop=True)
    guards.assert_folds_are_whole_lots(feat, feat["fold"].to_numpy())
    folds = feat["fold"].to_numpy()
    yhat = np.full(len(feat), np.nan)
    for f in sorted(set(folds.tolist())):
        te = folds == f
        if te.all():
            raise ValueError("a fold holds every row; nothing left to train on")
        obj = models.fit_one(feat.loc[~te].reset_index(drop=True), p, cfg)
        yhat[te] = models.predict_one(obj, feat.loc[te].reset_index(drop=True), p)
    if np.isnan(yhat).any():
        raise RuntimeError(f"{p}: out-of-fold prediction left NaNs")
    return yhat


def cross_validate(feat: pd.DataFrame, config_by_param: dict[str, dict], *,
                   with_baselines: bool = True,
                   params: list[str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Returns (metric rows, out-of-fold prediction arrays).

    Metric rows are one per parameter x variant x model, plus a pooled
    variant='ALL' row so a per-variant table and an overall number never have to
    be reconciled by hand later.
    """
    feat = feat.reset_index(drop=True)
    params = params or PARAMS
    folds = feat["fold"].to_numpy()
    rows, oof = [], {}

    for p in params:
        yc = f"{p}_168h"
        yhat = out_of_fold_predictions(feat, p, config_by_param[p])
        oof[p] = yhat
        preds = {"MODULE_B": yhat}
        if with_baselines:
            preds.update(baselines.fold_baselines(feat, p, folds))

        groups = [("ALL", np.ones(len(feat), bool))]
        groups += [(v, (feat.device_variant == v).to_numpy())
                   for v in sorted(feat.device_variant.unique())]
        for v, sel in groups:
            for mname, yp in preds.items():
                rows.append(dict(param=p, variant=v, model=mname,
                                 **metrics(feat.loc[sel, yc], yp[sel], feat.loc[sel, "lot_id"])))
    return pd.DataFrame(rows), oof
