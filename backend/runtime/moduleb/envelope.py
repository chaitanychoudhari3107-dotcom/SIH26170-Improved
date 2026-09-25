"""
moduleb.envelope — the p95 upper bound, and an honest account of what it is.

Method: conformalised gradient-boosted quantile regression (CQR, Romano,
Patterson & Candes 2019). A GBR with the pinball loss at tau predicts an upper
quantile of the relative drift; a set of held-back LOTS then supplies conformity
scores, and the (n+1)-rank conformal quantile of those scores is added as an
offset. Holding back whole lots rather than random rows is what makes the
resulting coverage an out-of-lot statement rather than an in-sample one.

WHAT THIS IS NOT
----------------
It is not a safety screen and must never be described as one. On Candidate V1
the measured behaviour was: marginal coverage calibrated to within half a point
of nominal, but conditional coverage on the worst-drifting decile only ~0.38 at
tau=0.95. Raising tau to 0.99 reached ~0.62 at roughly triple the width. A part
sitting inside its p95 envelope is therefore NOT thereby safe. The envelope is
evidence for the fusion layer; the outlier judgement belongs to Module A.

scripts/08_envelope_coverage.py re-measures both numbers on FINAL-01 rather than
carrying the V1 figures forward on trust.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor

from . import config, guards
from .featureset import build_X


@dataclass
class EnvelopeModel:
    param: str
    feature_set: str
    columns: list[str]
    estimator: object
    offset: float           # conformal correction, in relative-delta units
    tau: float
    n_conformal: int
    conformal_lots: list[str]


def conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    """The ceil((n+1)(1-alpha))-th smallest score.

    The (n+1) is not a typo and not cosmetic: it is the rank the split-conformal
    construction calls for. What that construction buys here is NOT claimed as a
    finite-sample guarantee: the standard result needs exchangeable calibration
    and test units, and these units are whole lots with within-lot correlation,
    for which no cluster-conformal derivation has been produced for this score
    construction (review finding F2). The coverage this package reports is
    MEASURED on twelve unseen calibration lots, not derived. When the required
    rank exceeds n the correct answer is the maximum score, which is the honest
    statement that this many calibration points cannot certify that level.
    """
    s = np.sort(np.asarray(scores, float))
    n = len(s)
    if n == 0:
        raise ValueError("no conformity scores")
    k = int(np.ceil((n + 1) * (1 - alpha)))
    return float(s[-1] if k > n else s[k - 1])


def fit_envelope(train: pd.DataFrame, p: str, cfg: dict, *,
                 tau: float | None = None, seed: int | None = None) -> EnvelopeModel:
    tau = config.ENVELOPE_TAU if tau is None else tau
    seed = config.GLOBAL_SEED if seed is None else seed
    x24c, yc = f"{p}_24h", f"{p}_168h"
    if yc not in train.columns:
        raise guards.LeakageError(f"cannot fit an envelope for {p} without its 168h target")

    lots = sorted(train.lot_id.unique())
    if len(lots) <= config.ENVELOPE_CONF_LOTS:
        raise guards.DataQualityError(
            f"need more than {config.ENVELOPE_CONF_LOTS} lots to calibrate the envelope, "
            f"got {len(lots)}")
    conf = set(np.random.default_rng(seed).permutation(np.array(lots))[:config.ENVELOPE_CONF_LOTS])
    is_conf = train.lot_id.isin(conf).to_numpy()
    fit, cal = train.loc[~is_conf], train.loc[is_conf]

    X = build_X(fit, p, cfg["features"], linear=False, pooled=True)
    guards.assert_feature_matrix_clean(X, name=f"envelope-fit/{p}")
    y = ((fit[yc].to_numpy(float) - fit[x24c].to_numpy(float)) / fit[x24c].to_numpy(float))
    est = GradientBoostingRegressor(alpha=tau, **config.ENVELOPE_GBR).fit(X.to_numpy(float), y)

    Xc = build_X(cal, p, cfg["features"], linear=False, pooled=True, keep=list(X.columns))
    y_cal = ((cal[yc].to_numpy(float) - cal[x24c].to_numpy(float)) / cal[x24c].to_numpy(float))
    offset = conformal_quantile(y_cal - est.predict(Xc.to_numpy(float)), 1 - tau)

    return EnvelopeModel(p, cfg["features"], list(X.columns), est, offset, tau,
                         int(len(cal)), sorted(conf))


def predict_envelope(env: EnvelopeModel, feat: pd.DataFrame, p: str) -> np.ndarray:
    feat = feat.reset_index(drop=True)
    X = build_X(feat, p, env.feature_set, linear=False, pooled=True, keep=env.columns)
    guards.assert_feature_matrix_clean(X, name=f"envelope-predict/{p}")
    rel = env.estimator.predict(X.to_numpy(float)) + env.offset
    return feat[f"{p}_24h"].to_numpy(float) * (1.0 + rel)


def coverage_report(y_true: np.ndarray, upper: np.ndarray, point: np.ndarray,
                    x24: np.ndarray, *, tail_pctl: float = 0.90) -> dict:
    """Marginal coverage, tail coverage, and width.

    CORRECTED 19 Sep 2026 (review finding F3). The previous version ranked the
    "tail" by `y_true - point`, which is the FORECAST RESIDUAL — how badly the
    model under-predicted a component — and then described the result as
    coverage of the "worst-drifting decile". Those are two different
    populations. A component can be badly under-predicted while barely drifting,
    and a heavy drifter the model saw coming is not in the residual tail at all.
    Ranking by residual also makes the tail definition depend on the forecast,
    so a change of model silently changes which components are called the worst
    drifters.

    The tail is now ranked by OBSERVED relative drift from the 24 h reading,
    `(y_true - x24) / x24`, which is a property of the component and the truth
    alone. `x24` is required rather than optional: a silent fallback to the old
    behaviour is exactly how a corrected metric gets un-corrected.
    """
    y_true = np.asarray(y_true, float)
    upper = np.asarray(upper, float)
    point = np.asarray(point, float)
    x24 = np.asarray(x24, float)
    if not (len(y_true) == len(upper) == len(point) == len(x24)):
        raise ValueError("coverage_report: y_true, upper, point and x24 must be the same length")
    if (x24 <= 0).any():
        raise guards.DataQualityError("coverage_report: non-positive 24h readings")

    covered = y_true <= upper
    true_rel_drift = (y_true - x24) / x24          # the physical quantity, not a residual
    cut = np.quantile(true_rel_drift, tail_pctl)
    tail = true_rel_drift >= cut
    return dict(
        n=int(len(y_true)),
        marginal_coverage=float(covered.mean()),
        tail_coverage=float(covered[tail].mean()) if tail.any() else float("nan"),
        n_tail=int(tail.sum()),
        tail_cut_rel_drift=float(cut),
        tail_rank_basis="true_relative_drift_from_24h",
        mean_width=float(np.mean(upper - point)),
        median_width=float(np.median(upper - point)),
        mean_rel_width=float(np.mean((upper - point) / np.maximum(point, 1e-12))),
    )
