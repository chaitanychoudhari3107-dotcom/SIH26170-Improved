# External review prompt — Module A

Paste this, plus `docs/VALIDATION_SUMMARY.md`, `docs/MODEL_CARD.md`,
`docs/LIMITATIONS.md` and `docs/DECISION_LOG.md`, into a fresh model. Module B went
through two such rounds; this is the equivalent for Module A.

---

You are reviewing a frozen anomaly-detection release for a student hackathon entry
(SIH 2026, ISRO problem statement 26170: detecting abnormal CMOS components during
burn-in). Your job is to find what is wrong, overstated, or unsupported. Praise is not
useful; a specific objection is.

**Module A** decides whether a component *already looks abnormal* against its variant's
normal references and the other components in its own lot. It emits a score, PASS or
MONITOR, and its evidence. Module B forecasts 168 h values from 0 h and 24 h. Fusion
owns the final PASS/MONITOR/REJECT.

**Please attack these specifically:**

1. **The zero-false-positive claim.** A "CONFIRMED" tier fires when a measured value
   exceeds its datasheet `static_spec_max`. Across all 5,400 components it fired 81
   times and every one was a labelled anomaly. The release states this as "no observed
   false positive in 5,076 normals, 95% upper bound 0.06%" and never as "never wrong".
   Is that framing right? Is there a way this tier is circular — could the data
   generator have *defined* out-of-spec parts as anomalous, making this tautological
   rather than predictive? If so, what does that do to its value at integration?

2. **The weight decision.** Twelve leave-one-lot-out folds each independently selected
   pure `lot_relative` weighting over the inherited 0.90/0.10. The release adopts it for
   simplicity while stating the performance difference is a tie (PR AUC +0.0008, 95% CI
   [−0.0081, +0.0171]) — and then reports that on the holdout the new weights did
   slightly *worse* (PR AUC 0.8166 vs 0.8239) and did **not** revert. Is refusing to
   revert correct, or is it rigidity dressed as discipline?

3. **The operating point.** 1% calibration false-alarm budget, chosen at the curve's
   knee: 47 of 54 at 8 false alarms, versus 48 of 54 at 24 at the 3% budget. The team
   prioritises not missing defects. Is one anomaly for sixteen false alarms obviously
   the wrong trade, or is that a judgement the release should not have made on the
   team's behalf?

4. **The blind spot.** Static offsets that stay inside spec are detected 6 of 21, while
   those that fail spec are 7 of 7. The release argues this is a ceiling of within-lot
   statistics — nine statistics from five families all land at 4–7 of 18 — rather than
   a deficiency of this candidate. Is that argument sound, or is it a convenient way to
   stop trying? What would you try that is not in that list?

5. **The nested validation.** Outer leave-one-lot-out over 12 lots; inner
   leave-one-lot-out over the 11 training lots selects weights and threshold. The
   feature design and the top-k aggregation depths are still inherited from
   full-calibration development. How much optimism does that leave, and is
   "48 of 54 at 25 false alarms" defensible as the headline?

6. **Module B corroboration.** Where Module B's reason codes name the same parameter
   Module A flagged, 19 of 19 holdout components are real anomalies. The release records
   the association and refuses to make it a rule, because the only data where both exist
   is the holdout. Is that the right call, and is there a leakage-free way to use it that
   has been missed?

**Ground rules for your reply:**

- You have not run the code and cannot see the data. Say when you are speculating.
- Sort each point into **accept / reject / needs data** yourself if you can.
- A suggestion that requires reopening the freeze, regenerating the dataset, or using
  the holdout for selection will be rejected on that ground — propose it only if you
  think the ground itself is wrong, and say why.
- Small numbers matter here: 54 calibration anomalies, 90 holdout anomalies. Do not
  recommend a change on a one-or-two-component difference.
