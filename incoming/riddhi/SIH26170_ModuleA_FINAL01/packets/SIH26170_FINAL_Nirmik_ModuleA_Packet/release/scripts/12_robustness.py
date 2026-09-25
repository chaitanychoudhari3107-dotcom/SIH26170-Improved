"""Stage 12 — perturb the input and see what actually happens.

Every claim in the integration note about "Module A will refuse X" or "Module A is
invariant to Y" is measured here. A property nobody has perturbed is a property
nobody knows.

Two kinds of check:

  INVARIANCE  the output must not change   (row order, column order, id relabelling)
  REFUSAL     the input must be rejected   (partial lot, unknown variant, bad value)

and one that is neither — SENSITIVITY, where the output is *expected* to change and
the question is by how much.

Nothing here touches the fitted model. It loads the frozen artifact and pokes it.
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from _common import MODELS, RESULTS, release_arg
from modulea.constants import PARAMETERS
from modulea.dataio import Release
from modulea.freeze import load

RESULT_COLUMNS = ["component_id", "module_a_score", "module_a_disposition",
                  "module_a_evidence_tier"]


def _scored(model, frame, epoch=168):
    return model.predict(frame, epoch).sort_values("component_id").reset_index(drop=True)


def _same(a: pd.DataFrame, b: pd.DataFrame) -> tuple[bool, float]:
    """Identical on the columns anyone downstream consumes?"""
    if list(a["component_id"]) != list(b["component_id"]):
        return False, float("nan")
    drift = float(np.max(np.abs(a["module_a_score"].to_numpy()
                                - b["module_a_score"].to_numpy())))
    same_disposition = bool((a["module_a_disposition"] == b["module_a_disposition"]).all())
    same_tier = bool((a["module_a_evidence_tier"] == b["module_a_evidence_tier"]).all())
    return (drift == 0.0 and same_disposition and same_tier), drift


def main() -> None:
    parser = release_arg(argparse.ArgumentParser())
    args = parser.parse_args()
    release = Release(args.release)
    model, _ = load(MODELS / "module_a_final01.joblib")
    holdout = release.split("holdout")
    baseline = _scored(model, holdout)
    rows = []

    def invariance(name, frame, note=""):
        try:
            same, drift = _same(baseline, _scored(model, frame))
            rows.append({"kind": "INVARIANCE", "case": name,
                         "status": "PASS" if same else "FAIL",
                         "max_score_drift": drift, "detail": note})
        except Exception as exc:
            rows.append({"kind": "INVARIANCE", "case": name, "status": "FAIL",
                         "max_score_drift": float("nan"),
                         "detail": f"raised instead of scoring: {exc}"})

    def refusal(name, frame, note=""):
        try:
            _scored(model, frame)
            rows.append({"kind": "REFUSAL", "case": name, "status": "FAIL",
                         "max_score_drift": float("nan"),
                         "detail": "scored an input it should have refused"})
        except Exception as exc:
            rows.append({"kind": "REFUSAL", "case": name, "status": "PASS",
                         "max_score_drift": float("nan"),
                         "detail": f"{type(exc).__name__}: {str(exc)[:110]}"})

    rng = np.random.default_rng(26170)

    # --- invariances the integration note promises -------------------------
    invariance("rows shuffled", holdout.sample(frac=1.0, random_state=7))
    invariance("rows reversed", holdout.iloc[::-1])
    invariance("columns reordered",
               holdout[list(rng.permutation(holdout.columns))])
    invariance("index non-monotonic",
               holdout.set_index(np.arange(len(holdout))[::-1]))
    invariance("lots interleaved",
               holdout.sort_values(["component_id"]).sort_values("device_variant",
                                                                 kind="stable"))
    extra = holdout.copy()
    extra["an_unrelated_column"] = "ignored"
    invariance("an unexpected extra column is ignored", extra)

    # --- sensitivities: the output SHOULD move ----------------------------
    scaled = holdout.copy()
    for p in PARAMETERS:
        for e in [0, 24, 96, 168]:
            scaled[f"{p}_{e}h"] = scaled[f"{p}_{e}h"] * 1000.0
    try:
        moved = _scored(model, scaled)
        _, drift = _same(baseline, moved)
        confirmed_before = int(baseline["module_a_evidence_tier"].eq("CONFIRMED").sum())
        confirmed_after = int(moved["module_a_evidence_tier"].eq("CONFIRMED").sum())
        rows.append({
            "kind": "SENSITIVITY", "case": "every measurement x1000 (unit error)",
            "status": "PASS" if confirmed_after > confirmed_before else "REVIEW",
            "max_score_drift": drift,
            "detail": f"CONFIRMED {confirmed_before} -> {confirmed_after}. The "
                      "lot-relative statistic is scale-free so the statistical tier "
                      "barely moves; only the datasheet-limit tier notices. A unit "
                      "error is NOT caught by the statistical score — it is caught by "
                      "the spec witness, and only upward."})
    except Exception as exc:
        rows.append({"kind": "SENSITIVITY", "case": "every measurement x1000",
                     "status": "REFUSED", "max_score_drift": float("nan"),
                     "detail": str(exc)[:140]})

    noisy = holdout.copy()
    for p in PARAMETERS:
        for e in [0, 24, 96, 168]:
            column = f"{p}_{e}h"
            noisy[column] = noisy[column] * (1 + rng.normal(0, 0.01, len(noisy)))
    perturbed = _scored(model, noisy)
    agreement = float((perturbed["module_a_disposition"]
                       == baseline["module_a_disposition"]).mean())
    rows.append({"kind": "SENSITIVITY", "case": "1% multiplicative measurement noise",
                 "status": "PASS" if agreement >= 0.95 else "REVIEW",
                 "max_score_drift": _same(baseline, perturbed)[1],
                 "detail": f"disposition agreement {agreement:.4f}"})

    # --- refusals ----------------------------------------------------------
    lot = holdout["lot_id"].iloc[0]
    refusal("a lot arrives short by one component",
            holdout.drop(index=holdout.index[holdout["lot_id"].eq(lot)][0]))
    # NOT a refusal, and deliberately so. The guard's contract is "every lot in the
    # batch is complete", not "every lot in the release is present". Scoring a subset
    # of complete lots is legitimate — screening one lot is a real use. The risk is a
    # silent row-count mismatch at the fusion join, so the semantic is measured here,
    # stated in the integration note, and checked from the other side in stage 15.
    subset = holdout[~holdout["lot_id"].eq(lot)]
    scored_subset = _scored(model, subset)
    shared = baseline[baseline["component_id"].isin(scored_subset["component_id"])]
    identical = bool((shared["module_a_score"].to_numpy()
                      == scored_subset["module_a_score"].to_numpy()).all())
    rows.append({
        "kind": "SEMANTIC", "case": "a whole lot is absent from the batch",
        "status": "PASS" if identical else "FAIL",
        "max_score_drift": 0.0 if identical else float("nan"),
        "detail": f"scored {len(scored_subset)} of {len(holdout)} components, and every "
                  "score is identical to the full-batch run. Module A returns one row "
                  "per component SENT, not one per component in the release. A caller "
                  "expecting full coverage must check the row count; Module A cannot "
                  "know which lots were meant to arrive."})
    duplicated = pd.concat([holdout, holdout.iloc[[0]]], ignore_index=True)
    refusal("a component is duplicated", duplicated)
    unknown = holdout.copy()
    unknown.loc[unknown["lot_id"].eq(lot), "device_variant"] = "CMOS_Z"
    refusal("an unknown variant", unknown)
    negative = holdout.copy()
    negative.loc[0, "IDDQ_168h"] = -1.0
    refusal("a negative measurement", negative)
    zero = holdout.copy()
    zero.loc[0, "IDDQ_0h"] = 0.0
    refusal("a zero 0 h measurement", zero)
    nan = holdout.copy()
    nan.loc[0, "Propagation_Delay_96h"] = np.nan
    refusal("a null measurement", nan)
    text = holdout.copy()
    text["IDDQ_24h"] = text["IDDQ_24h"].astype(object)
    text.loc[0, "IDDQ_24h"] = "n/a"
    refusal("a non-numeric measurement", text)
    missing_column = holdout.drop(columns=["Output_Fall_Time_96h"])
    refusal("a missing measurement column", missing_column)
    mixed = holdout.copy()
    mixed.loc[mixed.index[0], "device_variant"] = (
        "CMOS_B" if mixed.loc[mixed.index[0], "device_variant"] == "CMOS_A" else "CMOS_A")
    refusal("a lot containing two variants", mixed)
    blank = holdout.copy()
    blank.loc[0, "lot_id"] = "  "
    refusal("a blank lot_id", blank)

    table = pd.DataFrame(rows)
    table.to_csv(RESULTS / "12_robustness.csv", index=False)
    failures = table[table.status.eq("FAIL")]
    summary = {
        "cases": int(len(table)),
        "invariance_cases": int(table.kind.eq("INVARIANCE").sum()),
        "refusal_cases": int(table.kind.eq("REFUSAL").sum()),
        "failures": failures[["kind", "case", "detail"]].to_dict("records"),
        "note": "A unit error is the one perturbation the statistical score cannot "
                "see, because a lot-relative robust z is scale-free by construction. "
                "That is a property of the method, not a bug, and it belongs in the "
                "integration note so nobody assumes otherwise.",
    }
    (RESULTS / "12_robustness.json").write_text(json.dumps(summary, indent=2, default=float))
    print(table.to_string(index=False))
    print(f"\n{len(table)} cases, {len(failures)} failures")


if __name__ == "__main__":
    main()
