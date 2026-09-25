# Module A · final delivery envelope

**Model** `ModuleA-FINAL01` · **package** `final01.5.0` ·
dataset `SIH26170-FINAL-01` · state **HOLDOUT_PREDICTION_DELIVERED**
**Model digest** `2b2fa4da5ee36e7c…` ·
**runtime digest** `d73ea59a16361e23…`
**Holdout run** SPENT · **build mismatch** False

Six packets, one per person. Each is self-contained: its own letter, its own
`SHA256SUMS.txt`, and the same `RELEASE_IDENTITY.json`. **If two packets disagree on
`model_config` or `runtime_contract`, one is from a different build and must not be
used.**

## Who gets what

| For | Role | File | Bytes | SHA-256 |
|---|---|---|---:|---|
| **Anushka** | integration lead | `SIH26170_FINAL_Anushka_ModuleA_Packet.zip` | 174,891 | `bdf743b74f1bb225…` |
| **Sanskruti** | evaluation | `SIH26170_FINAL_Sanskruti_ModuleA_Packet.zip` | 202,457 | `72ef5d8fb66ff6a1…` |
| **Chaitany** | data | `SIH26170_FINAL_Chaitany_ModuleA_Packet.zip` | 44,607 | `9b2481618563944c…` |
| **Tanisha** | domain and standards | `SIH26170_FINAL_Tanisha_ModuleA_Packet.zip` | 44,059 | `453ebf7e78909497…` |
| **Riddhi** | Module A history | `SIH26170_FINAL_Riddhi_ModuleA_Packet.zip` | 54,755 | `6c5a9de3f4564531…` |
| **Nirmik** | owner | `SIH26170_FINAL_Nirmik_ModuleA_Packet.zip` | 804,734 | `8233b9bd1343c8cd…` |

**Anushka** — Threshold module_a_score at the published floor and you have reproduced Module A's decision exactly. The join to Module B is already done and checked.

**Sanskruti** — 166 claim checks, each naming the file it verifies. Two independent runs agree byte for byte. Two corrections the machinery caught are documented.

**Chaitany** — Two dataset findings: the train split is not anomaly-free, and calibration and holdout are composed very differently for one defect class. One concrete ask for the next split.

**Tanisha** — Please sanity-check the eleven datasheet limits the CONFIRMED tier rests on, and tell me whether a physically justified parameter relationship exists.

**Riddhi** — What measuring Better Potential, RC2 and RC3 under one protocol showed, the six defects and their fixes, and the hypothesis I got wrong.

**Nirmik** — Everything, plus the three decisions that need you: the operating point, calibration-split Module B forecasts, and a fresh test set.

## State of the release

| | |
|---|---|
| tests | 151 passed |
| claim checks | 166, 0 failed |
| reproducibility | 47 of 47 files identical, two independent runs |
| robustness cases | 19, 0 failures |
| confusion matrices | 10 reported, all balance, all cross-checked against sklearn |

## The four outcomes

Every headline here is a view of four integers. Both rows below are the complete matrix.

| result | TP | TN | FP | FN | recall | precision | FPR |
|---|---:|---:|---:|---:|---:|---:|---:|
| calibration, out of fold, shipped config | 47 | 844 | 8 | 7 | 87.0% | 85.5% | 0.94% |
| holdout 168 h — **DIAGNOSTIC** | 65 | 1,240 | 13 | 25 | 72.2% | 83.3% | 1.04% |

**FN is the expensive cell** — 25 real defects passed onward on the holdout.
FP costs review time and harms nobody. Accuracy is deliberately not reported: with 90
anomalies in 1,343 components, flagging nothing would score above 93%.

The datasheet-limit rule, across all 5,400 components in the dataset:
**81 flagged, every one a real anomaly, 0 false
positives in 5,076 healthy components.** The honest form, used
everywhere in these packets: no observed false positive, 95% upper bound on the true
rate 0.06%. Not "never".

## What is not claimed

- **The holdout is not an independent test.** It shaped RC1, RC2, RC3 and this
  release's reporting. Every holdout cell above is a comparison against prior runs.
- **The score is not a probability.** Monotone in the anomaly rate, but the largest gap
  between a band midpoint and its observed rate is 0.75.
- **Within-spec static offsets are largely invisible** — 6 of
  21. Established as a ceiling across nine statistics, not a
  deficiency of this candidate.
- **This is synthetic data.** Nothing here supports a claim about real silicon.

## Verifying a packet

```bash
unzip SIH26170_FINAL_<name>_ModuleA_Packet.zip
cd SIH26170_FINAL_<name>_ModuleA_Packet
sha256sum -c SHA256SUMS.txt
```

Archives are byte-deterministic: two release runs from identical analysis produce
identical zips, so the hashes above are reproducible rather than incidental.
