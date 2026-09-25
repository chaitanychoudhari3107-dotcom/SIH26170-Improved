# Module B model card

**Module:** B — early 168 h drift forecasting
**Dataset:** `SIH26170-FINAL-01` (5,400 components, 72 lots, 3 CMOS variants)
**Owner:** Nirmik · **Release candidate:** `ModuleB-FINAL01-RC2`
**Status:** `HOLDOUT_PREDICTION_DELIVERED` — **frozen 20 Sep 2026** on a recorded team
sign-off; the one-shot holdout run is **spent**. The fitted model is final and is not
retuned in response to any score
**Digests:** three, and they answer different questions. `config.frozen_config_digest()`
— is this the same fitted model? `serving.runtime_contract_digest()` — does it still
behave the same way to a caller? `freeze.source_tree_digest()` — is this the same code?
All three, with the input hashes, are in `RELEASE_MANIFEST.json` and in the frozen
artifact's manifest.

## The serving contract

Module B answers a request about **whole, complete lots**. The timing models read
own-lot medians and every evidence column ranks a component against the others in the
request, so a lot delivered with components missing answers a different question.

Completeness is **proved**, not assumed: the caller supplies either declared per-lot
sizes (`expected_lot_sizes`) or the custodian's whole-file attestation (SHA-256, rows,
lots). Without one of them the request is refused, whatever its row count.
`MIN_LOT_COHORT = 30` is a secondary sanity floor and nothing more.
`allow_partial_lot=True` is the single explicit override; it records the offending lots
and their counts and makes the run report non-clean. (Decisions D12, D15.)

## What it does

For each component, predict the 168 h value of six electrical parameters using
only measurements available at 0 h and 24 h, and emit forecast-risk evidence
alongside each forecast.

## What it does not do

It does not decide PASS / MONITOR / REJECT. That belongs to Module A + fusion
(decision D1, 15 Sep 2026). There is no `module_b_disposition` column, and it is
not emitted as `NOT_SET` either — an always-null column invites a fusion rule
built against a field Module B has no authority over.

## Allowed inputs

| Allowed | Forbidden |
|---|---|
| `component_id`, `lot_id`, `device_family`, `device_variant` | any `*_96h` column |
| the six parameters at 0 h | any `*_168h` value as a feature |
| the six parameters at 24 h | hidden anomaly labels, defect modes, severity, onset |
| own-lot medians of the above | holdout 168 h targets |
| the `Device_Specs` 0 h baseline (a fixed external constant) | anything measured after 24 h |

Enforced in `moduleb/guards.py`, on the file *and* on the matrix handed to each
estimator. A violation raises; it does not warn.

## Model

One regressor per parameter. All three variants pooled, with a variant one-hot.

| Parameter | Model | Feature set |
|---|---|---|
| IDDQ | Huber | `own` |
| Input_Leakage_Current | Huber | `own` |
| Active_Supply_Current | Huber | `own` |
| Propagation_Delay | Huber | `own+lot+cross` |
| Output_Rise_Time | Huber | `own+lot+cross` |
| Output_Fall_Time | Huber | `own+lot+cross` |

`HuberRegressor(epsilon=1.35, alpha=1e-3, max_iter=800)` behind a
`StandardScaler`, refit inside every fold so the scaler never sees a validation
lot. All fits converge well inside `max_iter` on FINAL-01.

**Target parameterisation.** The model predicts the relative change from 24 h,
`y = (x168 − x24) / x24`, and the forecast is `x24 · (1 + ŷ)`. Two reasons: it
makes the variants commensurable, so one pooled model replaces three thin ones;
and it means the model learns only the drift instead of re-deriving a level that
has already been measured.

**Why two feature groups, and not eighteen per-cell picks.** The current/leakage
block's 0→24 h delta is noise-dominated (measured SNR 0.50–0.94 against the
declared noise) and its cross-parameter early→late couplings are weak, so extra
features add variance without signal. The timing block shares a latent slew
factor — within-variant drift correlations of 0.14–0.59 — and the members'
early deltas genuinely cross-predict. Two groups, one mechanism each.

