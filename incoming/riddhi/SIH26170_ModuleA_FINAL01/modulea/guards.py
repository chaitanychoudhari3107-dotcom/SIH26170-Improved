"""Every condition the code refuses to proceed through.

The principle throughout: a guard raises. It does not warn, it does not coerce,
and it never turns an invalid input into healthy-looking evidence. Where a
documented fallback exists it is named in the error or recorded on the artifact.

These are the conditions the handoff asks to be audited explicitly — zero/near-zero
MAD, small or incomplete lots, contaminated lot references, unknown variants,
duplicate ids, missing or non-finite values, joins, index alignment, and
parameter-name mismatches — plus the ones the intake audit added.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from modulea.constants import (EPOCHS, IDENTIFIERS, PARAMETERS, future_columns,
                               observed_columns)

MIN_LOT_SIZE = 30


class GuardError(ValueError):
    """A precondition failed. The caller must fix the input, not the guard."""


def require_schema(frame: pd.DataFrame, epoch: int, name: str) -> None:
    required = set(IDENTIFIERS) | set(observed_columns(epoch))
    missing = required - set(frame.columns)
    if missing:
        raise GuardError(f"{name}: missing required columns {sorted(missing)}")
    for column in IDENTIFIERS:
        values = frame[column]
        if values.isna().any() or values.astype(str).str.strip().eq("").any():
            raise GuardError(f"{name}: blank or null {column}")


def require_unique_ids(frame: pd.DataFrame, name: str) -> None:
    duplicated = frame.loc[frame["component_id"].duplicated(), "component_id"]
    if len(duplicated):
        raise GuardError(f"{name}: duplicate component_id {duplicated.head().tolist()}")


def require_measurements(frame: pd.DataFrame, epoch: int, name: str) -> None:
    """Finite and strictly positive. These are currents and times; zero or negative
    is an instrument or export fault, and a zero 0 h reading would also make the
    percentage-change feature undefined."""
    columns = observed_columns(epoch)
    values = frame[columns].apply(pd.to_numeric, errors="coerce")
    if values.isna().any().any():
        bad = values.columns[values.isna().any()].tolist()
        raise GuardError(f"{name}: null or non-numeric measurements in {bad}")
    array = values.to_numpy(float)
    if not np.isfinite(array).all():
        raise GuardError(f"{name}: non-finite measurements")
    if (array <= 0).any():
        where = values.columns[(values <= 0).any()].tolist()
        raise GuardError(f"{name}: non-positive measurements in {where}")


def forbid_future_columns(frame: pd.DataFrame, epoch: int, name: str) -> None:
    """The scoring path must not even be able to see a later epoch."""
    present = sorted(set(future_columns(epoch)) & set(frame.columns))
    if present:
        raise GuardError(
            f"{name}: columns later than {epoch} h reached the scoring frame: {present}. "
            "Drop them before scoring rather than trusting the model not to use them.")


def require_lot_variant_purity(frame: pd.DataFrame, name: str) -> None:
    mixed = frame.groupby("lot_id")["device_variant"].nunique()
    offenders = mixed[mixed > 1].index.tolist()
    if offenders:
        raise GuardError(
            f"{name}: lots contain more than one device_variant: {offenders[:5]}. "
            "The lot-relative reference assumes one variant per lot.")


def require_complete_lots(frame: pd.DataFrame, expected: dict[str, int], name: str) -> None:
    """Completeness is proved against external lot metadata, never against a count
    taken from the arriving batch itself — a half-delivered lot counts itself as
    whole. This is the check that licenses same-lot statistics at inference."""
    if not expected:
        raise GuardError(
            f"{name}: no external lot sizes supplied. Same-lot statistics are only "
            "valid on a complete lot, and completeness cannot be inferred from the "
            "batch being validated.")
    observed = frame.groupby("lot_id").size().to_dict()
    unknown = sorted(set(observed) - set(expected))
    if unknown:
        raise GuardError(f"{name}: lots absent from the manifest: {unknown[:5]}")
    partial = {lot: (n, expected[lot]) for lot, n in observed.items() if n != expected[lot]}
    if partial:
        shown = list(partial.items())[:5]
        raise GuardError(f"{name}: incomplete lots (observed, expected) {shown}")
    small = [lot for lot, n in observed.items() if n < MIN_LOT_SIZE]
    if small:
        raise GuardError(
            f"{name}: lots below {MIN_LOT_SIZE} components {small[:5]}; a lot-relative "
            "median and MAD are not meaningful on so few parts.")


def require_known_variants(frame: pd.DataFrame, known: list[str], name: str) -> None:
    unknown = sorted(set(frame["device_variant"]) - set(known))
    if unknown:
        raise GuardError(
            f"{name}: unknown device_variant {unknown}; there is no fitted reference "
            "and substituting another variant's would be a guess.")


def require_no_label_columns(frame: pd.DataFrame, name: str) -> None:
    """Nothing derived from the generator may reach a scoring path."""
    leaked = sorted({"is_anomalous", "defect_behavior", "severity", "onset_epoch",
                     "primary_parameter", "affected_parameters", "defect_domain",
                     "static_fail_target", "static_spec_pass_168h", "healthy_edge"}
                    & set(frame.columns))
    if leaked:
        raise GuardError(f"{name}: ground-truth columns reached the scoring frame: {leaked}")


def require_disjoint(frames: dict[str, pd.DataFrame], key: str = "component_id") -> None:
    names = list(frames)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            shared = set(frames[a][key]) & set(frames[b][key])
            if shared:
                raise GuardError(
                    f"{a} and {b} share {len(shared)} {key} values, e.g. "
                    f"{sorted(shared)[:3]}")


def require_lot_disjoint(frames: dict[str, pd.DataFrame]) -> None:
    require_disjoint(frames, key="lot_id")


def validate_scoring_frame(frame: pd.DataFrame, epoch: int, name: str,
                           known_variants: list[str],
                           expected_lot_sizes: dict[str, int]) -> pd.DataFrame:
    """The full gate a batch passes before it is scored. Returns a clean copy with
    future columns dropped, so the model cannot read them even by accident."""
    frame = frame.reset_index(drop=True)
    require_schema(frame, epoch, name)
    require_unique_ids(frame, name)
    require_measurements(frame, epoch, name)
    require_lot_variant_purity(frame, name)
    require_complete_lots(frame, expected_lot_sizes, name)
    require_known_variants(frame, known_variants, name)
    kept = [c for c in frame.columns
            if c in IDENTIFIERS or c in set(observed_columns(epoch))]
    clean = frame[kept].copy()
    require_no_label_columns(clean, name)
    forbid_future_columns(clean, epoch, name)
    return clean
