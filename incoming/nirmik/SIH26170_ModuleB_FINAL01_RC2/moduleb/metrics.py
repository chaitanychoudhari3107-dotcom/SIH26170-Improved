"""
moduleb.metrics — the metric panel, and the per-lot paired test.

MAE is the official primary metric. Everything else is here because a single
pooled MAE hides the two things that actually decide whether Module B is
trustworthy: whether it is systematically optimistic, and whether it holds up on
lots it has never seen.

MAPE is deliberately absent. Input_Leakage_Current runs down to ~0.007 uA, so a
percentage error would be dominated by the smallest denominators and would
reward nothing useful. nMAE_pct normalises by the median instead, which is
stable and comparable across parameters without that pathology.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

METRIC_COLS = ["n", "MAE", "MedAE", "P90AE", "RMSE", "MeanSignedError",
               "UnderPredRate", "MacroLotMAE", "WorstLotMAE", "nMAE_pct"]


def metrics(y, yhat, lots) -> dict:
    y = np.asarray(y, float)
    yhat = np.asarray(yhat, float)
    if y.shape != yhat.shape:
        raise ValueError(f"shape mismatch {y.shape} vs {yhat.shape}")
    if len(y) == 0:
        raise ValueError("no rows to score")
    e = yhat - y
    a = np.abs(e)
    per_lot = pd.Series(a).groupby(np.asarray(lots)).mean()
    med_y = float(np.median(y))
    return dict(
        n=int(len(y)),
        MAE=float(a.mean()),                    # official primary metric
        MedAE=float(np.median(a)),              # typical case
        P90AE=float(np.quantile(a, 0.90)),      # tail
        RMSE=float(np.sqrt((e ** 2).mean())),   # large errors
        MeanSignedError=float(e.mean()),        # negative => systematically low
        UnderPredRate=float((e < 0).mean()),
        MacroLotMAE=float(per_lot.mean()),      # lot-weighted, not row-weighted
        WorstLotMAE=float(per_lot.max()),
        nMAE_pct=float(100 * a.mean() / med_y) if med_y > 0 else float("nan"),
    )


def per_lot_mae(y, yhat, lots) -> pd.Series:
    a = np.abs(np.asarray(yhat, float) - np.asarray(y, float))
    return pd.Series(a).groupby(np.asarray(lots)).mean().sort_index()


def paired_lot_test(y, yhat_a, yhat_b, lots) -> dict:
    """Is model A better than model B, lot by lot?

    Held-out lots are the independent unit here, not components: components in a
    lot share whatever that lot did, so treating 3,151 rows as 3,151 independent
    observations would overstate significance by roughly the lot size. With 42
    lots the honest sample size is 42.

    Returns the two-sided Wilcoxon signed-rank p-value over per-lot MAEs, the
    number of lots A wins, and the percentage MAE gain. Read all three: a 1%
    gain on 40 of 42 lots is real and uninteresting.
    """
    from scipy.stats import wilcoxon
    la = per_lot_mae(y, yhat_a, lots)
    lb = per_lot_mae(y, yhat_b, lots)
    common = la.index.intersection(lb.index)
    la, lb = la.loc[common], lb.loc[common]
    diff = (la - lb).to_numpy(float)
    n_lots = len(common)
    wins = int((diff < 0).sum())
    if n_lots < 3 or np.allclose(diff, 0):
        p = float("nan")
    else:
        try:
            p = float(wilcoxon(la.to_numpy(float), lb.to_numpy(float))[1])
        except ValueError:
            p = float("nan")
    mean_b = float(lb.mean())
    # NB: mae_a / mae_b are MACRO-LOT means — the average of the per-lot MAEs,
    # which weights every lot equally. They are NOT the row-weighted pooled MAE
    # reported by metrics(); with unequal lot sizes the two differ slightly, and
    # quoting one as the other is the easiest way to publish a wrong number.
    return dict(
        n_lots=n_lots,
        lots_won=wins,
        lots_won_frac=wins / n_lots if n_lots else float("nan"),
        macro_lot_mae_a=float(la.mean()),
        macro_lot_mae_b=mean_b,
        mae_a=float(la.mean()),
        mae_b=mean_b,
        gain_pct=float(100 * (mean_b - float(la.mean())) / mean_b) if mean_b > 0 else float("nan"),
        wilcoxon_p=p,
    )


def verdict(test: dict, tie_pct: float, alpha: float) -> str:
    """Turn a paired test into one of three words, using the team's own rule:
    differences under `tie_pct` are ties whatever the rank or the p-value."""
    if not np.isfinite(test["gain_pct"]):
        return "UNDETERMINED"
    if abs(test["gain_pct"]) < tie_pct:
        return "TIE"
    if test["gain_pct"] > 0 and np.isfinite(test["wilcoxon_p"]) and test["wilcoxon_p"] <= alpha:
        return "BETTER"
    if test["gain_pct"] < 0 and np.isfinite(test["wilcoxon_p"]) and test["wilcoxon_p"] <= alpha:
        return "WORSE"
    return "TIE"
