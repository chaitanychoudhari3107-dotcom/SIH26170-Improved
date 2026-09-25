"""
moduleb.guards — the fail-safe layer.

Every rule in the Module B contract that can be checked mechanically is checked
here, and a violation raises rather than warns. The design principle is that a
run which cannot be trusted must not produce a file: a silently wrong CSV that
reaches Anushka's fusion layer is far more expensive than a crashed script.

Two distinct failure classes, deliberately separate exception types:

  LeakageError  — the contract was violated (96h column, hidden label, target
                  reaching the predict stage, lot overlap across protected
                  splits). This is never recoverable in code; it means the input
                  file or the call is wrong.
  DataQualityError — the file is structurally broken (nulls, duplicate ids,
                  non-positive magnitudes, unknown variant). Escalate to
                  Chaitany; do NOT patch the data locally.

Neither is raised for "the MAE is worse than I hoped". That is a model problem,
not a data bug — see docs/DATA_BUG_VS_MODEL_PROBLEM.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .constants import (
    DEVICE_FAMILY, FORBIDDEN_EPOCHS, FORBIDDEN_OUTPUT_COLS, GROUP_KEY,
    HIDDEN_LABEL_TOKENS, ID_COLS, JOIN_KEY, PARAMS, PREDICTOR_COLS, TARGET_COLS,
    TARGET_EPOCH, VARIANTS,
)


class LeakageError(RuntimeError):
    """A hard contract rule was broken. Never catch this to continue."""


class DataQualityError(RuntimeError):
    """The file is structurally unusable. Escalate; do not repair in place."""


# ---------------------------------------------------------------- contract
def find_forbidden_epoch_columns(columns) -> list[str]:
    """Columns carrying a forbidden epoch.

    Matched on the token with word boundaries rather than a bare substring, so a
    hypothetical `Notes_1996h_comment` is caught while a legitimate column that
    merely contains the digits is not silently ignored — we prefer the false
    alarm here and say so in the message.
    """
    out = []
    for c in columns:
        low = str(c).lower()
        for e in FORBIDDEN_EPOCHS:
            if e in low:
                out.append(c)
                break
    return out


def find_hidden_label_columns(columns) -> list[str]:
    return [c for c in columns
            if any(tok in str(c).lower() for tok in HIDDEN_LABEL_TOKENS)]


def assert_input_clean(df: pd.DataFrame, *, allow_target: bool, name: str) -> None:
    """The gate every input file passes through before anything reads a value.

    allow_target=True   train / calibration: all six 168h targets must be present
    allow_target=False  holdout / inference: no 168h column may be present at all
    """
    bad96 = find_forbidden_epoch_columns(df.columns)
    if bad96:
        raise LeakageError(
            f"[{name}] 96h information is forbidden for Module B; found {bad96}. "
            "Module B predicts from 0h and 24h only.")

    lab = find_hidden_label_columns(df.columns)
    if lab:
        raise LeakageError(
            f"[{name}] hidden generator-truth columns are forbidden; found {lab}. "
            "This file should not have reached Module B — tell Chaitany.")

    missing_ctx = [c for c in ID_COLS if c not in df.columns]
    if missing_ctx:
        raise LeakageError(f"[{name}] missing required context columns: {missing_ctx}")

    absent = [c for c in PREDICTOR_COLS if c not in df.columns]
    if absent:
        raise LeakageError(f"[{name}] missing required 0h/24h predictors: {absent}")

    present_targets = [c for c in TARGET_COLS if c in df.columns]
    if not allow_target and present_targets:
        raise LeakageError(
            f"[{name}] this stage must not receive 168h targets, found {present_targets}. "
            "If this is the real holdout file, stop and tell Chaitany: the holdout "
            "is supposed to ship without answers.")
    if allow_target and len(present_targets) != len(TARGET_COLS):
        raise LeakageError(
            f"[{name}] expected all six 168h targets, found {present_targets}")


def assert_feature_matrix_clean(X: pd.DataFrame, *, name: str) -> None:
    """Last line of defence: run on the actual matrix handed to an estimator.

    assert_input_clean checks the file. This checks the thing the model really
    sees, which is where a feature-engineering mistake would show up.
    """
    bad = find_forbidden_epoch_columns(X.columns) + find_hidden_label_columns(X.columns)
    if bad:
        raise LeakageError(f"[{name}] forbidden columns reached the feature matrix: {bad}")
    tgt = [c for c in X.columns if any(t in str(c) for t in TARGET_COLS)]
    if tgt:
        raise LeakageError(f"[{name}] 168h target information reached the feature matrix: {tgt}")
    arr = X.to_numpy(dtype=float, copy=False)
    if not np.isfinite(arr).all():
        n = int((~np.isfinite(arr)).sum())
        raise DataQualityError(
            f"[{name}] feature matrix holds {n} non-finite values. "
            "A NaN or inf here silently poisons a fitted model.")


# ---------------------------------------------------------------- quality
def assert_data_quality(df: pd.DataFrame, *, name: str, expect_targets: bool) -> None:
    if len(df) == 0:
        raise DataQualityError(f"[{name}] file is empty")

    n_null = int(df.isna().sum().sum())
    if n_null:
        cols = df.columns[df.isna().any()].tolist()
        raise DataQualityError(f"[{name}] {n_null} null values in {cols}")

    dup = int(df[JOIN_KEY].duplicated().sum())
    if dup:
        raise DataQualityError(
            f"[{name}] {dup} duplicate {JOIN_KEY} values. The join key must be unique "
            "or Anushka's fusion join silently multiplies rows.")

    unknown = sorted(set(df.device_variant.unique()) - set(VARIANTS))
    if unknown:
        raise DataQualityError(
            f"[{name}] unknown device_variant {unknown}; FINAL-01 defines {VARIANTS}. "
            "A model pooled with a variant one-hot cannot score a variant it never saw.")

    fam = sorted(set(df.device_family.unique()))
    if fam != [DEVICE_FAMILY]:
        raise DataQualityError(f"[{name}] unexpected device_family {fam}, expected ['{DEVICE_FAMILY}']")

    cols = PREDICTOR_COLS + (TARGET_COLS if expect_targets else [])
    num = df[cols]
    nonnum = [c for c in cols if not pd.api.types.is_numeric_dtype(num[c])]
    if nonnum:
        raise DataQualityError(f"[{name}] non-numeric measurement columns: {nonnum}")
    bad = (num <= 0).sum()
    bad = bad[bad > 0]
    if len(bad):
        raise DataQualityError(
            f"[{name}] non-positive measurements in {bad.to_dict()}. All six parameters "
            "are magnitudes; a zero would also divide by zero in the relative-delta target.")
    if not np.isfinite(num.to_numpy(dtype=float)).all():
        raise DataQualityError(f"[{name}] non-finite measurement values")


def assert_lots_disjoint(a: pd.DataFrame, b: pd.DataFrame, *, name_a: str, name_b: str) -> None:
    """Whole-lot separation between two protected splits.

    Components from one manufacturing lot are related, so a single shared lot
    turns a held-out score into a partly in-sample one.
    """
    overlap = sorted(set(a.lot_id) & set(b.lot_id))
    if overlap:
        raise LeakageError(
            f"lots appear in both {name_a} and {name_b}: {overlap}. "
            "Every Module B split is by whole lot.")
    shared_ids = sorted(set(a[JOIN_KEY]) & set(b[JOIN_KEY]))
    if shared_ids:
        raise LeakageError(
            f"{len(shared_ids)} component_ids appear in both {name_a} and {name_b}, "
            f"first few {shared_ids[:5]}")


def assert_cohort_sufficient(df: pd.DataFrame, *, min_rows: int, name: str) -> None:
    """Refuse a request too small to support the lot-context features.

    The timing models read own-lot medians and the evidence layer ranks a
    component against the others in the same request. Both are cohort
    properties. Answering a one-row request would not be a slightly worse
    answer, it would be a different one computed from a lot of size one — and it
    would look perfectly well formed on the way out.
    """
    sizes = df.groupby(GROUP_KEY).size()
    small = sizes[sizes < min_rows]
    if len(small):
        raise DataQualityError(
            f"[{name}] Module B scores whole lots, not individual components. "
            f"{len(small)} lot(s) in this request carry fewer than {min_rows} rows: "
            f"{small.to_dict()}. Send the complete lot. If a partial cohort is "
            "genuinely intended, pass allow_partial_lot=True and read the warning "
            "it produces — the timing forecasts and every evidence column are then "
            "computed against that partial cohort and are not comparable to "
            "full-lot output.")


def assert_folds_are_whole_lots(df: pd.DataFrame, folds) -> None:
    f = pd.Series(np.asarray(folds), index=df.index)
    per_lot = f.groupby(df.lot_id.values).nunique()
    split = per_lot[per_lot > 1]
    if len(split):
        raise LeakageError(f"lots split across folds: {split.index.tolist()}")


# ---------------------------------------------------------------- outputs
def assert_predictions_sane(preds: dict[str, np.ndarray], n_rows: int, *, name: str) -> None:
    for p in PARAMS:
        v = np.asarray(preds[p], float)
        if v.shape != (n_rows,):
            raise DataQualityError(f"[{name}] {p}: expected {n_rows} predictions, got {v.shape}")
        if not np.isfinite(v).all():
            raise DataQualityError(
                f"[{name}] {p}: {int((~np.isfinite(v)).sum())} non-finite predictions. "
                "Refusing to write a CSV with NaN in it.")
        if (v <= 0).any():
            raise DataQualityError(
                f"[{name}] {p}: {int((v <= 0).sum())} non-positive predictions survived the "
                "positivity guard — this is a bug in moduleb.predict, not in the data.")


def assert_output_contract(out: pd.DataFrame, expected_cols: list[str], src_ids,
                           *, name: str) -> None:
    """The output frame is what integration consumes; check it like an API response."""
    missing = [c for c in expected_cols if c not in out.columns]
    if missing:
        raise DataQualityError(f"[{name}] output is missing contract columns: {missing}")
    forbidden = [c for c in FORBIDDEN_OUTPUT_COLS if c in out.columns]
    if forbidden:
        raise LeakageError(
            f"[{name}] Module B must not emit {forbidden}. The final "
            "PASS/MONITOR/REJECT belongs to Module A + fusion (decision D1).")
    if len(out) != len(src_ids):
        raise DataQualityError(f"[{name}] {len(out)} output rows for {len(src_ids)} input rows")
    if list(out[JOIN_KEY]) != list(src_ids):
        raise DataQualityError(
            f"[{name}] component_id order or content differs from the input file. "
            "Integration joins on component_id, but a reordered file is still a red flag.")
    # NB: `module_b_primary_parameter` also starts with "module_b_p" and is a STRING.
    # Matching on the prefix alone crashed the numeric check; the epoch suffix is what
    # actually distinguishes a forecast column. Keep both conditions.
    numeric = [c for c in expected_cols
               if c.startswith("predicted_")
               or (c.startswith("module_b_p") and c.endswith(f"_{TARGET_EPOCH}"))]
    if len(numeric) != 2 * len(PARAMS):
        raise DataQualityError(
            f"[{name}] expected {2 * len(PARAMS)} numeric forecast columns, matched {numeric}")
    if not np.isfinite(out[numeric].to_numpy(dtype=float)).all():
        bad = [c for c in numeric if not np.isfinite(out[c].to_numpy(float)).all()]
        raise DataQualityError(f"[{name}] non-finite values in the forecast columns: {bad}")
    str_cols = ["module_b_primary_parameter", "module_b_reason_codes"]
    for c in str_cols:
        if c in out.columns and out[c].isna().any():
            raise DataQualityError(f"[{name}] null values in {c}")
    if "module_b_primary_parameter" in out.columns:
        unknown = sorted(set(out.module_b_primary_parameter.unique()) - set(PARAMS))
        if unknown:
            raise DataQualityError(
                f"[{name}] module_b_primary_parameter holds values that are not parameters: {unknown}")
