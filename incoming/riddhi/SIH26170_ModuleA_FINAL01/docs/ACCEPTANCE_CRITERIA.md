# Acceptance criteria — ModuleA-FINAL01

Declared so that "ready" is a check, not an opinion. Every line is verified by a script
and its result is in `results/10_verify_claims.csv`.

## A · The model does what it says

| # | Criterion | How it is checked | State |
|---|---|---|---|
| A1 | Dataset identity matches the frozen release | three SHA-256 values, stage 00 | ✅ |
| A2 | The reimplemented core reproduces the inherited one exactly | `tests/test_equivalence.py` | ✅ |
| A3 | Performance is estimated with the configuration selected inside the fold, at the shipped budget | stage 04, nested leave-one-lot-out | ✅ 45/54 at 9 FP |
| A4 | No comparison is reported as a win when its interval contains zero | two reported as ties | ✅ |
| A5 | The holdout is opened once, after freeze, by one gated script | stage 08, receipt | ✅ spent |

## B · The output is safe to consume

| # | Criterion | How it is checked | State |
|---|---|---|---|
| B1 | One threshold on `module_a_score` reproduces `module_a_disposition` | `contract.validate_output`, every emitted frame | ✅ |
| B2 | A frame where it does not is refused before it leaves | `tests/test_tiers.py` reproduces the RC2 defect | ✅ |
| B3 | Module A never emits REJECT | contract validator, freeze preflight | ✅ |
| B4 | The five contract fields come first, in the release's order | `tests/test_contract.py` | ✅ |
| B5 | A perfect statistical score cannot enter the out-of-spec band | `tests/test_score_semantics.py` | ✅ fixed in hardening |
| B6 | Attribution ships with its margin and is blank where it is noise | `tests/test_reason_codes.py` | ✅ |

## C · Failure is loud

| # | Criterion | How it is checked | State |
|---|---|---|---|
| C1 | A lot that cannot be proved complete is refused | stage 12, `tests/test_guards.py` | ✅ |
| C2 | A batch counting *itself* as complete is still refused | `tests/test_guards.py` | ✅ |
| C3 | An unknown variant raises rather than borrowing a reference | stage 12 | ✅ |
| C4 | Null, non-numeric, zero and negative measurements raise | stage 12, 4 cases | ✅ |
| C5 | A degenerate reference scale raises rather than scoring as normal | `tests/test_reference.py` | ✅ |
| C6 | A ground-truth column reaching a scoring frame raises | `tests/test_guards.py` | ✅ |
| C7 | A future-epoch column cannot influence an earlier score | poisoning test, 1e6 into a 168 h column | ✅ |

## D · The interface is self-describing

| # | Criterion | How it is checked | State |
|---|---|---|---|
| D1 | The runtime contract has its own digest | stage 17 | ✅ |
| D2 | A worked serving example ships — input and output | stage 18 | ✅ |
| D3 | The join to Module B is performed and recorded, not assumed | stage 15, 9 checks | ✅ 1,343 rows |
| D4 | The score's meaning, and what it is not, is measured | stage 13 | ✅ |
| D5 | Robustness is measured, including where it is weak | stage 12, 19 cases | ✅ |
| D6 | Every packet carries the same `RELEASE_IDENTITY.json` | stage 18 | ✅ |

## E · The evidence is checkable

| # | Criterion | How it is checked | State |
|---|---|---|---|
| E1 | Every figure quoted in `docs/` traces to a file in `results/` | stage 10 | ✅ 151 checks |
| E2 | Every figure checked also appears in a document | stage 10, reverse direction | ✅ |
| E3 | The test suite passes and its count is recorded | `RELEASE_MANIFEST.json` | ✅ 79 tests |
| E7 | A documented figure measured at one budget is never quoted against another | stage 10 | ✅ caught and fixed once |
| E4 | Predictions are hashed when written and re-verified before scoring | stages 08 and 09 | ✅ |
| E5 | Post-freeze source changes are enumerated and explained | `PROVENANCE_ADDENDUM.json` | ✅ 1 explained |
| E6 | An interrupted session can resume from a file | `state/CHECKPOINT.json` | ✅ |
| E8 | Two independent runs produce byte-identical analysis outputs | stage 19 | ✅ 44 of 44 |
| E9 | Every packet verifies against its own checksums and carries the same model digest | stage 10 `--with-packets` | ✅ 6 of 6 |
| E10 | Packet archives are byte-deterministic | fixed zip timestamps | ✅ |
| E11 | All four confusion-matrix cells reported for every result | stage 20 | ✅ 10 matrices |
| E12 | Every matrix balances and agrees with sklearn | stage 20, every run | ✅ |
| E13 | The confusion implementation is pinned by orientation, not only arithmetic | `tests/test_confusion_matrix.py` | ✅ 72 tests |
| E14 | Accuracy is never quoted as a headline | stage 10 | ✅ |

## F · Honesty

| # | Criterion | State |
|---|---|---|
| F1 | The zero-false-positive claim is stated with an upper bound, never as "never" | ✅ 0.06% |
| F2 | The result that went the wrong way is reported at the same volume | ✅ VALIDATION_SUMMARY §7 |
| F3 | A falsified hypothesis is written up as falsified | ✅ H1, IMPROVEMENTS |
| F4 | The blind spot is named by mechanism, not by label | ✅ within-spec static offsets |
| F5 | Everything found and not fixed is listed with why | ✅ FUTURE_RELEASE_ITEMS |

## Not met, and not claimed

- **An independent test set.** Every holdout number is diagnostic. F2 in
  `docs/FUTURE_RELEASE_ITEMS.md`.
- **Calibrated probabilities.** The score is monotone, not calibrated. Measured.
- **Detection of within-spec static offsets.** 6 of 21. Measured, and established as a
  ceiling across nine statistics rather than a deficiency of this candidate.
- **Real-silicon validity.** Synthetic data throughout.
