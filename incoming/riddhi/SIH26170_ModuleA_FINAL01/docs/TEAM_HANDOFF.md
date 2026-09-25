# Module A → the team

**Model** `ModuleA-FINAL01-RC1` · **package** `final01.2.0` · dataset `SIH26170-FINAL-01` · **frozen**, holdout
run **spent**. Model digest `2b2fa4da5ee36e7c…`, runtime digest `d73ea59a16361e23…`.

One page each for the people who need something from Module A.

---

## Anushka — integration

Your packet is `packets/SIH26170_FINAL_Anushka_ModuleA_Integration_Packet.zip`. It has
the contract, the runtime rules, a worked serving call, the frozen holdout output and
the join to Module B already performed.

**The one line that matters:** threshold `module_a_score` at `monitor_floor`
(`0.8455864571`, in `runtime_contract.json`) and you have reproduced Module A's
decision exactly, for every row. Nothing else needs reimplementing.

Four things that will bite if missed, in `README_ANUSHKA.md`: the score is not a
probability; requests carry whole complete lots; a batch missing a whole lot is scored
rather than refused, so check your row count; Module A emits no REJECT.

The join is done, not described — 1,343 rows, nine checks, all passing, against Module
B's real frozen packet.

---

## Sanskruti — evaluation

Everything you need to check the claims independently:

- `results/10_verify_claims.csv` — 130 checks, each naming the file it verifies against.
  Re-run `scripts/10_verify_claims.py` and it should still be 130 of 130.
- `results/HOLDOUT_PREDICTION_RECEIPT.json` — the predictions were hashed when written,
  before any label was opened. `scripts/09_evaluate_holdout.py` re-hashes and refuses to
  score a file that moved.
- `docs/ACCEPTANCE_CRITERIA.md` — what "ready" was declared to mean, and what is
  explicitly **not** met.

The number to scrutinise first is the nested estimate of the shipped configuration,
**45 of 54 at 9 false alarms** (`results/04_nested_validation.csv`, the `shipped` arm).
It is the only Module A figure ever produced with both the weights and the threshold
selected inside the fold, at the budget the release operates at. The four arms in that
file show what each layer of selection was worth.

Worth knowing how that number was corrected: an earlier revision quoted 48 of 54 at 25
false alarms, which came from a 3% budget run while the release ships at 1%. The claim
checker caught it when the stage was re-run. The correction is in `docs/DECISION_LOG.md`
under D3.

The number that is *not* a performance claim is anything on the holdout. It shaped RC1,
RC2, RC3 and this release's reporting.

---

## Chaitany — data

Two findings about `SIH26170-FINAL-01` that are yours rather than the model's.

**The train split is not a "Normal-reference split".** The hidden ground truth records
180 anomalies among its 3,151 components, about 5.7%. Median and MAD survive that
comfortably, and Module A fits without labels anyway, so nothing is broken — but the
handoff's description is wrong and has been corrected everywhere here.

**Calibration and holdout are composed very differently for one defect class.** Of
calibration's 10 static outliers, 6 fail their datasheet spec; of the holdout's 18, 1
does. Detection tracks that flag almost perfectly — 7 of 7 caught where spec fails, 6
of 21 where it does not. So "8 of 10 on calibration, 4 of 18 on holdout" is one
detector at one threshold looking at two different populations, and **nothing selected
on calibration can be tuned for the failure mode that dominates the holdout misses.**

Not a request to regenerate FINAL-01. A request that the next split balance that flag.

---

## Tanisha — domain and standards

Two asks.

**The datasheet limits are carrying real weight.** `static_spec_max` from
`Device_Specs.csv` is the basis of the CONFIRMED tier: 81 flags across 5,400
components, all 81 real anomalies. Please sanity-check the eleven populated cells; the
seven empty ones stay empty and the rule never fires there.

**Is there a physically justified relationship between parameters?** The remaining
misses are components individually within spec and individually unremarkable against
their lot. An unconstrained multivariate distance was tried and did not help. A
relationship physics fixes — IDDQ against Active_Supply_Current, rise against fall time
— would be a genuinely independent witness. A ratio nobody can justify is just another
fitted threshold, so this needs you rather than more search.

---

## Riddhi — Module A history

Better Potential, RC2 Hybrid and RC3 Specialist are preserved and still runnable as
shipped. Measured under one protocol: RC2's residual band does not beat simply lowering
the threshold (paired lot bootstrap, ΔTP interval contains zero at every budget), and at
matched workload the plain core score equals RC3 exactly — agreeing on 66 of 67
detections. Neither add-on is carried forward, and `docs/DECISION_LOG.md` D10 records
what would reopen that.

The core formula itself survives intact. `tests/test_equivalence.py` asserts the
rewritten path reproduces it bit for bit.

---

## Nirmik — what needs a decision

1. **The operating point.** Frozen at a 1% calibration false-alarm budget, at the
   curve's knee. Moving to 3% buys one more anomaly of 54 and costs sixteen more false
   alarms. It is a config edit and a re-freeze, not a retrain. Decision D2 is closed in
   code and open in substance until someone states a review capacity.
2. **Calibration-split Module B forecasts.** F1 in `docs/FUTURE_RELEASE_ITEMS.md`, and
   the highest-value item open. B corroboration is 19 of 19 on the holdout and cannot be
   used until it can be fitted without leakage. You own both modules, so this is one
   decision and one prediction run.
3. **A fresh lot-grouped test set.** Until it exists, nothing here should be presented
   as a performance claim to judges.
