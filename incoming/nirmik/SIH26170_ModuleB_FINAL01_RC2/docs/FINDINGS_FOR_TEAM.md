# Module B on FINAL-01 — what changed, and the one thing we need to decide

**From:** Nirmik (Module B) · **Date:** 18 Sep 2026 · **Dataset:** SIH26170-FINAL-01
**Status:** benchmarked, calibrated, pre-declared decision executed. **Not frozen.**

Everything below was produced by rerunning the Candidate-V1 configuration
**unchanged**, as decision D5 required. No number in the `FROZEN_V1` block was
touched to make any of this look better.

---

## 1. The file is clean

5,400 rows, 72 lots, 42/12/18 split, 14/14/14 · 4/4/4 · 6/6/6 lots per variant.
Zero nulls, zero duplicate `component_id`, zero non-positive measurements, zero
`96h` columns, no hidden-label columns, no shared lot or component between any
two splits, and the holdout carries no `168h` answers. Row and lot counts match
`Dataset_Version_Safe.json` exactly.

**Nothing to escalate.**

## 2. Three of the five V2 generator changes are visible in the data

| Change | V1 | FINAL-01 | Landed? |
|---|---|---|---|
| 1 — strengthen lot ageing | lot explains 1.3–5.1 % of late-drift variance | **1.2–17.8 %** | **Yes**, unevenly — strongest on `Active_Supply_Current` (11.9–17.8 %) and CMOS_C timing (9.4–17.4 %) |
| 2 — recalibrate `Input_Leakage_Current` early SNR | SNR ~0.7–0.9 | **0.50–0.74** | **No — it moved the wrong way** on this measure |
| 3 — more independent lots | 21 train lots | **42** train lots | **Yes** |
| 4 — clean-lot coverage across variants | uneven | 14 lots per variant, every split balanced | **Yes** |
| 5 — spread the static-fail cases | 5 breaches, all CMOS_C `Propagation_Delay` | **58 breaches across 10 variant × parameter cells** | **Yes** |

Change 2 needs a word. Measured as "median early move ÷ declared noise", input
leakage's early signal got *weaker*, not stronger. But its early→late correlation
improved sharply on two variants (CMOS_A 0.10→0.22, CMOS_C 0.14→0.56) while
CMOS_B stayed at 0.08, and its late drift dispersion is now very large (late SD
18–71 % depending on variant). So the parameter became more *predictable* and
more *volatile* at the same time. That is not a complaint — it is the reason
section 4 exists.

**For Riddhi:** lot *ageing* structure is now real, where in V1 it was not. Your
lot-relative assumptions should behave differently on FINAL-01 than they did on
Candidate V1, and probably better.

## 3. The frozen model got better, and the data is why

The same configuration, the same folds, the same code — only the dataset changed.

| Parameter | V1 verdict | FINAL-01 verdict | MAE gain vs median-ratio | lots won | p |
|---|---|---|---|---|---|
| IDDQ | tie | TIE | +0.4 % | 22/42 | 0.60 |
| Input_Leakage_Current | tie | **BETTER** | +6.8 % | 34/42 | 0.00009 |
| Active_Supply_Current | tie | TIE | +3.9 % | 25/42 | 0.034 |
| Propagation_Delay | better (~10 %) | **BETTER** | +8.9 % | 31/42 | 0.0013 |
| Output_Rise_Time | better (~10 %) | **BETTER** | +8.8 % | 33/42 | 0.00002 |
| Output_Fall_Time | suggestive, failed at 5 % | **BETTER** | +8.4 % | 30/42 | 0.0015 |

**Four of six, up from two.** Note `Active_Supply_Current` at +3.9 % with
p = 0.034: significant, but under the 5 % tie threshold, so it is reported as a
tie. The threshold exists precisely so a p-value cannot promote a small effect.

Comparing effect sizes rather than p-values across versions is deliberate —
FINAL-01 has twice the independent lots, so the p-values are not comparable and
the percentage gains are.

The 24-configuration grid was also run. **Nothing beats the frozen configuration
by more than 4.5 %** on any parameter, which is inside the tie threshold. The
frozen config stands on its own evidence, not on the freeze protocol alone.

## 4. The extrapolation finding — D11 closed 19 Sep, cap stays OFF

On the 12 calibration lots, `Input_Leakage_Current` is **33 % worse** than a
constant median ratio. That reverses the train-CV result, and it is one
component.

```
component C03478   lot B_L23   CMOS_B
  measured   0h   0.51133 µA
  measured  24h   0.69613 µA      early move  +36.1 %
  true      168h  1.04689 µA      true drift  +50.4 %
  forecast  168h  2.05571 µA      predicted   +195.3 %
  absolute error  1.00882 µA   =  27.7 % of the parameter's entire
                                  calibration error, from 1 row of 906
```

Remove that single row and Module B is 1.075× median-ratio — a 7.5 % deficit, which is
outside the 5 % tie band; it was called "a tie" before 19 Sep and that was wrong
(secondary audit S1). Keep the row and
Module B is 1.315× worse.

**Why it happens.** The `Input_Leakage_Current` training target has a very heavy
right tail: the largest relative delta is 13.3×, which is **54× its own 99th
percentile**. No other parameter exceeds 15×. Huber downweights outliers in the
*loss*, but nothing stops the fitted function from returning a drift far outside
anything it should assert when a component's inputs resemble a tail case.

This is **not** a data bug. The training file genuinely contains those
components; the model is extrapolating from real data.

**The proposal.** A hard cap on the predicted relative delta, applied after the
model and before the output contract. Not a retune — the fitted coefficients are
untouched. It is a statement that Module B will not assert a drift larger than
*c*.

