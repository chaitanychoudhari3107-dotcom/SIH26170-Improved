"""The false-positive tests. These are the ones that matter most: a reason code
that fires when it should not is worse than no reason code at all."""
import numpy as np
import pandas as pd
import pytest

from moduleb import config, reason_codes
from moduleb.constants import PARAMS


def _flat_preds(feat, factor=1.0):
    return {p: feat[f"{p}_24h"].to_numpy(float) * factor for p in PARAMS}


def test_no_limit_means_no_limit_flag(synth_feat, specs):
    """The seven variant x parameter cells with no static_spec_max must never
    raise a limit-based code, however extreme the forecast."""
    _, lim = specs
    huge = {p: feat_col * 1e6 for p, feat_col in
            ((p, synth_feat[f"{p}_24h"].to_numpy(float)) for p in PARAMS)}
    _, _, fired = reason_codes.build_reason_codes(synth_feat, huge, lim, env=huge)
    for p in PARAMS:
        no_limit_variants = lim.index[lim[p].isna()].tolist()
        if not no_limit_variants:
            continue
        sel = synth_feat.device_variant.isin(no_limit_variants).to_numpy()
        for code in ("B_FORECAST_EXCEEDS_LIMIT", "B_ENVELOPE_REACHES_LIMIT"):
            assert not fired.loc[sel, f"{code}:{p}"].any(), \
                f"{code}:{p} fired for a variant with no static limit"


def test_limits_are_never_imputed(specs):
    _, lim = specs
    assert lim.isna().to_numpy().sum() == 7, \
        "the seven empty Device_Specs limit cells must stay NaN, not be filled"


def test_no_early_signal_never_fires_alone(synth_feat, specs):
    _, lim = specs
    preds = _flat_preds(synth_feat, 1.02)
    _, codes, fired = reason_codes.build_reason_codes(synth_feat, preds, lim, env=None)
    quiet_only = fired[[c for c in fired.columns if c.startswith("B_NO_EARLY_SIGNAL")]].any(axis=1)
    other = fired[[c for c in fired.columns if not c.startswith("B_NO_EARLY_SIGNAL")]].any(axis=1)
    assert not (quiet_only & ~other).any(), \
        "B_NO_EARLY_SIGNAL fired on a component carrying no risk flag"


def test_flags_are_sparse(synth_feat, specs):
    """Sparsity of the data-independent codes. The limit-based codes depend on how
    much headroom FINAL-01 actually leaves, so their rates are audited against the
    real file in scripts/07_reason_code_audit.py, not against this fixture."""
    _, lim = specs
    preds = _flat_preds(synth_feat, 1.03)
    _, _, fired = reason_codes.build_reason_codes(synth_feat, preds, lim, env=None)
    rates = reason_codes.firing_rates(fired)
    per_code = rates[rates.param == "ANY"].set_index("code").rate
    # B_NO_EARLY_SIGNAL is excluded here on purpose: it is a qualifier whose rate is
    # conditional on a risk flag already firing, and this fixture's arbitrary values
    # trip the limit codes constantly. Its "never alone" property is tested above.
    for code in ("B_HIGH_FORECAST_DRIFT", "B_LOT_OUTLIER_24H"):
        assert per_code[code] <= config.MAX_FLAG_FIRING_RATE, \
            f"{code} fires on {per_code[code]:.1%} of components; that is not evidence"


def test_any_rate_never_exceeds_one(synth_feat, specs):
    """Regression test: the ANY row once summed per-parameter counts and reported
    133% of components flagged."""
    _, lim = specs
    preds = _flat_preds(synth_feat, 1.03)
    _, _, fired = reason_codes.build_reason_codes(synth_feat, preds, lim, env=None)
    rates = reason_codes.firing_rates(fired)
    assert (rates.rate <= 1.0).all()
    assert (rates.rate >= 0.0).all()


def test_primary_parameter_is_scale_free(synth_feat, specs):
    """Multiplying one parameter's UNITS must not make it the primary parameter.
    The z is computed on relative drift, so a constant rescale is invisible."""
    _, lim = specs
    preds = {p: synth_feat[f"{p}_24h"].to_numpy(float) * (1.0 + 0.01 * i)
             for i, p in enumerate(PARAMS)}
    primary_a, _, _ = reason_codes.build_reason_codes(synth_feat, preds, lim)
    scaled_feat = synth_feat.copy()
    for e in ("0h", "24h"):
        scaled_feat[f"IDDQ_{e}"] = scaled_feat[f"IDDQ_{e}"] * 1000.0
    scaled_feat["lotmed_IDDQ_0h"] *= 1000.0
    scaled_feat["lotmed_IDDQ_24h"] *= 1000.0
    preds_b = dict(preds)
    preds_b["IDDQ"] = preds["IDDQ"] * 1000.0
    primary_b, _, _ = reason_codes.build_reason_codes(scaled_feat, preds_b, lim)
    assert (primary_a.to_numpy() == primary_b.to_numpy()).all()


def test_zero_dispersion_group_does_not_flag_everything(synth_feat, specs):
    """A reference group with no spread has a zero MAD. Dividing by it would make
    every z infinite and flag the whole group."""
    _, lim = specs
    preds = {p: synth_feat[f"{p}_24h"].to_numpy(float) * 1.05 for p in PARAMS}
    _, _, fired = reason_codes.build_reason_codes(synth_feat, preds, lim, env=None)
    rate = fired[[c for c in fired.columns if c.startswith("B_HIGH_FORECAST_DRIFT")]].any(axis=1).mean()
    assert rate < 0.5, f"constant drift flagged {rate:.1%} of components"


def test_robust_z_of_constant_is_zero():
    z = reason_codes._robust_z(np.full(50, 3.7))
    assert np.allclose(z, 0.0)


def test_evidence_limit_column_is_nan_where_no_limit(synth_feat, specs):
    _, lim = specs
    preds = _flat_preds(synth_feat)
    ev = reason_codes.evidence_columns(synth_feat, preds, lim)
    for p in PARAMS:
        for v in lim.index[lim[p].isna()]:
            sel = (synth_feat.device_variant == v).to_numpy()
            assert ev.loc[sel, f"evidence_{p}_limit"].isna().all()
            assert ev.loc[sel, f"evidence_{p}_pred_frac_of_limit"].isna().all()
