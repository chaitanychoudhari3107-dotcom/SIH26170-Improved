# What changed, and what else is worth doing

Part one is every change made in this release against the three inherited packages.
Part two is the improvements identified but **not** made, with the reason.

---

## Part one — changes made

### Defects found in the inherited code, and their fixes

| # | Defect | Status on this data | Fix |
|---|---|---|---|
| C1 | RC2's `module_a_score = max(core, residual)` is not monotone with its own disposition — 54 PASS rows scored above the weakest REVIEW row | **Live** | One monotone score with a reserved band; `contract.validate_output` refuses a frame where a single threshold does not reproduce the disposition. `tests/test_tiers.py` reproduces the RC2 defect to prove the check catches it |
| C2 | Review threshold selected on out-of-fold scores, then applied to a model refitted on all data — the score distributions differ | **Live in RC2/RC3** | No residual model exists. The threshold is selected out of fold and the *same* score function serves |
| C3 | A feature with zero reference MAD is scored `z = 0`, i.e. perfectly normal, for every component of that variant | **Dormant** — 0 of 180 references affected on this release | Declared ladder MAD → IQR/1.349 → std, then **raise**. Never silently zero. `tests/test_reference.py` |
| C4 | The stated reason could name a component whose weight is exactly 0.0, contributing nothing to the flag | **Live** | Reason codes are built only from components with non-zero weight. `tests/test_reason_codes.py` |
| C5 | Primary-parameter attribution unstable — two methods agreed on only 81% of the same 73 components | **Live** | `module_a_attribution_margin` ships alongside, and the field is blank on PASS rows where the attribution is noise being ranked |
| C6 | Weights and cutoff grid-searched on the full calibration set; grouping the residual model did not undo it | **Live** | Weights *and* threshold re-selected inside each of 12 leave-one-lot-out folds. `results/04_nested_validation.csv` reports what that costs: the honest estimate is 48/54, not the development-fit 44/54 at a tighter FPR |

### Methodology

- **Leave-one-lot-out replaces repeated k-fold.** With 12 lots
  `StratifiedGroupKFold` returns the same partition for every seed — 4 of 5 seeds gave
  a byte-identical assignment. Repeats reported a spread of zero and implied a stability
  nobody had measured. Uncertainty now comes from a bootstrap over whole lots.
- **Nested selection.** No previous Module A candidate reported a number with the
  configuration chosen inside the fold.
- **Ties are named as ties.** Two comparisons in this release have bootstrap intervals
  containing zero and are reported as no measurable difference, not as small wins.
- **The result that went the wrong way is reported.** The frozen weights rank slightly
  worse on the holdout than the ones they replaced, and the freeze was not reopened.

### Capability

- **A non-statistical witness.** The datasheet `static_spec_max` check: 81 flags across
  5,400 components, 81 real anomalies, zero normals. Not a fitted threshold, so nothing
  to overfit and nothing to drift. It certifies rather than adds recall.
- **Epoch semantics separated.** Detection of an already-active deviation is not
  conflated with warning about a future one. Early recall is documented as a property
  of the question, never quoted as a miss rate.
- **The blind spot renamed from a behaviour to a mechanism** — within-spec static
  offsets, measured at 6 of 21 against 7 of 7 for spec failures, with the ceiling
  established across nine statistics from five families.

### Engineering

- 13 modules, none over 200 lines, against the inherited single 1,456-line notebook
  export. Each is separately openable and separately tested.
- 38 tests, including a poisoning test that sets a 168 h column to 1e6 and asserts a
  24 h score is unchanged.
- Guards raise instead of coercing: partial lots, batches that count themselves as
  complete, unknown variants, duplicate ids, non-positive measurements, mixed-variant
  lots, ground-truth columns reaching a scoring frame.
- The hidden labels have exactly one door, imported by no fitting path.
- Config and runtime contract are separately digested; a reload under a changed config
  raises rather than silently serving a different model.
- Freeze is gated on a real sign-off, embedded before the bytes are written, with the
  release decisions re-checked mechanically.
- Predictions are hashed when written; the evaluator refuses to score a file that
  changed afterwards.
- `scripts/10_verify_claims.py` checks every figure quoted in `docs/` against a file in
  `results/` — 18 checks, all passing. This is what makes the master prompt's
  zero-unsupported-claims rule a property of the release rather than a promise.

---

## Part two — identified, not done, and why

Ordered by what I would do next.

### 1. A fresh lot-grouped test set — **the only one that actually matters**

Every holdout number in this release is diagnostic. The holdout shaped RC1, RC2, RC3
and now this release's reporting. Until a set of lots nobody has looked at is scored
once, no performance claim should leave the team.

*Cost:* Chaitany regenerating with new seeds, same generator configuration, held by
Sanskruti and opened once. **Not** a regeneration of FINAL-01, which stays frozen.

### 2. Fix the calibration split's composition — a dataset job, not a modelling one

Calibration holds four within-spec static offsets against the holdout's seventeen.
Nothing selected on calibration can be tuned for the failure mode that dominates the
remaining misses. No validation protocol fixes a population that is not there.

*Cost:* one conversation with whoever owns the generator, before the next split.

### 3. Physically motivated parameter relationships

The remaining misses are components that are individually within spec and individually
unremarkable against their lot. The one thing not yet tried is whether they violate a
*relationship* between parameters that physics fixes — IDDQ against
`Active_Supply_Current`, or rise against fall time — rather than a marginal
distribution. Robust within-lot Mahalanobis was tested and did not help (4–6 of 18),
but that is an unconstrained multivariate distance, not a physically justified ratio.
Tanisha would need to name the relationship; a ratio nobody can justify is another
fitted threshold.

*Cost:* one domain conversation, then a day. *Risk:* may hit the same ceiling.

### 4. Per-parameter evidence with the null properly controlled

The current aggregate takes a maximum over 24 parameter-epoch values, so a healthy
component's maximum routinely reaches 2.4 z simply by being a maximum over 24 draws,
which is where a genuine 2.3 z static offset disappears. Converting each
parameter-epoch deviation to a p-value against its own null and applying a multiplicity
correction would make the evidence comparable across defect shapes. Not attempted here
because it is a redesign of the score, and this release's brief was to close out
honestly rather than to keep searching.

### 5. Measure what the review band costs in reviewer time

The whole trade-off is stated in false alarms per 1,343 components. Nobody has said
what a review costs. Until they do, the operating point is a placeholder the team owns
and D2 stays open in substance even though it is closed in code.

### 6. Re-derive the feature design under the nested protocol

The 60-feature block and the top-k aggregation depths are inherited from full-calibration
development. This release re-selected the weights and threshold — where the selection
pressure was — but not the feature design. A genuinely pristine estimate would include it.

*Cost:* significant. *Expected gain:* small, given that every aggregation variant tested
landed within noise of every other.

### 7. Things deliberately **not** worth doing

- **Another ensemble.** Two were built and measured. RC2's residual band does not beat
  lowering the threshold (ΔTP interval contains zero at every budget); RC3's specialists
  reproduce the plain threshold exactly at matched workload, agreeing on 66 of 67
  detections. A third would need to move PR AUC with an interval excluding zero, and
  nothing tried so far has come close.
- **Grid-searching more algorithms against this holdout.** It is no longer a test set.
- **Tuning a statistical threshold to zero false alarms and calling it a guarantee.**
  It sits at 0.956835 on calibration and catches 38 of 54, and it is a fitted quantity
  on 852 parts that will not hold on an unseen lot. The CONFIRMED tier is the honest
  version of that idea.
- **Weakening labels or making anomalies easier to raise reported scores.**