| cap | calibration (906 rows) | train OOF (3,151 rows) | `Input_Leakage` calibration MAE | other five parameters |
|---|---|---|---|---|
| none (current) | — | — | 0.00402 | — |
| ±1.00 | 1 capped | 2 capped | 0.00328 (−18 %) | untouched |
| **±0.50** | **1 capped** | **2 capped** | **0.00290 (−28 %)** | **untouched** |
| ±0.25 | 3 capped | 3 capped | 0.00308 (−23 %) | untouched |

*(Denominators corrected 19 Sep, review finding F5. This table previously said
"of 5,400", which silently counted the 1,343 holdout rows that have never been
predicted. Only 4,057 forecasts exist.)*

On the 4,057 forecasts that exist, ±0.50 clips three — one calibration row and two
train-OOF rows, all `Input_Leakage_Current`. It touches nothing else at all. **No
statement is made about the 1,343 holdout rows**, which have not been predicted.

**Two honest caveats.** The cap also limits how alarming Module B can be. On this
very component both the true value (1.047 µA) and the capped forecast
(0.696 × 1.5 = 1.044 µA) still exceed CMOS_B's 1.0 µA limit, so the
`B_FORECAST_EXCEEDS_LIMIT` flag survives — the flag was a **true** positive and
stays one. And the cap is tuned against one component, which is the thinnest
possible evidence; it is defensible as a fail-safe bound, not as an accuracy
improvement.

**DECIDED 19 Sep 2026 — D11 = LEAVE_OFF.** `FORECAST_REL_DELTA_CAP` stays `None`.
Three reasons beyond the two caveats above: the value would be selected after seeing
calibration truth, which is post-hoc pipeline selection and the one pre-declared
calibration decision is spent; the motivating case is a true positive with an
exaggerated magnitude, not a false alarm; and **no independently-justified cap is also
effective** — a bound taken from the training target distribution sits at p99.9 = 7.81
or max = 13.32, both far above the offending +1.95 forecast, while the only tight
enough train-derived bound (≈ p99 = 0.247) is inside the range training says is
legitimate and would start clipping timing forecasts too.

The finding stands as a known limitation carried into freeze. Full reasoning in
`docs/DECISION_LOG.md` and guide §13.7.

## 5. The pre-declared fall-time rule did not fire

Declared 14 Sep 2026, before the calibration file existed: move
`Output_Fall_Time` to the `own` feature set iff `own` beats `own+lot+cross` by
> 3 % MAE **and** wins more than half the calibration lots.

Measured: **−1.5 %** MAE (the `own` set is *worse*), **2 of 12 lots**. Neither
condition met. `Output_Fall_Time` keeps `own+lot+cross`. The rule is now spent.

One re-reading, recorded rather than done quietly: the rule said "≥ 4 of 6 lots"
because Candidate V1's calibration file had six. FINAL-01 ships twelve. Applying
"4 lots" literally would have silently weakened the rule from two-thirds of lots
to one-third, so it was applied as the proportion it was written to express:
more than half, ≥ 7 of 12. It fails either way — 2 of 12 does not clear 4 either.

## 6. For Anushka

- **The schema is final.** Six `predicted_*`, six `module_b_p95_*`,
  `module_b_primary_parameter`, `module_b_reason_codes`, plus 24 additive
  `evidence_*` columns. **No `module_b_disposition`**, not even `NOT_SET`.
- **CHANGED 19 Sep — the serving contract is cohort-level.** Send whole lots. A
  request with any lot under 30 rows is refused. A one-component call is not
  equivalent to a full-lot call: timing forecasts move by up to 7.18 % and
  `module_b_primary_parameter` degenerates. This corrects a wrong promise in the
  previous integration note.
- **The p95 envelope is evidence, not a screen.** Marginal coverage is calibrated
  (0.933–0.974 against 0.95). Tail coverage on the worst-drifting decile is
  **0.407–0.769** *(re-measured 19 Sep — it was previously ranked by forecast
  residual rather than observed drift)*. If a fusion rule treats "inside the
  envelope" as a pass, it will fail first on `Output_Rise_Time` at 0.407.
- 14.9 % of components carry any reason code; the most common single code fires
  on 10.9 %. Designed to be a worklist, not wallpaper.
- `docs/INTEGRATION_NOTE.md` has the calling interface, and the predict path is
  tested to be identical whether you send one component or all of them.

## 7. For Tanisha

The seven variant × parameter cells with no `static_spec_max` are unchanged:
`Active_Supply_Current` on all three variants, and `Output_Rise_Time` /
`Output_Fall_Time` on CMOS_B and CMOS_C. Module B invents nothing for them and
simply emits no limit-based evidence there. If any of the seven can be given a
source-backed limit, that directly increases the evidence Module B can supply.

The C4 withdrawal stands: TI's SN74LVC00A gives tpd MIN 1 / TYP 3.5 / MAX 4.1 ns
at 3.3 V ± 0.3 V and 25 °C, so the CMOS_C 3.5 ns baseline is a genuine datasheet
typical and the 5.5 → 4.1 ns limit change was a correction.

## 8. For Chaitany

Nothing to escalate. FINAL-01 passes every structural check. Change 2 did not
land on the SNR measure it was written against (section 2) — reporting it for the
record, **not** as a request to regenerate. FINAL-01 stays frozen.

## 9. What happens next

1. ~~The team decides section 4.~~ **Done 19 Sep — D11 = LEAVE_OFF**, recorded in
   `docs/DECISION_LOG.md`.
2. `python scripts/11_freeze.py --team-signoff "<who, when>"`
3. `python scripts/12_predict_holdout.py --frozen` — once.
4. The output goes to Sanskruti for blind evaluation and to Anushka for
   integration. No retuning afterwards, whatever she reports.
