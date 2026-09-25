# Future release items

Everything found and deliberately **not** fixed in `ModuleA-FINAL01`, with why. The
hardening phase's rule is that a flaw found after the freeze is written down, not
quietly repaired, because the holdout is spent and there is nothing left to validate a
change against.

Ordered by value.

---

### F1 — Calibration-split Module B forecasts, so B corroboration can become a rule

**The single most valuable open item, and it is a cross-module ask.**

On the holdout, the 19 Module A flags that Module B corroborates on the same parameter
are **19 of 19 real anomalies**, against 46 of 59 without corroboration
(`results/14_b_corroboration.csv`). That is a large association and it is currently
unusable: the only data where Module A's output, Module B's forecasts and the labels
all exist is the holdout, so any policy fitted there would be fitted on the labels it
would then be judged against.

**What is needed:** Module B produces forecasts for the 906 calibration components,
using a model fitted without them. Then a confirmation policy can be fitted on
calibration and tested on a fresh set.

**Who:** Nirmik owns both modules, so this is one decision, not a negotiation. Cost is
one prediction run of a model that already exists.

---

### F2 — A fresh lot-grouped test set

Every holdout number in this release is diagnostic. The holdout shaped RC1, RC2, RC3
and now this release's reporting. Until a set of lots nobody has looked at is scored
once, no performance claim should leave the team.

**Not** a regeneration of FINAL-01, which stays frozen. New seeds, same generator
configuration, held by Sanskruti, opened once.

---

### F3 — Fix the calibration split's composition

Calibration holds four within-spec static offsets against the holdout's seventeen.
Nothing selected on calibration can be tuned for the failure mode that dominates the
remaining misses, and no validation protocol fixes a population that is not there.

A dataset job for whoever owns the generator, before the next split.

---

### F4 — `expected_scope`: let a caller demand full coverage

Measured in `results/12_robustness.csv` as a semantic, not a defect. Module A refuses a
lot it cannot prove complete, but a batch that simply *omits* a whole lot is scored —
correctly, since screening one lot is legitimate. The consequence is that Module A
returns one row per component **sent**, and a caller expecting the full release gets
fewer rows with no signal.

**Change:** an optional `expected_scope={lot_id: n}` covering the whole request, so a
caller can ask Module A to refuse a batch that is missing a lot entirely. It is
optional because the current behaviour is right for single-lot screening.

**Why not now:** it adds a field to the runtime contract, which moves
`runtime_contract_digest`, which the hardening phase's own invariant forbids. It is in
the integration note instead so nobody meets it by surprise.

---

### F5 — Unit validation upstream of Module A

`results/12_robustness.csv` records that multiplying every measurement by 1,000 barely
moves the statistical score. That is correct behaviour — a lot-relative robust z is
scale-free — and it means Module A **cannot** catch a unit error. Only the datasheet
witness notices, and only upward.

The fix does not belong in Module A. A unit or range check belongs where measurements
enter the system. Recorded so that nobody assumes Module A covers it.

---

### F6 — Per-parameter evidence with the null properly controlled

The score aggregates a maximum over 24 parameter-epoch values, so a healthy component's
maximum routinely reaches 2.4 z simply by being a maximum over 24 draws — which is
where a genuine 2.3 z static offset disappears. Converting each deviation to a p-value
against its own null, with a multiplicity correction, would make evidence comparable
across defect shapes.

A redesign of the score, so a new release and a new validation, not a patch.

---

### F7 — Re-derive the feature design under the nested protocol

The 60-feature block and the top-k depths are inherited from full-calibration
development. This release re-selected the weights and threshold, where the selection
pressure was, but not the feature design. Significant cost; expected gain small, given
that every aggregation variant tested landed within noise of every other.

---

### F8 — A reviewer-cost model

The whole trade-off is expressed in false alarms per 1,343 components. Nobody has said
what a review costs, so the operating point is a placeholder the team owns. Decision D2
is closed in code and open in substance until someone states a review capacity or a
cost ratio.

---

## Explicitly not worth doing

- **Another ensemble.** Two were built and measured. RC2's residual band does not beat
  lowering the threshold; RC3's specialists reproduce the plain threshold at matched
  workload, agreeing on 66 of 67 detections. A third would need to move PR AUC with an
  interval excluding zero.
- **Grid-searching more algorithms against this holdout.** It is no longer a test set.
- **Tuning a statistical threshold to zero false alarms and calling it a guarantee.**
  It sits at 0.956835 on calibration and catches 38 of 54, and it is a fitted quantity
  on 852 parts. The CONFIRMED tier is the honest version of that idea.
- **Reverting the weights because the holdout preferred the old ones.** Decision D6.
