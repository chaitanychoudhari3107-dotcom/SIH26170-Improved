"""
moduleb.config — every tunable number in Module B, in one place.

Why one file: the freeze stage hashes this module's contents into the model
manifest. If a number here changes, the frozen artifact is provably a different
model. Scattering constants across the codebase makes that check meaningless.

FROZEN STATUS (18 Sep 2026)
---------------------------
The block marked FROZEN_V1 is carried over unchanged from the Candidate V1
freeze recorded in 07_candidate_v1/DECISIONS_2026-09-15.md (D2). It is
reproduced here byte-for-byte on purpose: the first job on FINAL-01 is to rerun
the V1 configuration untouched so the V1 -> FINAL-01 difference is attributable
to the data and not to model shopping. Do not edit the FROZEN_V1 block to make a
number look better.
"""
from __future__ import annotations

from .constants import CURRENT_GROUP, PARAMS, TIMING_GROUP

# ============================================================== FROZEN_V1 begin
# Structure: one model per parameter, all variants pooled with a variant one-hot,
# predicting the RELATIVE delta from the 24h reading rather than the absolute
# 168h level. Two feature groups, chosen on a mechanism rather than on 18
# independent per-cell picks:
#
#   current/leakage — the 0->24h delta is noise-dominated (SNR ~0.7-0.9) and the
#       cross-parameter early->late couplings are weak. Extra features add
#       variance without signal, so the simplest feature set wins.
#   timing — delay/rise/fall share a latent slew factor (drift correlation
#       0.65-0.73) and one another's early deltas genuinely carry late-drift
#       information (cross correlation 0.23-0.33).
RECOMMENDED: dict[str, dict] = {
    **{p: dict(structure="pooled", model="Huber", features="own") for p in CURRENT_GROUP},
    **{p: dict(structure="pooled", model="Huber", features="own+lot+cross") for p in TIMING_GROUP},
}

# Hyper-parameters. Selected by nested whole-lot CV on training lots only;
# the nested check concluded that further tuning is noise.
HUBER = dict(epsilon=1.35, alpha=1e-3, max_iter=800)
RIDGE = dict(alpha=10.0)
GBR = dict(n_estimators=200, learning_rate=0.07, max_depth=3,
           subsample=0.8, min_samples_leaf=20, random_state=0)

N_FOLDS = 7                 # whole-lot GroupKFold folds used for every CV number
GLOBAL_SEED = 0             # every stochastic step derives from this

# --- upper envelope --------------------------------------------------------
# Conformalised gradient-boosted quantile regression (CQR, Romano et al. 2019).
# ENVELOPE_TAU is the operating point; 0.99 roughly triples the width for a
# modest gain in tail capture. READ docs/MODEL_CARD.md before calling this a
# screen: marginal coverage is calibrated, conditional coverage on the
# worst-drifting decile is not.
ENVELOPE_TAU = 0.95
ENVELOPE_CONF_LOTS = 6      # training lots held back to calibrate conformity scores
ENVELOPE_GBR = dict(loss="quantile", n_estimators=200, learning_rate=0.07,
                    max_depth=3, subsample=0.8, min_samples_leaf=20, random_state=0)

# --- reason-code thresholds ------------------------------------------------
# Deliberately sparse. A flag that fires on most components is not evidence, it
# is noise with a name — scripts/07_reason_code_audit.py measures the firing
# rate of every flag and fails the build if one becomes common.
FLAG_HIGH_DRIFT_Z = 3.0         # primary parameter's predicted drift, robust z within variant
FLAG_WIDE_ENVELOPE_PCTL = 0.90  # widest decile AMONG components this parameter drives
FLAG_LOT_Z = 3.0                # |robust z| of the 24h reading against the component's own lot
# There is deliberately no "near limit" percentage. The limit-based codes use the
# limit ITSELF as the threshold, so no constant is invented, and the seven
# variant x parameter cells with no static_spec_max simply never fire (decision D1).

