"""
moduleb.contract — assemble and validate the file integration consumes.

The output frame is an API response in CSV clothing. Anushka's fusion layer
joins it on component_id and reads fixed column names, so shape errors here are
expensive and silent. Every frame this module returns has been through
guards.assert_output_contract before it leaves.

There is deliberately no `module_b_disposition` column. Per decision D1
(15 Sep 2026) the final PASS / MONITOR / REJECT belongs to Module A + fusion.
It is not emitted as NOT_SET either: an always-null column invites someone to
write a fusion rule against a field Module B has no authority over.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, guards, reason_codes
from .constants import JOIN_KEY, PARAMS, TARGET_EPOCH, contract_columns

TAU_PCT = int(round(config.ENVELOPE_TAU * 100))
CONTRACT_COLS = contract_columns(TAU_PCT)


def build_output(feat: pd.DataFrame, preds: dict[str, np.ndarray],
                 limits: pd.DataFrame, env: dict[str, np.ndarray] | None = None,
                 *, with_evidence: bool = True) -> pd.DataFrame:
    """The final Module B frame: contract columns first, evidence columns after.

    Integration reads the contract columns by name; the evidence columns are
    additive and a consumer that ignores them is unaffected.
    """
    feat = feat.reset_index(drop=True)
    guards.assert_predictions_sane(preds, len(feat), name="build_output")

    out = pd.DataFrame({JOIN_KEY: feat[JOIN_KEY].to_numpy()})
    for p in PARAMS:
        out[f"predicted_{p}_{TARGET_EPOCH}"] = np.asarray(preds[p], float)

    if env is not None:
        for p in PARAMS:
            up = np.asarray(env[p], float)
            if not np.isfinite(up).all():
                raise guards.DataQualityError(f"non-finite envelope values for {p}")
            if (up < np.asarray(preds[p], float) - 1e-12).any():
                raise guards.DataQualityError(
                    f"{p}: envelope below the point forecast. moduleb.predict is supposed to "
                    "have clipped this already, so reaching here is a bug.")
            out[f"module_b_p{TAU_PCT}_{p}_{TARGET_EPOCH}"] = up
    else:
        for p in PARAMS:
            out[f"module_b_p{TAU_PCT}_{p}_{TARGET_EPOCH}"] = np.nan

    primary, codes, fired = reason_codes.build_reason_codes(feat, preds, limits, env)
    out["module_b_primary_parameter"] = primary.to_numpy()
    out["module_b_reason_codes"] = codes.to_numpy()

    out = out[CONTRACT_COLS]
    if with_evidence:
        out = pd.concat([out, reason_codes.evidence_columns(feat, preds, limits)], axis=1)

    guards.assert_output_contract(out, CONTRACT_COLS, feat[JOIN_KEY].tolist(),
                                  name="module_b_output")
    out.attrs["firing_matrix"] = fired
    return out


def check_against_reference(out: pd.DataFrame, reference_cols: list[str]) -> list[str]:
    """Compare the produced columns with ModuleB_Output_Contract.csv's own header.

    Returns a list of human-readable discrepancies; empty means exact agreement
    on the contract columns. Extra evidence columns are not discrepancies.
    """
    problems = []
    for c in reference_cols:
        if c not in out.columns:
            problems.append(f"missing contract column {c!r}")
    produced = [c for c in out.columns if c in reference_cols]
    if produced != [c for c in reference_cols if c in out.columns]:
        problems.append("contract columns are present but out of order")
    return problems
