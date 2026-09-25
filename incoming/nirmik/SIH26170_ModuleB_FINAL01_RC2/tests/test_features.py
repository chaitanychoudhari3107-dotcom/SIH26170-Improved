"""Feature purity, fold integrity, and the collinearity trap."""
import numpy as np
import pandas as pd
import pytest

from moduleb import featureset, guards
from moduleb.constants import PARAMS, PREDICTOR_EPOCHS
from moduleb.features import add_features, make_folds


def test_no_derived_feature_reads_a_target(synth, specs):
    """Perturb every 168h column wildly; the derived features must not move."""
    base, _ = specs
    a = add_features(synth, base)
    shuffled = synth.copy()
    for p in PARAMS:
        shuffled[f"{p}_168h"] = shuffled[f"{p}_168h"].to_numpy()[::-1] * 3.0
    b = add_features(shuffled, base)
    derived = [c for c in a.columns
               if c.startswith(("lotmed_", "spec_", "lotdrift_", "reldelta_", "reldev_"))]
    assert derived, "no derived columns produced"
    pd.testing.assert_frame_equal(a[derived], b[derived])


def test_lot_features_use_only_the_components_own_lot(synth, specs):
    """Change one lot's measurements; no other lot's features may move."""
    base, _ = specs
    a = add_features(synth, base)
    tampered = synth.copy()
    sel = tampered.lot_id == "CMOS_A_LOT00"
    for p in PARAMS:
        for e in PREDICTOR_EPOCHS:
            tampered.loc[sel, f"{p}_{e}"] *= 1.5
    b = add_features(tampered, base)
    keep = ~sel.to_numpy()
    derived = [c for c in a.columns if c.startswith(("lotmed_", "lotdrift_", "reldelta_", "reldev_"))]
    pd.testing.assert_frame_equal(a.loc[keep, derived].reset_index(drop=True),
                                  b.loc[keep, derived].reset_index(drop=True))


def test_folds_are_whole_lots_and_deterministic(synth, specs):
    base, _ = specs
    f = add_features(synth, base)
    a = make_folds(f, 5)
    b = make_folds(f.sample(frac=1, random_state=3).reset_index(drop=True), 5)
    guards.assert_folds_are_whole_lots(f, a)
    # the map is by lot name, so reordering rows cannot change any lot's fold
    m1 = dict(zip(f.lot_id, a))
    m2 = dict(zip(f.sample(frac=1, random_state=3).reset_index(drop=True).lot_id, b))
    assert m1 == m2


def test_every_variant_appears_in_most_folds(synth, specs):
    base, _ = specs
    f = add_features(synth, base)
    f["fold"] = make_folds(f, 3)
    counts = f.groupby(["fold", "device_variant"]).size().unstack(fill_value=0)
    assert (counts > 0).all().all(), f"a fold is missing a variant:\n{counts}"


def test_linear_basis_is_full_rank(synth_feat):
    """The whole point of the linear/non-linear split: OLS must not receive a
    column that is an exact linear combination of the others."""
    for p in PARAMS:
        for kind in featureset.FEATURE_SETS:
            X = featureset.build_X(synth_feat, p, kind, linear=True, pooled=True)
            A = X.to_numpy(float)
            # the variant one-hot sums to 1, which is only collinear with an
            # intercept; the estimators centre the data, so drop one column
            A = A[:, :-1]
            assert np.linalg.matrix_rank(A) == A.shape[1], f"{p}/{kind} is rank deficient"


def test_tree_basis_includes_the_redundant_forms(synth_feat):
    X = featureset.build_X(synth_feat, "IDDQ", "own", linear=False, pooled=True)
    assert "reldelta_IDDQ" in X.columns
    Xl = featureset.build_X(synth_feat, "IDDQ", "own", linear=True, pooled=True)
    assert "reldelta_IDDQ" not in Xl.columns


def test_predict_time_missing_column_raises_not_zero_fills(synth_feat):
    X = featureset.build_X(synth_feat, "IDDQ", "own", linear=True, pooled=True)
    cols = list(X.columns)
    trimmed = synth_feat.drop(columns=["IDDQ_24h"])
    with pytest.raises(guards.LeakageError):
        featureset.build_X(trimmed, "IDDQ", "own", linear=True, pooled=True, keep=cols)


def test_single_variant_batch_gets_zero_one_hots(synth_feat):
    X = featureset.build_X(synth_feat, "IDDQ", "own", linear=True, pooled=True)
    one = synth_feat[synth_feat.device_variant == "CMOS_B"]
    Xo = featureset.build_X(one, "IDDQ", "own", linear=True, pooled=True, keep=list(X.columns))
    assert list(Xo.columns) == list(X.columns)
    assert (Xo["var_CMOS_A"] == 0).all() and (Xo["var_CMOS_B"] == 1).all()