# Declared measurement-noise CVs (design record s6.3). These are the team's
# ASSUMPTIONS, not measurements — they are labelled as such in the model card.
# The noise on a 0->24h delta is CV*sqrt(2); a move below that carries no signal.
NOISE_CV = {
    "IDDQ": 0.010,
    "Input_Leakage_Current": 0.020,
    "Active_Supply_Current": 0.005,
    "Propagation_Delay": 0.0035,
    "Output_Rise_Time": 0.0045,
    "Output_Fall_Time": 0.0045,
}
# --- extrapolation guard (PROPOSED, OFF) -----------------------------------
# A hard cap on the predicted relative delta from 24h, applied at inference.
# None means no cap, which is the Candidate V1 behaviour and therefore the frozen
# one. Stage 7 measures what a cap would do; it is deliberately left OFF so this
# package reproduces the frozen model exactly. Turning it on changes
# frozen_config_digest(), which is the point: it is a model change and has to be
# recorded as one, not slipped in as a bug fix.
FORECAST_REL_DELTA_CAP: float | None = None
# ============================================================== FROZEN_V1 end

# --- serving contract ------------------------------------------------------
# Review finding F1, 19 Sep 2026. The timing models use own-lot medians, and the
# evidence layer ranks each component against the other components in the same
# request. Both are therefore properties of the COHORT, not of one row. A
# single-component request silently produces a different answer: measured on
# calibration lot B_L23, the timing forecasts move by up to 7.18 % and
# module_b_primary_parameter collapses to IDDQ for every component.
#
# So Module B's serving contract is cohort-level: a request carries whole lots.
# MIN_LOT_COHORT is the floor below which predict_frame refuses rather than
# answering wrongly. It is a pragmatic threshold, not a statistical one — the
# smallest real lot in FINAL-01 carries 68 components, and 30 is a little under
# half, so a partial delivery still works while a handful of rows does not.
#
# This is deliberately NOT in the FROZEN_V1 block and NOT in the digest: it
# changes no fitted parameter and alters no forecast that was ever valid. It
# converts a silently wrong output into an explicit error.
MIN_LOT_COHORT = 30

# --- acceptance thresholds for the self-checks -----------------------------
# Not model parameters. These are the pass/fail lines the runner scripts apply
# to their own output, so a bad run fails loudly instead of writing a plausible
# CSV. See docs/ACCEPTANCE_CRITERIA.md.
TIE_THRESHOLD_PCT = 5.0        # MAE differences below this are ties, whatever the rank
PAIRED_TEST_ALPHA = 0.05       # per-lot Wilcoxon signed-rank level
MAX_FLAG_FIRING_RATE = 0.25    # any single B_ flag above this is not evidence
MAX_ANY_FLAG_RATE = 0.60       # fraction of components carrying at least one code

# Pre-declared calibration decision, carried over from the V1 freeze unexecuted.
# Scoped to exactly one parameter and one binary choice; both conditions must
# hold or the frozen feature set stands. Recorded before calibration was opened.
PREDECLARED_FALLTIME_RULE = dict(
    param="Output_Fall_Time",
    move_to="own",
    from_set="own+lot+cross",
    min_mae_gain_pct=3.0,
    min_lots_won=4,
    of_lots=6,
    note="Declared 14 Sep 2026, before ModuleB_Calibration.csv existed. "
         "The lot counts were written for the Candidate V1 calibration file "
         "(6 lots). FINAL-01 ships 12 calibration lots, so the rule is applied "
         "as a proportion: > half of the calibration lots, i.e. >= 7 of 12.",
)


def frozen_config_digest() -> str:
    """SHA-256 of the FROZEN_V1 block's effective values.

    Hashing the parsed values rather than the source text means a comment edit
    does not invalidate a frozen model, but a changed number does.
    """
    import hashlib
    import json
    payload = json.dumps(
        dict(
            recommended={p: RECOMMENDED[p] for p in PARAMS},
            huber=HUBER, ridge=RIDGE, gbr=GBR,
            n_folds=N_FOLDS, seed=GLOBAL_SEED,
            rel_delta_cap=FORECAST_REL_DELTA_CAP,
            envelope=dict(tau=ENVELOPE_TAU, conf_lots=ENVELOPE_CONF_LOTS, gbr=ENVELOPE_GBR),
            flags=dict(drift_z=FLAG_HIGH_DRIFT_Z, wide_pctl=FLAG_WIDE_ENVELOPE_PCTL,
                       lot_z=FLAG_LOT_Z),
            noise_cv=NOISE_CV,
        ),
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()
