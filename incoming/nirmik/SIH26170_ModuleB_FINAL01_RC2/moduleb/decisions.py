"""
moduleb.decisions — the release decisions, as something a machine can check.

A decision log is prose, and prose does not stop a freeze. Every decision below
carries a predicate that reads the live code, so "D11 is closed with the cap
off" is not a sentence someone has to remember to honour — stage 11 refuses to
freeze while it is false.

The predicates deliberately read the *implementation*, not a copy of the
decision. `d11` asks `config.FORECAST_REL_DELTA_CAP is None`; it does not ask
whether a constant called `D11_STATE` says "OFF", because that constant could
agree with the log and disagree with the model.

Full reasoning for each decision lives in docs/DECISION_LOG.md. This module is
the enforcement, not the record.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Decision:
    id: str
    closed: str              # date the decision closed
    statement: str           # what was decided, in one line
    predicate: Callable[[], bool]
    failure: str             # what to say when the predicate is false


def _d1() -> bool:
    """Module B emits no PASS / MONITOR / REJECT, not even as NOT_SET."""
    from .constants import FORBIDDEN_OUTPUT_COLS, contract_columns
    from . import config
    tau_pct = int(round(config.ENVELOPE_TAU * 100))
    cols = contract_columns(tau_pct)
    return ("module_b_disposition" in FORBIDDEN_OUTPUT_COLS
            and not any(c in cols for c in FORBIDDEN_OUTPUT_COLS))


def _d10() -> bool:
    """The pre-declared fall-time rule did not fire; the frozen feature set stands."""
    from . import config
    return config.RECOMMENDED["Output_Fall_Time"]["features"] == "own+lot+cross"


def _d11() -> bool:
    """FORECAST_REL_DELTA_CAP stays off for this release."""
    from . import config
    return config.FORECAST_REL_DELTA_CAP is None


def _d12() -> bool:
    """The serving contract is cohort-level and completeness must be proved."""
    from . import config, serving
    return (serving.REQUIRES_COMPLETENESS_PROOF
            and serving.PARTIAL_LOT_DEFAULT is False
            and config.MIN_LOT_COHORT == 30)


def _d13() -> bool:
    """Tail coverage ranks by observed relative drift from 24 h, not by residual."""
    import numpy as np
    from .envelope import coverage_report
    y = np.array([1.0, 1.2, 1.5, 2.0])
    rep = coverage_report(y, y * 1.1, y * 0.99, np.ones(4))
    return rep["tail_rank_basis"] == "true_relative_drift_from_24h"


def _d14() -> bool:
    """The corrected pre-freeze holdout provenance is recorded, intact and unedited.

    This is a statement about history, so it stays true after the one-shot is spent.
    Whether the one-shot has been spent is a live fact read from disk by
    `holdout_manifest.one_shot_state()`, not a constant asserted here.
    """
    from . import holdout_manifest as hm
    p = hm.PROVENANCE
    return (p["predictor_only_file_read_before_freeze"] is True
            and p["hidden_168h_truth_available_to_module_b"] is False
            and p["holdout_forecast_generated"] is False
            and p["holdout_score_observed"] is False
            and p["model_or_config_decision_used_holdout_outcome"] is False
            and hm.one_shot_state() in ("SPENT", "UNSPENT"))


RELEASE_DECISIONS: list[Decision] = [
    Decision("D1", "2026-09-15",
             "Module B emits forecasts and evidence, never a disposition.",
             _d1,
             "a disposition column is reachable from the output contract"),
    Decision("D10", "2026-09-18",
             "The pre-declared Output_Fall_Time rule did not fire; features stay "
             "own+lot+cross.",
             _d10,
             "moduleb.config no longer matches the executed pre-declared decision"),
    Decision("D11", "2026-09-19",
             "FORECAST_REL_DELTA_CAP = None. The cap stays off for this release.",
             _d11,
             "the relative-delta cap is enabled; D11 closed LEAVE_OFF and enabling it "
             "is a model change requiring a new recorded decision"),
    Decision("D12", "2026-09-19",
             "Cohort-level serving contract: completeness is proved, not assumed.",
             _d12,
             "the serving contract no longer requires a completeness proof, or "
             "MIN_LOT_COHORT moved without a new decision"),
    Decision("D13", "2026-09-19",
             "Tail coverage is ranked by true relative drift from 24 h.",
             _d13,
             "the tail metric no longer ranks by observed drift; a model-dependent "
             "tail definition moves with the forecast and cannot be compared"),
    Decision("D14", "2026-09-19",
             "Corrected holdout-access provenance: no target, forecast, score or "
             "decision before the freeze.",
             _d14,
             "the recorded holdout provenance no longer matches the corrected history"),
]


def check_release_decisions() -> list[str]:
    """Return one message per failing decision. Empty means every decision holds."""
    out = []
    for d in RELEASE_DECISIONS:
        try:
            ok = bool(d.predicate())
        except Exception as exc:                       # a predicate that cannot run is a failure
            out.append(f"{d.id}: predicate raised {type(exc).__name__}: {exc}")
            continue
        if not ok:
            out.append(f"{d.id}: {d.failure}")
    return out


def decision_state() -> dict:
    """The machine-readable state, for the release manifest and the receipts."""
    return {d.id: dict(closed=d.closed, statement=d.statement,
                       holds=bool(_safe(d))) for d in RELEASE_DECISIONS}


def _safe(d: Decision) -> bool:
    try:
        return bool(d.predicate())
    except Exception:
        return False


# ---------------------------------------------------------------- limitations
# The list that travels with the release. Every item here is something a reader
# of the output could otherwise mistake for a guarantee, and every one of them
# is measured or stated elsewhere in the package — none is a hedge.
KNOWN_LIMITATIONS: list[str] = [
    "Input_Leakage_Current is ~33 % WORSE than the median-ratio baseline on the "
    "twelve calibration lots (acceptance criterion M5, FAIL). 27.7 % of that error "
    "sits on one component of 906. D11 closed with the relative-delta cap OFF, so "
    "this is carried into the freeze as a known limitation, not a fixed defect.",

    "IDDQ and Active_Supply_Current tie a single per-variant constant under the "
    "pre-declared 5 % rule. For those two parameters Module B is not better than a "
    "well-chosen constant, and that is reported rather than hidden.",

    "The p95 envelope is evidence, never a screen. Marginal coverage is calibrated "
    "(0.933-0.974 measured on calibration); coverage on the worst-drifting decile is "
    "0.407-0.769. It must never be described as a safety or detection guarantee.",

    "No cluster-conformal derivation exists for the implemented score construction on "
    "whole-lot units, so conformal coverage here is MEASURED, not proved "
    "(review finding F2).",

    "The timing forecasts and every evidence column are COHORT statistics: they are "
    "computed against the components present in the request. A lot delivered "
    "incomplete answers a different question, which is why completeness must be "
    "proved and why the partial-lot override is recorded as degraded (D12).",

    "Seven of eighteen variant x parameter cells have no static_spec_max in "
    "Device_Specs. No limit is invented for them and the limit-based reason codes "
    "never fire there (D1).",

    "The measurement-noise CVs are the team's stated design assumptions, not "
    "measurements, and every figure derived from them inherits that status.",

    "FINAL-01 is synthetic. Claims about physical realism are claims about the "
    "generator, not about silicon, and no external standard has been cited as "
    "authority for any threshold in this package.",

    "Module B has no correctness label for its own B_ reason codes. Sparsity is "
    "measured; precision and recall of the codes are not, and cannot be here "
    "(review finding A1).",
]
