"""
moduleb.reason_codes — the evidence layer, and the false-positive discipline.

This module is where Module B is most likely to do harm, so it is the most
conservative code in the package. A forecast that is 4% off is a number someone
can reason about. A reason code that fires on a third of the fleet is worse than
useless: it trains the fusion layer and the operator to ignore it, and the one
component that actually mattered goes out with the crowd.

Three rules, applied to every flag here:

1. REFERENCE CLASS. A component's primary parameter is BY CONSTRUCTION the one
   with its highest drift z. Ranking those primaries against the whole variant
   would flag roughly a third of them purely by that construction. So the drift
   flag uses an absolute z threshold, and envelope width is ranked only among the
   components that this same parameter drives.
2. NO INVENTED LIMITS. The limit-based codes use the static limit itself as the
   threshold. Seven of the eighteen variant x parameter cells carry no
   static_spec_max, and those cells never fire — no default, no proxy, no
   "conservative" stand-in. A fabricated limit manufactures false positives that
   look authoritative.
3. QUALIFIERS DO NOT STAND ALONE. B_NO_EARLY_SIGNAL is true of ~40% of
   components. On its own that is a fact about the dataset, not evidence about a
   part. It is emitted only where a risk flag already fired, where it reads as
   "this component is flagged, and the forecast behind the flag has no early
   evidence under it" — which is exactly the caveat fusion needs.

`build_reason_codes` returns the joined strings AND the boolean firing matrix,
so scripts/07_reason_code_audit.py can measure every rate rather than trusting
this docstring.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config
from .constants import PARAMS

CODE_NAMES = [
    "B_HIGH_FORECAST_DRIFT",
    "B_WIDE_ENVELOPE",
    "B_LOT_OUTLIER_24H",
    "B_FORECAST_EXCEEDS_LIMIT",
    "B_ENVELOPE_REACHES_LIMIT",
    "B_NO_EARLY_SIGNAL",
]
_MIN_RANKING_POP = 10   # below this, a within-group percentile is noise; skip the flag


def _robust_z(values: np.ndarray) -> np.ndarray:
    """Median/MAD z. A zero MAD returns zeros, not infinities: a parameter with
    no dispersion in its reference group cannot supply evidence about any one
    component, and dividing by zero would flag everything."""
    med = np.median(values)
    mad = 1.4826 * np.median(np.abs(values - med))
    if mad <= 0:
        return np.zeros_like(values)
    return (values - med) / mad


def predicted_relative_drift(feat: pd.DataFrame, preds: dict[str, np.ndarray]) -> pd.DataFrame:
    return pd.DataFrame({
        p: (np.asarray(preds[p], float) - feat[f"{p}_24h"].to_numpy(float))
           / feat[f"{p}_24h"].to_numpy(float)
        for p in PARAMS
    })


def drift_z_within_variant(feat: pd.DataFrame, reldrift: pd.DataFrame) -> pd.DataFrame:
    """Each parameter's predicted relative drift in robust z-units against the
    same variant. Scale-free, so uA and ns become comparable and no static limit
    is needed to pick a primary parameter."""
    feat = feat.reset_index(drop=True)
    zs = pd.DataFrame(0.0, index=range(len(feat)), columns=PARAMS)
    for _, idx in feat.groupby("device_variant", sort=True).groups.items():
        loc = np.asarray(idx, dtype=int)
        for p in PARAMS:
            zs.iloc[loc, zs.columns.get_loc(p)] = _robust_z(reldrift[p].to_numpy(float)[loc])
    return zs


def build_reason_codes(feat: pd.DataFrame, preds: dict[str, np.ndarray],
                       limits: pd.DataFrame,
                       env: dict[str, np.ndarray] | None = None
                       ) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """Returns (primary_parameter, reason_code_strings, firing_matrix)."""
    feat = feat.reset_index(drop=True)
    n = len(feat)
    reldrift = predicted_relative_drift(feat, preds)
    zs = drift_z_within_variant(feat, reldrift)

    primary = pd.Series(zs.idxmax(axis=1).to_numpy(), name="module_b_primary_parameter")
    zmax = zs.max(axis=1).to_numpy(float)

    fired = pd.DataFrame(False, index=range(n),
                         columns=[f"{c}:{p}" for c in CODE_NAMES for p in PARAMS])
    codes: list[list[str]] = [[] for _ in range(n)]

    def mark(code: str, p: str, rows: np.ndarray) -> None:
        rows = np.asarray(rows, dtype=int)
        if rows.size == 0:
            return
        fired.loc[rows, f"{code}:{p}"] = True
        for i in rows:
            codes[i].append(f"{code}:{p}")

    is_primary = {p: (primary.to_numpy() == p) for p in PARAMS}

    # ---- flags on the PRIMARY parameter only -----------------------------
    for p in PARAMS:
        prim = is_primary[p]
        if not prim.any():
            continue

        # absolute z threshold, not a percentile — see rule 1
        mark("B_HIGH_FORECAST_DRIFT", p,
             np.flatnonzero(prim & (zmax >= config.FLAG_HIGH_DRIFT_Z)))

        # envelope width, ranked only among the components this parameter drives
        if env is not None:
            width = np.asarray(env[p], float) - np.asarray(preds[p], float)
            for _, idx in feat.groupby("device_variant", sort=True).groups.items():
                loc = np.asarray(idx, dtype=int)
                sel = loc[prim[loc]]
                if len(sel) < _MIN_RANKING_POP:
                    continue
                cut = np.quantile(width[sel], config.FLAG_WIDE_ENVELOPE_PCTL)
                mark("B_WIDE_ENVELOPE", p, sel[width[sel] >= cut])

        # 24h reading against the component's OWN lot
        dev = feat[f"{p}_24h"].to_numpy(float) - feat[f"lotmed_{p}_24h"].to_numpy(float)
        for _, idx in feat.groupby("lot_id", sort=True).groups.items():
            loc = np.asarray(idx, dtype=int)
            z = np.abs(_robust_z(dev[loc]))
            mark("B_LOT_OUTLIER_24H", p, loc[(z >= config.FLAG_LOT_Z) & prim[loc]])

    # ---- limit flags, any parameter. The limit IS the threshold -----------
    for p in PARAMS:
        lim = feat.device_variant.map(limits[p]).to_numpy(float)
        has = ~np.isnan(lim)
        if not has.any():
            continue                       # no source-backed limit: never fires
        pred = np.asarray(preds[p], float)
        mark("B_FORECAST_EXCEEDS_LIMIT", p, np.flatnonzero(has & (pred >= lim)))
        if env is not None:
            up = np.asarray(env[p], float)
            mark("B_ENVELOPE_REACHES_LIMIT", p,
                 np.flatnonzero(has & (up >= lim) & (pred < lim)))

    # ---- confidence qualifier, applied last and never alone ---------------
    for p in PARAMS:
        prim = is_primary[p]
        x0 = feat[f"{p}_0h"].to_numpy(float)
        x24 = feat[f"{p}_24h"].to_numpy(float)
        early = np.abs((x24 - x0) / x0)
        quiet = prim & (early < config.NOISE_CV[p] * np.sqrt(2.0))
        rows = np.array([i for i in np.flatnonzero(quiet) if codes[i]], dtype=int)
        mark("B_NO_EARLY_SIGNAL", p, rows)

    joined = pd.Series(["|".join(c) for c in codes], name="module_b_reason_codes")
    return primary, joined, fired


def evidence_columns(feat: pd.DataFrame, preds: dict[str, np.ndarray],
                     limits: pd.DataFrame) -> pd.DataFrame:
    """The raw numbers behind the flags, four per parameter.

    Emitted so the fusion layer can apply its own thresholds instead of
    inheriting the ones in moduleb.config. `evidence_<p>_limit` is NaN wherever
    Device_Specs carries no static maximum, and NaN is the correct answer there —
    not zero, and not a guess.
    """
    feat = feat.reset_index(drop=True)
    out = pd.DataFrame(index=range(len(feat)))
    for p in PARAMS:
        lim = feat.device_variant.map(limits[p]).to_numpy(float)
        pred = np.asarray(preds[p], float)
        x24 = feat[f"{p}_24h"].to_numpy(float)
        lotmed = feat[f"lotmed_{p}_24h"].to_numpy(float)
        out[f"evidence_{p}_limit"] = lim
        with np.errstate(invalid="ignore", divide="ignore"):
            out[f"evidence_{p}_pred_frac_of_limit"] = pred / lim
        out[f"evidence_{p}_pred_rel_delta_from_24h"] = (pred - x24) / x24
        out[f"evidence_{p}_lot_rel_dev_24h"] = x24 / lotmed - 1.0
    return out


def firing_rates(fired: pd.DataFrame) -> pd.DataFrame:
    """Per-code firing rate, for the false-positive audit."""
    rows = []
    for col in fired.columns:
        code, p = col.split(":", 1)
        rows.append(dict(code=code, param=p, n_fired=int(fired[col].sum()),
                         rate=float(fired[col].mean())))
    df = pd.DataFrame(rows)
    # The ANY row is the fraction of COMPONENTS carrying this code for at least one
    # parameter — not the sum of the per-parameter counts, which double-counts a
    # component flagged on two parameters and can exceed 100%.
    tot = []
    for code in CODE_NAMES:
        cols = [c for c in fired.columns if c.startswith(f"{code}:")]
        any_row = fired[cols].any(axis=1) if cols else pd.Series(False, index=fired.index)
        tot.append(dict(code=code, param="ANY", n_fired=int(any_row.sum()),
                        rate=float(any_row.mean())))
    any_code = fired.any(axis=1)
    tot.append(dict(code="ANY_CODE", param="ANY", n_fired=int(any_code.sum()),
                    rate=float(any_code.mean())))
    out = pd.concat([df, pd.DataFrame(tot)], ignore_index=True)
    return out.sort_values(["code", "param"], ignore_index=True)