**Why linear models get fewer columns.** `delta = x24 − x0` and
`dev = x − lot_median` are exact linear combinations of the level terms. Handing
all of them to OLS/Ridge/Huber at once is exact collinearity, so the redundant
forms go only to the tree model, which cannot construct them itself.

## Validation

Whole-lot `GroupKFold`, 7 folds, lots dealt round-robin within each variant so
every fold holds out two lots of each. Deterministic from the lot names — the
same file always gives the same fold map. Row-level splitting raises.

Significance is tested on **per-lot** MAEs (42 lots), not on rows. The team rule
stands: differences under 5 % MAE are ties whatever the rank or the p-value.

## Performance, whole-lot CV on the 42 training lots

MAE below is the **row-weighted pooled** MAE. The per-lot test beside it uses
macro-lot means (every lot weighted equally), which differ slightly because the
lots are not the same size — `results/03_cv_metrics.csv` and
`results/03_paired_lot_test.csv` respectively.

| Parameter | MAE | vs median-ratio | lots won | Wilcoxon p | verdict |
|---|---|---|---|---|---|
| IDDQ | 0.02412 µA | +0.4 % | 22/42 | 0.60 | TIE |
| Input_Leakage_Current | 0.00442 µA | +6.8 % | 34/42 | 0.00009 | BETTER |
| Active_Supply_Current | 1.04117 µA | +3.9 % | 25/42 | 0.034 | TIE |
| Propagation_Delay | 0.08956 ns | +8.9 % | 31/42 | 0.0013 | BETTER |
| Output_Rise_Time | 0.06773 ns | +8.8 % | 33/42 | 0.00002 | BETTER |
| Output_Fall_Time | 0.06781 ns | +8.4 % | 30/42 | 0.0015 | BETTER |

On the 12 held-out calibration lots, `Active_Supply_Current` turns BETTER
(+5.6 %) and `Input_Leakage_Current` turns **worse** (−33 %) — the latter driven
by a single component; see Limitations.

MAE sits 3.1×–6.1× above the assumed measurement-noise floor, so the problem is
neither solved nor unpredictable.

## Uncertainty: the p95 envelope

Conformalised gradient-boosted quantile regression (CQR). Six complete training lots
are withheld from envelope fitting and supply the conformity scores.

**What is claimed:** an *empirical* out-of-lot calibration — marginal coverage measured
on twelve unseen calibration lots. **What is not claimed:** a finite-sample
split-conformal theorem. That result needs exchangeable calibration and test units, and
the conformity scores here are per-component inside those six lots, while this project
treats within-lot components as dependent everywhere else. No cluster-conformal
derivation has been produced for the implemented construction. *(Corrected 19 Sep,
review finding F2.)*

Measured on the calibration lots at τ = 0.95:

| Parameter | marginal coverage | **tail** coverage | mean width |
|---|---|---|---|
| IDDQ | 0.967 | 0.681 | 7.7 % |
| Input_Leakage_Current | 0.974 | 0.769 | 10.0 % |
| Active_Supply_Current | 0.955 | 0.593 | 5.0 % |
| Propagation_Delay | 0.958 | 0.604 | 4.2 % |
| Output_Rise_Time | 0.933 | **0.407** | 4.4 % |
| Output_Fall_Time | 0.942 | 0.451 | 4.9 % |

*Corrective run, 19 Sep 2026 (review finding F3): the tail is the decile with the
largest observed relative drift from 24 h. It was previously ranked by forecast
residual, which is a different population. Marginal coverage is unchanged; the
superseded tail figures are kept in `results/`.*

**May be said:** the envelope is marginally calibrated — across the population,
its stated level is close to what it delivers.

**Must not be said:** that it catches 95 % of the parts that drift worst. The
tail column measures exactly that and it is far below nominal. A part inside its
p95 envelope is **not** thereby safe. The envelope is evidence for fusion; the
outlier judgement belongs to Module A.

