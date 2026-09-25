# Decision log — Module A

Each entry: what was decided, when, on what evidence, and what would reopen it.
Every decision marked **closed** is re-checked mechanically by `modulea/freeze.py`
at freeze time where that is possible.

---

### D1 — Module A never emits a final disposition. **Closed, inherited.**

PASS and MONITOR only. The final PASS / MONITOR / REJECT belongs to fusion, per
`Integration_Contract_Safe.json`. `contract.validate_output` raises on anything else
and `freeze.preflight` re-checks it.

**Reopens on:** the integration team changing the contract in writing.

---

### D2 — Operating at a 1% calibration false-alarm budget. **Closed 22 Sep 2026.**

The curve (`results/03_operating_points.csv`) has a knee there: 47 of 54 at 8 false
alarms. Moving to 3% buys one more anomaly and costs sixteen more false alarms; 10%
buys two and costs seventy-seven.

The 3% figure in the RC2 and RC3 work was a **development budget**, not an operational
requirement, and is not inherited. There is still no agreed cost ratio between a missed
defect and a review flag, so this is a placeholder the team owns.

**Reopens on:** the team stating a review capacity or a cost ratio. Changing it is a
config edit and a re-freeze, not a retrain — the score is unchanged and the curve is
already measured.

---

### D3 — Weights are pure `lot_relative`. **Closed 22 Sep 2026.**

`scripts/04_nested_validation.py` re-ran the weight search inside each of 12
leave-one-lot-out folds, at two budgets.

**Across all 24 fold-selections, not one chose `overall_extreme`.** Dropping it is
therefore well supported. What replaces it is budget-dependent: at a 3% cap all twelve
folds chose pure `lot_relative`; at the shipped 1% cap they split 6/6 between pure
`lot_relative` and 0.9 `lot_relative` + 0.1 `temporal`.

**Corrected 22 Sep 2026.** An earlier revision of this entry claimed unanimity without
naming the budget it was measured at, and quoted the nested estimate from a 3% run
while the release ships at 1%. `scripts/10_verify_claims.py` caught both when the
nested stage was re-run at the shipped budget. The unanimity claim was budget-dependent
and the corrected justification is weaker.

Adopted on **simplicity**, explicitly not on performance or unanimity: pure
`lot_relative` is the simpler of the two survivors, and the PR AUC difference against
the inherited weights is +0.0008, 95% CI [−0.0081, +0.0171] — a tie.

**Reopens on:** a protocol that shows a difference whose interval excludes zero.

---

### D4 — No static limit is ever invented. **Closed, inherited from Module B.**

Seven of eighteen variant × parameter cells have no `static_spec_max`. They stay empty;
the CONFIRMED tier cannot fire on those parameters. No interpolation, no borrowing from
a neighbouring variant, no derivation from the data. Re-checked at freeze.

**Reopens on:** Tanisha supplying a sourced limit with provenance.

---

### D5 — Same-lot statistics require a proved-complete lot. **Closed, inherited.**

Proved against external lot metadata, never against a count taken from the arriving
batch — a half-delivered lot counts itself as whole. `MIN_LOT_SIZE = 30` is a secondary
sanity floor, not the proof. Tested both ways in `tests/test_guards.py`.

---

### D6 — The holdout result does not reopen the freeze. **Closed 22 Sep 2026.**

On the holdout the frozen weights rank slightly *worse* than the ones they replaced:
PR AUC 0.8166 against 0.8239, 1–2 fewer true positives at matched workload
(`results/09_ranking_comparison.json`).

**No change made.** The configuration was selected without seeing the holdout, by a
protocol fixed in advance, and unanimously. Reverting it now because of a holdout
result is exactly the failure mode the freeze prevents, and it would make every number
in `docs/VALIDATION_SUMMARY.md` unverifiable. The difference is within the noise the
calibration bootstrap already described.

**Reopens on:** nothing on this dataset. On the fresh post-freeze test set, both
weightings may be evaluated together as pre-declared candidates.

---

### D7 — The CONFIRMED tier is described with a bound, never as "never wrong".
**Closed 22 Sep 2026.**

81 flags, 81 anomalies, 0 normals across 5,400 components. Zero observed errors in
5,076 normals is not a zero rate; the 95% one-sided upper bound is 0.06%. Every
document states it that way, and `scripts/10_verify_claims.py` checks that the bound
is present and non-zero.

**Reopens on:** nothing. This is a statement about what the evidence supports.

---

### D8 — `module_a_score` is one monotone number with a reserved band.
**Closed 22 Sep 2026.**

Supersedes RC2's `max(core_score, residual_score)`, which was not monotone with its own
disposition — in its shipped holdout file 54 PASS rows scored above the weakest REVIEW
row. Fusion thresholding that column would not have reproduced Module A's decisions.

Here `[0, 0.90)` is statistical evidence and `[0.90, 1.00]` is out-of-specification, so
a single threshold reproduces the disposition exactly. `contract.validate_output`
refuses a frame where it does not, and `tests/test_tiers.py` reproduces the RC2 defect
to prove the check catches it.

---

### D9 — No early-epoch classifier is trained against a final label.
**Closed 22 Sep 2026.**

At 0 h a component whose defect begins at 168 h is not abnormal yet. A model taught to
predict the final label from 0 h data learns the lot, not the part. The early epochs
therefore report **observed deviation only**, with thresholds fitted on calibration
normals at the same budget, and the low early recall is documented as a property of the
question rather than a miss rate.

---

### D10 — The inherited packages are preserved, not adopted. **Closed 22 Sep 2026.**

Better Potential, RC2 Hybrid and RC3 Specialist remain runnable as shipped. Measured
under one protocol, RC2's residual band does not beat simply lowering the threshold
(paired lot bootstrap, ΔTP interval contains zero at every budget), and at matched
workload the plain core score equals RC3 exactly and beats RC2 on both axes. Neither
add-on is carried into this release.

**Reopens on:** an add-on that moves PR AUC with an interval excluding zero.
