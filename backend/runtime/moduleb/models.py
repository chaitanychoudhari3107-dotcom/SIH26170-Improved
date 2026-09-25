"""
moduleb.models — estimator construction, and fit/predict for one parameter.

The target parameterisation is the important design choice here, so it is stated
plainly: the model does not predict the 168h level. It predicts the RELATIVE
change from the 24h reading,

    y = (x168 - x24) / x24            and       x168_hat = x24 * (1 + y_hat)

Two reasons. First, it makes the three variants commensurable, which is what
allows one pooled model instead of three thin ones. Second, it means the model
only has to learn the drift, not re-derive the component's level — the level is
already measured, and re-predicting it would let a large, easy, uninformative
component of the variance dominate the fit.

Every estimator is deterministic given moduleb.config.GLOBAL_SEED.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import HuberRegressor, LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config, guards
from .constants import PARAMS
from .featureset import build_X

LINEAR_MODELS = frozenset({"OLS", "Ridge", "Huber"})
MODEL_NAMES = ("OLS", "Ridge", "Huber", "GBR")

# Fits that hit the iteration cap instead of converging. A HuberRegressor that
# stops on max_iter has not solved its own objective, so its coefficients are
# whatever the optimiser happened to be holding. That is not automatically fatal
# — the fit is often close — but it must never be invisible, so every occurrence
# is recorded here and the runner scripts print the tally.
CONVERGENCE_ISSUES: list[dict] = []


def _record_convergence(est, param: str, tag: str) -> None:
    inner = est[-1] if hasattr(est, "__getitem__") and hasattr(est, "steps") else est
    n_iter = getattr(inner, "n_iter_", None)
    if n_iter is None:
        return
    n_iter = int(np.ravel(n_iter)[0])
    cap = getattr(inner, "max_iter", None)
    if cap is not None and n_iter >= int(cap):
        CONVERGENCE_ISSUES.append(dict(param=param, tag=tag,
                                       estimator=type(inner).__name__,
                                       n_iter=n_iter, max_iter=int(cap)))


def make_model(name: str):
    """Standardisation is inside the pipeline, so it is refit per fold and can
    never see a validation lot's scale."""
    if name == "OLS":
        return make_pipeline(StandardScaler(), LinearRegression())
    if name == "Ridge":
        return make_pipeline(StandardScaler(), Ridge(**config.RIDGE))
    if name == "Huber":
        return make_pipeline(StandardScaler(), HuberRegressor(**config.HUBER))
    if name == "GBR":
        return GradientBoostingRegressor(**config.GBR)
    raise ValueError(f"unknown model {name!r}; expected one of {MODEL_NAMES}")


@dataclass
class ParamModel:
    """One fitted estimator plus everything needed to reproduce its input."""
    param: str
    structure: str          # "pooled" | "per-variant"
    model_name: str
    feature_set: str
    columns: list[str]
    estimator: object
    target: str             # "rel_delta" (pooled) | "abs_delta" (per-variant)
    n_train: int = 0
    variant: str | None = None
    meta: dict = field(default_factory=dict)


def _fit_pooled(train: pd.DataFrame, p: str, cfg: dict) -> ParamModel:
    linear = cfg["model"] in LINEAR_MODELS
    X = build_X(train, p, cfg["features"], linear=linear, pooled=True)
    guards.assert_feature_matrix_clean(X, name=f"fit/{p}")
    x24 = train[f"{p}_24h"].to_numpy(float)
    y = (train[f"{p}_168h"].to_numpy(float) - x24) / x24
    est = make_model(cfg["model"]).fit(X.to_numpy(float), y)
    _record_convergence(est, p, "pooled")
    return ParamModel(p, "pooled", cfg["model"], cfg["features"],
                      list(X.columns), est, "rel_delta", n_train=len(train))


def _fit_per_variant(train: pd.DataFrame, p: str, cfg: dict) -> dict[str, ParamModel]:
    linear = cfg["model"] in LINEAR_MODELS
    out: dict[str, ParamModel] = {}
    for v, gv in train.groupby("device_variant", sort=True):
        X = build_X(gv, p, cfg["features"], linear=linear, pooled=False)
        guards.assert_feature_matrix_clean(X, name=f"fit/{p}/{v}")
        y = gv[f"{p}_168h"].to_numpy(float) - gv[f"{p}_24h"].to_numpy(float)
        est = make_model(cfg["model"]).fit(X.to_numpy(float), y)
        _record_convergence(est, p, f"per-variant/{v}")
        out[v] = ParamModel(p, "per-variant", cfg["model"], cfg["features"],
                            list(X.columns), est, "abs_delta", n_train=len(gv), variant=v)
    return out


def fit_one(train: pd.DataFrame, p: str, cfg: dict):
    """Fit the model for one parameter. Returns a ParamModel, or a dict of them
    keyed by variant when the structure is per-variant."""
    if p not in PARAMS:
        raise ValueError(f"unknown parameter {p!r}")
    if f"{p}_168h" not in train.columns:
        raise guards.LeakageError(f"cannot fit {p}: no 168h target in the training frame")
    if cfg["structure"] == "pooled":
        return _fit_pooled(train, p, cfg)
    if cfg["structure"] == "per-variant":
        return _fit_per_variant(train, p, cfg)
    raise ValueError(f"unknown structure {cfg['structure']!r}")


def predict_one(obj, feat: pd.DataFrame, p: str) -> np.ndarray:
    """Predict the 168h level for one parameter.

    `feat` must carry the derived columns (features.add_features) and must be
    positionally indexed 0..n-1; the per-variant branch writes back by position.
    """
    feat = feat.reset_index(drop=True)
    x24 = feat[f"{p}_24h"].to_numpy(float)

    if isinstance(obj, ParamModel):
        X = build_X(feat, p, obj.feature_set,
                    linear=obj.model_name in LINEAR_MODELS,
                    pooled=obj.structure == "pooled", keep=obj.columns)
        guards.assert_feature_matrix_clean(X, name=f"predict/{p}")
        d = obj.estimator.predict(X.to_numpy(float))
        return x24 * (1.0 + d) if obj.target == "rel_delta" else x24 + d

    yhat = np.full(len(feat), np.nan)
    for v, sub in feat.groupby("device_variant", sort=True):
        if v not in obj:
            raise guards.LeakageError(
                f"no per-variant model for {p}/{v}; the frozen model never saw this variant")
        m = obj[v]
        X = build_X(sub, p, m.feature_set, linear=m.model_name in LINEAR_MODELS,
                    pooled=False, keep=m.columns)
        guards.assert_feature_matrix_clean(X, name=f"predict/{p}/{v}")
        yhat[sub.index.to_numpy()] = (sub[f"{p}_24h"].to_numpy(float)
                                      + m.estimator.predict(X.to_numpy(float)))
    if np.isnan(yhat).any():
        raise guards.DataQualityError(f"{p}: {int(np.isnan(yhat).sum())} rows left unpredicted")
    return yhat