## Evidence layer

`module_b_primary_parameter` is the parameter whose predicted relative drift is
largest in robust z-units **against the same variant** — scale-free, so µA and ns
are comparable and no static limit is needed.

`module_b_reason_codes` is a `|`-separated list in the `B_` namespace:

| Code | Fires when | Rate (calibration) |
|---|---|---|
| `B_HIGH_FORECAST_DRIFT:<p>` | the primary parameter's drift z ≥ 3 | 5.8 % |
| `B_WIDE_ENVELOPE:<p>` | envelope width in the top decile **among components this parameter drives** | 10.9 % |
| `B_LOT_OUTLIER_24H:<p>` | \|robust z\| ≥ 3 against the component's own lot at 24 h | 2.8 % |
| `B_FORECAST_EXCEEDS_LIMIT:<p>` | the forecast reaches an **available** static limit | 0.7 % |
| `B_ENVELOPE_REACHES_LIMIT:<p>` | the envelope does, and the forecast does not | 0.6 % |
| `B_NO_EARLY_SIGNAL:<p>` | the 0→24 h move is below the noise scale — **and only where a risk flag already fired** | 1.4 % |

14.9 % of components carry any code at all. Three design rules keep it that way,
and each is tested rather than asserted: the reference class for a flag is the
population it is ranked against, never a larger one; a cell with no
`static_spec_max` never fires a limit code; and a qualifier true of ~40 % of the
fleet never stands alone.

24 evidence columns carry the raw numbers behind the flags so fusion can apply
its own thresholds instead of inheriting these. `evidence_<p>_limit` is NaN where
no limit exists, and NaN is the correct answer there.

## Limitations

1. **One forecast dominates one parameter.** On the calibration lots, one
   component of 906 receives a +195 % predicted drift where the truth was +50 %,
   and it carries 27.7 % of `Input_Leakage_Current`'s total error. Without that row
   the parameter is a tie with median-ratio; with it, Module B is 33 % worse. A
   relative-delta cap is implemented, tested and **off**: D11 closed LEAVE_OFF on
   19 Sep because the value would be post-hoc on calibration, the case is a true
   positive with an exaggerated magnitude, and no independent bound is both
   available and effective. Carried into freeze as a known limitation.
2. **Two parameters are ties.** IDDQ and (on train CV) Active_Supply_Current are
   matched by one constant per variant. That is a result, not a gap to close.
3. **Systematic under-prediction.** `MeanSignedError` is negative for all six
   parameters, 46–48 % of forecasts sitting low. Smaller than the median-ratio
   baseline's bias, but in the direction that matters for screening.
4. **Tail coverage is not nominal** (see above).
5. **The noise CVs are assumptions,** taken from the design record §6.3, not
   measurements. Everything derived from them — `B_NO_EARLY_SIGNAL`, the SNR
   table, the noise floor — inherits that.
6. **Seven variant × parameter cells have no static limit.** No limit-based
   evidence exists there, by design.
7. **42 training lots.** Effect sizes under ~5 % cannot be distinguished from
   fold noise at this sample size.
8. **The serving contract is cohort-level.** The timing models read own-lot medians
   and the evidence layer ranks against the request cohort, so a single-component call
   is not equivalent to a full-lot call — timing forecasts move by up to 7.18 % and the
   primary parameter degenerates. `predict_frame` refuses lots under 30 rows.
   *(Review finding F1; the previous card implied per-component stability.)*
9. **Synthetic data.** Every number here describes SIH26170-FINAL-01. None of it
   is a claim about real burn-in behaviour, and the safety margins are a team
   choice, never a NASA, ISRO or MIL-STD requirement.

## Reproducibility

Single seed (`GLOBAL_SEED = 0`); deterministic fold assignment; sorted iteration
throughout; no randomness outside the conformal lot draw, which is seeded. The
freeze manifest records the SHA-256 of every input file, the config digest, and
the library versions. `freeze.load_frozen` refuses an artifact whose digest does
not match the code loading it.
