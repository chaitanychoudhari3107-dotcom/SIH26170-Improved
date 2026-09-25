"""The six role-scoped letters. Every figure is interpolated from results/, never typed.

A letter that quotes a number by hand is a number that will drift from the evidence the
moment anything is re-run. Each function takes the facts dictionary the packet builder
assembles from results/ and returns markdown.
"""
from __future__ import annotations


def _header(name: str, role: str, f: dict) -> str:
    return f"""# Module A → {name} · {role}

**Model** `{f['model']}` · **package** `{f['package']}` · dataset `{f['dataset']}` ·
state **{f['state']}**
**Model digest** `{f['config_digest'][:16]}…` · **runtime digest** `{f['runtime_digest'][:16]}…` ·
**source digest** `{f['source_digest'][:16]}…` (at freeze `{f['freeze_source_digest'][:16]}…`)
**Sign-off** RECORDED · **holdout run** SPENT · **build mismatch** {f['build_mismatch']}

All six packets carry the same `RELEASE_IDENTITY.json`. If two disagree on
**model_config** or **runtime_contract**, one is from a different build and must not be
used. `source_tree` moving on its own is explained in `PROVENANCE_ADDENDUM.json`.

"""


def anushka(f: dict) -> str:
    return _header("Anushka", "integration", f) + f"""## What you need to do

Threshold `module_a_score` at **{f['monitor_floor']:.10f}** — `monitor_floor` in
`contract/runtime_contract.json`. That reproduces `module_a_disposition` exactly, for
every row. Nothing else needs reimplementing.

## What is in here

| Path | What it is |
|---|---|
| `contract/ModuleA_Output_Contract.csv` | the exact output header |
| `contract/runtime_contract.json` | serving rules, the published floor, score bands, what is refused |
| `contract/Schema_Data_Dictionary.csv` | the meaning of every column |
| `contract/Device_Specs.csv` | units, reference values, the eleven available static limits |
| `example/input_one_complete_lot.csv` | a worked serving call — what goes in |
| `example/output_one_complete_lot.csv` | …and exactly what comes back |
| `example/fusion_joined_example_60_rows.csv` | Module A joined to Module B — the frame you start from |
| `example/fusion_join_checks.csv` | the {f['fusion_checks']} join checks, all passing |
| **`prediction/ModuleA_Final_Holdout_168h.csv`** | **the frozen output fusion consumes — 1,343 rows** |
| `prediction/ModuleA_Final_Holdout_0h/24h/96h.csv` | the same components at earlier epochs |
| `prediction/HOLDOUT_PREDICTION_RECEIPT.json` | input hash, output hashes, digests, sign-off |
| `docs/INTEGRATION_NOTE.md` | the full interface note |

## Four things that will bite if they are missed

**1 · The score is not a probability.** It is monotone in the anomaly rate — every band
up, the observed rate rises — but the largest gap between a band's midpoint and its
observed rate is {f['probability_gap']:.2f}. A score of 0.7 does not mean 70%. Do not
display it to a user as a percentage.

**2 · Requests carry whole, complete lots.** Module A compares a component to the others
in its lot, so a partial lot gives a wrong reference — wrong, not approximate.
Completeness is proved against external lot sizes; a row count is not a proof. A short
lot is refused. **A batch missing a whole lot is scored, not refused** — screening one
lot is legitimate — so Module A returns one row per component you *send*, and checking
you got the coverage you expected is yours.

**3 · Module A emits no REJECT.** PASS and MONITOR only. The final disposition is yours.

**4 · A unit error is invisible to the statistical score.** A lot-relative robust z is
scale-free by construction, so if every reading arrives 1000x too large the statistical
tier barely moves. Only the datasheet witness notices, and only upward. Unit validation
belongs upstream of Module A.

## The tier you can lean on

`module_a_evidence_tier == "CONFIRMED"` means the part exceeds its own datasheet
`static_spec_max`. Across all 5,400 components this fired {f['spec_flags']} times and
**every one was a real anomaly** — {f['spec_fp']} false positives in
{f['spec_normals']:,} normal components. Not a fitted threshold, so nothing to overfit.

Still bounded, not absolute: the 95% upper bound on the true rate is
**{f['spec_bound']:.2%}**. Please do not write "never" in the dashboard.

`MONITOR` is statistical evidence and is not zero-false-positive.

## The join, already done

{f['fusion_rows']:,} rows against `ModuleB-FINAL01-RC2`'s frozen packet,
{f['fusion_checks']} checks, all passing: no duplicate ids either side, full coverage
both ways, no column collision beyond `component_id`, Module A emits no REJECT and
Module B emits no disposition.

**`b_evidence_status` is a view, not a rule.** Where Module B's reason codes name the
same parameter Module A flagged, {f['corroborated']} components are corroborated and on
the holdout every one is a real anomaly. That association is real and **cannot be a
decision rule yet** — the only data where both modules and the labels exist is the
holdout, so a policy fitted there would be fitted on the labels it would be judged
against. Making it usable needs calibration-split Module B forecasts; it is F1 in
`docs/FUTURE_RELEASE_ITEMS.md` and the highest-value cross-module item open.

The two modules name the same primary parameter on only a small minority of components.
Expected: A names where a deviation is already *observed*, B where drift is *forecast*.
Agreement is corroboration; disagreement is two pieces of evidence, not a contradiction.

## What Module A does not do

It does not forecast, decide, or identify root cause.
`module_a_primary_parameter` ships with `module_a_attribution_margin` — the gap to the
runner-up. A margin near zero is a coin toss. Both are blank on PASS rows, deliberately.

Please read `docs/LIMITATIONS.md` section 1 before writing UI copy about static outliers.
"""


def sanskruti(f: dict) -> str:
    return _header("Sanskruti", "evaluation", f) + f"""## What to check first

**{f['claims']} claim checks**, each naming the file it verifies against. Re-run
`scripts/10_verify_claims.py` from the full release and it should still be
{f['claims']} of {f['claims']}. A single failure means a document and `results/`
disagree, and the document is wrong.

**The number to scrutinise:** the nested estimate of the shipped configuration,
**{f['nested_tp']} of 54 anomalies at {f['nested_fp']} false alarms** (recall
{f['nested_recall']:.1%}, FPR {f['nested_fpr']:.2%}) — `04_nested_validation.csv`, the
`shipped` arm. Weights *and* threshold selected inside each of 12 leave-one-lot-out
folds, at the 1% budget the release operates at. The before-state under the same
protocol is {f['inherited_tp']} of 54 at {f['inherited_fp']}.

No previous Module A candidate reported a number with the selection inside the fold.

## Two corrections you should know were made

Both were caught by the verification machinery rather than by review, and both are in
`docs/DECISION_LOG.md`.

1. **A headline quoted from the wrong budget.** An earlier revision reported 48 of 54 at
   25 false alarms — a 3% run, while the release ships at 1%. Corrected to
   {f['nested_tp']} of 54 at {f['nested_fp']}.
2. **A weight-unanimity claim that was budget-dependent.** "All 12 folds chose pure
   `lot_relative`" holds at 3%; at the shipped 1% the folds split 6/6. What *is* robust:
   across all 24 fold-selections, **no fold chose the inherited `overall_extreme`**.

## Reproducibility

Two independent runs from separate clean extractions produce
**{f['repro_identical']} of {f['repro_total']} analysis outputs byte-identical**
(`verification/19_reproducibility.csv`). The protocol is
`docs/MASTER_PROMPT_FINAL_VERIFICATION.md` and you can re-run it yourself.

Getting there found two defects worth knowing as failure shapes: a results file
recording wall-clock time so no two runs could ever match, and a pipeline that could not
run on a cleared `results/` because it read a gated stage's one-shot output from there.

## What is NOT a performance claim

Everything on the holdout. It shaped RC1, RC2, RC3 and this release's reporting.
`docs/ACCEPTANCE_CRITERIA.md` has a section headed "Not met, and not claimed" — a fresh
lot-grouped test set is F2 in `docs/FUTURE_RELEASE_ITEMS.md` and is the only thing that
would turn any of this into a claim.

## Evidence trail

Predictions were written and hashed by stage 08 **before any label was opened**.
`scripts/09_evaluate_holdout.py` re-hashes them and refuses to score a file that moved.
The hashes are in `prediction/HOLDOUT_PREDICTION_RECEIPT.json`.
"""


def chaitany(f: dict) -> str:
    return _header("Chaitany", "data", f) + f"""Two findings about `SIH26170-FINAL-01` that belong to the dataset rather than the model.
Neither is a request to regenerate FINAL-01, which stays frozen.

## 1 · The train split is not a "Normal-reference split"

The handoff describes it that way. The hidden ground truth records **180 anomalies among
its 3,151 components**, about 5.7%.

Nothing is broken by it — Module A fits its reference without labels, and median and MAD
have a 50% breakdown point, so 5.7% contamination does not move them materially. But the
description is wrong and has been corrected everywhere in this release.

Detectable without opening a label: {f['train_spec_violations']} train components exceed
a datasheet `static_spec_max`, which is only possible if the split is not anomaly-free.

## 2 · Calibration and holdout are composed very differently for one defect class

This one matters.

| | calibration | holdout |
|---|---:|---:|
| static outliers that **fail** spec | 6 of 10 | 1 of 18 |
| static outliers rated SUBTLE | 3 of 10 | 10 of 18 |

Detection tracks that flag almost perfectly: **7 of 7** caught where spec fails,
**{f['within_detected']} of {f['within_actual']}** where it does not.

So the published "8 of 10 on calibration, 4 of 18 on holdout" is one detector at one
threshold looking at two different populations — not a model that degrades.

**The consequence is the ask.** Nothing selected on calibration can be tuned for
within-spec static offsets, because calibration contains four of them against the
holdout's seventeen. No validation protocol fixes a population that is not there.

**Request:** balance `static_fail_target` across splits in the next dataset version. Same
generator, new seeds — F3 in `docs/FUTURE_RELEASE_ITEMS.md`.

## What is in here

`data_findings/` holds `01_audit.json`, `02_spec_witness.csv`,
`05_static_composition.csv` and `05_blindspot.csv`; `docs/LIMITATIONS.md` sections 1–2
has the reasoning.
"""


def tanisha(f: dict) -> str:
    return _header("Tanisha", "domain and standards", f) + f"""Two asks, both needing domain judgement rather than more searching.

## 1 · Please sanity-check the datasheet limits

`Device_Specs.csv`'s `static_spec_max` is carrying real weight in this release. It is
the basis of the **CONFIRMED** tier: across all 5,400 components the rule fired
{f['spec_flags']} times and **every one was a real anomaly** — {f['spec_fp']} false
positives in {f['spec_normals']:,} normals, 95% upper bound {f['spec_bound']:.2%}.

Eleven of eighteen variant x parameter cells have a limit. **The seven empty ones stay
empty** — no interpolation, no borrowing from a neighbouring variant, no derivation from
the data — and the rule simply never fires on those parameters:

- `Active_Supply_Current` — no limit for any variant
- `Output_Rise_Time`, `Output_Fall_Time` — no limit for CMOS_B or CMOS_C

If any of the eleven populated values is wrong, a real defect gets certified on a wrong
basis, or a real one is missed. That is worth twenty minutes of your time.

## 2 · Is there a physically justified relationship between parameters?

This is the open technical question and I cannot answer it without you.

The components Module A misses are individually **within spec** and individually
unremarkable against their own lot — {f['within_detected']} of {f['within_actual']}
within-spec static offsets are caught. Nine statistics from five families all land in
the same place, so the evidence is genuinely below the noise floor of comparing a
component to its lot.

What has **not** been tried is whether those parts violate a *relationship* that physics
fixes, rather than a marginal distribution: IDDQ against `Active_Supply_Current`, or rise
time against fall time. An unconstrained multivariate distance was tried (robust
within-lot Mahalanobis) and did not help.

The reason this needs you: a ratio nobody can justify is just another fitted threshold,
and this release has been careful not to add any. A relationship you can point to a
physical reason for would be a genuinely independent witness — the second one after the
datasheet limits.

## What is in here

`domain/` holds `Device_Specs.csv`, `02_spec_witness.csv`, `02_spec_coverage.csv`,
`05_blindspot.csv` and `14_per_severity.csv`; `docs/LIMITATIONS.md` has the reasoning.
"""


def riddhi(f: dict) -> str:
    return _header("Riddhi", "Module A history", f) + f"""Your three packages — Better Potential, RC2 Hybrid, RC3 Specialist — are preserved and
still runnable exactly as shipped. Nothing was modified. This is what measuring them
under one protocol showed.

## The core survives; the add-ons do not

**Better Potential's scoring formula is the release.** The rewritten path reproduces it
bit for bit under the inherited weights — `tests/test_equivalence.py` asserts a maximum
absolute difference of 0.0 and refuses to run if that ever stops being true.

What changed is narrower than it looks: the aggregation depths are named parameters
instead of slice literals, the reference scales refuse a degenerate MAD instead of
scoring it as `z = 0`, and the component weights were re-selected under a nested
protocol.

## The structural finding

RC2's and RC3's `core_score` columns are **bit-identical to each other**, and Better
Potential's 73 flags are a **strict subset of both**. All three were one detector plus a
different bolt-on — not three candidates.

Measured at matched review workload on the holdout:

- at 78 flags the plain core score gives 67 TP / 11 FP; **RC3 gives 67 TP / 11 FP**, and
  the two flag sets agree on 66 of 67 anomalies;
- at 125 flags the plain core gives 72 TP / 53 FP; **RC2 gives 71 TP / 54 FP**;
- the plain core score *ranks* better than RC2's combined score — PR AUC 0.8239 against
  0.8000, from RC2's own report.

Under a nested lot-grouped protocol at matched budget, the paired lot bootstrap puts
RC2's band against simply lowering the threshold at 0 to +2 true positives, with a 95%
interval spanning zero at every budget.

## The six defects, and what happened to each

| | defect | fixed by |
|---|---|---|
| C1 | RC2's score not monotone with its own disposition — 54 PASS rows above the weakest REVIEW | one monotone score with a reserved band; the validator refuses a frame where a single threshold fails to reproduce the decision |
| C2 | threshold selected out-of-fold, applied to a model refit on all data | no residual model exists |
| C3 | zero reference MAD scored as `z = 0`, i.e. perfectly normal | declared ladder MAD, IQR, std, then raise. Dormant on this data: 0 of 180 references affected |
| C4 | a zero-weight component named as the reason for a flag | reasons built only from weighted components |
| C5 | attribution unstable — two methods agreed on 81% of the same 73 components | `module_a_attribution_margin` ships alongside |
| C6 | weights and cutoff selected on the full calibration set | both re-selected inside each fold |

## What I got wrong, for the record

I proposed that static outliers were being averaged away by the top-k aggregation
(hypothesis H1). It looked convincing on calibration — PR AUC +0.0196, interval
excluding zero — and **evaporated on the holdout**: static detection is flat at 6–7 of 18
for every k from 1 to 12. Written up as a falsification in `docs/IMPROVEMENTS.md`, because
a hypothesis that survives only on the split lacking the hard cases is how a false claim
gets made.

## What is in here

`docs/DECISION_LOG.md` (D10 records what would reopen the RC2/RC3 question),
`VALIDATION_SUMMARY.md`, `IMPROVEMENTS.md`, `MODEL_CARD.md`, and the comparison results.
"""


def nirmik(f: dict) -> str:
    return _header("Nirmik", "owner · full release custody", f) + f"""Everything, plus the three things that need a decision from you.

## Three decisions

**1 · The operating point.** Frozen at a 1% calibration false-alarm budget, chosen at the
curve's knee. Moving to 3% buys one more anomaly of 54 and costs sixteen more false
alarms. This is a config edit and a re-freeze, not a retrain — the score is unchanged and
the whole curve is already measured (`03_operating_points.csv`). Decision D2 is closed in
code and **open in substance** until someone states a review capacity or a cost ratio.

**2 · Calibration-split Module B forecasts.** The highest-value item open, and you own
both modules so it is one decision. Where Module B corroborates Module A on the same
parameter, {f['corroborated']} of {f['corroborated']} holdout components are real
anomalies, against a much lower rate without. Unusable today: the only data with both
modules and labels is the holdout. One prediction run of a model that already exists
makes it fittable. F1 in `docs/FUTURE_RELEASE_ITEMS.md`.

**3 · A fresh lot-grouped test set.** Until it exists, nothing here should be presented
to judges as a performance claim. F2.

## State

| | |
|---|---:|
| tests | {f['tests']} |
| claim checks | {f['claims']}, 0 failed |
| reproducibility | {f['repro_identical']} of {f['repro_total']} files identical across two independent runs |
| robustness cases | {f['robustness_cases']}, 0 failures |
| config digest | unchanged since freeze |
| holdout run | SPENT |

Shipped nested estimate: **{f['nested_tp']} of 54 at {f['nested_fp']} false alarms**.
Holdout at 168 h: **{f['holdout_tp']} TP, {f['holdout_fp']} FP, {f['holdout_fn']} FN**,
{f['holdout_flagged']} flagged, of which {f['confirmed']} CONFIRMED with zero normals.

## What is in here

The complete release, all six packets, and the three master prompts. `CONTINUATION.md`
and `state/CHECKPOINT.json` mean any session can resume this work without conversation
history.

`docs/MASTER_PROMPT_FINAL_VERIFICATION.md` is the protocol for the two independent
re-runs. It has already been executed once and the result is in
`results/19_reproducibility.csv`.

## The two things I would not let pass without saying

**The weight change did not transfer to the holdout.** The frozen configuration ranks
slightly *worse* there than the weights it replaced — PR AUC 0.8166 against 0.8239, one
to two fewer true positives at matched workload. Inside the noise the calibration
bootstrap described, and deliberately not reverted (D6), because a configuration chosen
before the holdout was seen cannot be rewritten by it without making every other number
unverifiable.

**The blind spot is a ceiling, not a to-do.** Within-spec static offsets are caught
{f['within_detected']} of {f['within_actual']}. Nine statistics from five families all
land in the same place. Catching them needs different evidence — Tanisha's physical
relationship, tighter measurement, or an accepted higher false-alarm rate — not another
classifier.
"""


def start_here(name: str, role: str, one_line: str, do: list, dont: list,
               f: dict) -> str:
    """The plain-words page. No jargon, no cross-references to other packets."""
    do_lines = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(do))
    dont_lines = "\n".join(f"  - {d}" for d in dont)
    return f"""SIH 26170 - MODULE A - YOUR ENVELOPE
{"=" * 60}

Hello {name}. You are the {role} on this.

WHAT MODULE A IS, IN ONE PARAGRAPH
Components are baked at high temperature for a week (that is the "burn-in"),
and measured at 0, 24, 96 and 168 hours. Module A looks at those measurements
and says whether a component ALREADY looks wrong - compared to normal parts of
the same type, and compared to the other parts in its own manufacturing lot.
It does not predict the future; that is Module B. It does not make the final
call; that is fusion. It says PASS or MONITOR and shows its reasoning.

WHY YOU ARE GETTING A FILE
{one_line}

WHAT IS IN HERE
  START_HERE.txt        this page
  README_{name.upper()}.md{" " * max(1, 14 - len(name))}your letter - the detail, with the numbers
  RELEASE_IDENTITY.json what exactly this is, so two copies can be compared
  SHA256SUMS.txt        checksums, so you can prove nothing was altered
  docs/                 the model card and the honest list of limitations
  evidence/             the numbers behind every claim in your letter

  Plus the folders your role needs. Your letter walks through them.

WHAT TO DO
{do_lines}

WHAT NOT TO DO
{dont_lines}

THE ONE NUMBER EVERYONE SHOULD KNOW
Out of 1,343 components in the final test, Module A flagged
{f['holdout_flagged']}. Of those, {f['holdout_tp']} really were faulty and
{f['holdout_fp']} were healthy parts that will cost somebody review time.
It missed {f['holdout_fn']} faulty parts. Those {f['holdout_fn']} misses are
the expensive number - a missed fault carries on down the line - and nobody on
this team should quote the good numbers without them.

IF SOMETHING LOOKS WRONG
Say so. Every number in here traces to a file you have been given, and if one
of them does not add up, that is worth more than a polite nod.

  - Nirmik owns Module A. Questions go to him.
{"=" * 60}
"""


START_HERE = {
    "Anushka": ("integration lead",
                "You are wiring Module A into fusion. This is everything you need to\n"
                "consume it, and nothing about how it was built - you should never have\n"
                "to read its internals.",
                ["Read your letter. The four warnings in it are the ones that bite.",
                 "Open example/output_one_complete_lot.csv - that is the shape you get.",
                 "Threshold the module_a_score column at the number in your letter.",
                 "Check example/fusion_joined_example_60_rows.csv - the join to Module "
                 "B is already done and checked."],
                ["Do not re-derive the decision from the other columns. One threshold "
                 "on one column reproduces it exactly.",
                 "Do not show module_a_score to a user as a percentage. It is not one.",
                 "Do not send partial lots. Module A will refuse them, on purpose."]),
    "Sanskruti": ("evaluator",
                  "You check whether the claims are true. This is the evidence, the\n"
                  "checks that were run, and the two corrections the checks caught.",
                  ["Read your letter, then open evidence/10_verify_claims.csv.",
                   "Look at evidence/20_confusion_matrices.csv - all four outcomes for "
                   "every result quoted anywhere.",
                   "Check the two corrections described in your letter. They were "
                   "caught by machinery, not by review, and they are worth your "
                   "scepticism.",
                   "Try to break a claim. That is the job."],
                  ["Do not treat any holdout number as proof the model generalises. It "
                   "is a comparison against earlier runs, and your letter says why.",
                   "Do not accept a recall figure without its false-alarm count. They "
                   "are one measurement, not two."]),
    "Chaitany": ("data owner",
                 "Two things about the dataset turned out to be different from what the\n"
                 "handover said. Neither is your mistake and neither breaks anything -\n"
                 "but the next dataset version should know about both.",
                 ["Read your letter. It is two findings and one request.",
                  "Open data_findings/05_static_composition.csv - it shows the split "
                  "imbalance in one small table.",
                  "Decide whether the next split should balance it."],
                 ["Do not regenerate SIH26170-FINAL-01. It is frozen and everything "
                  "here is measured against it.",
                  "Do not read this as a complaint. The dataset did its job; these are "
                  "notes for the next one."]),
    "Tanisha": ("domain and standards",
                "Two questions only you can answer. One is a twenty-minute check; the\n"
                "other is the open technical problem on this module.",
                ["Read your letter - it is two asks.",
                 "Check the eleven datasheet limits in domain/Device_Specs.csv. A whole "
                 "tier of Module A rests on them being right.",
                 "Tell us whether a physically justified relationship between two "
                 "parameters exists - your letter explains why it matters."],
                ["Do not fill in the seven empty limit cells to be helpful. An invented "
                 "limit is worse than no limit, and the code deliberately never fires "
                 "where one is missing."]),
    "Riddhi": ("Module A history",
               "Your three packages were measured under one protocol. The core survived\n"
               "and is what ships; the two add-ons did not. This is what the numbers\n"
               "showed, stated plainly.",
               ["Read your letter. The structural finding is the interesting part.",
                "Open comparison/04_nested_validation.csv for the honest estimate.",
                "Note the hypothesis I got wrong, and why - it is in your letter."],
               ["Do not read this as your work being discarded. Better Potential's "
                "formula IS the release; there is a test asserting it is reproduced "
                "bit for bit.",
                "Do not re-run the old packages against the holdout to compare. It is "
                "no longer a test set."]),
    "Nirmik": ("owner",
               "Everything, plus the three decisions that are yours and nobody else's.",
               ["Read your letter - the three decisions are at the top.",
                "Hand the other five envelopes out. Nobody needs more than their own.",
                "Decide the operating point, or tell the team it stays where it is."],
               ["Do not let anyone present a holdout number to judges as a performance "
                "claim. Your letter says what is missing before that is honest.",
                "Do not reopen the freeze because of a score. The reasoning is in "
                "DECISION_LOG D6."]),
}


LETTERS = {"Anushka": anushka, "Sanskruti": sanskruti, "Chaitany": chaitany,
           "Tanisha": tanisha, "Riddhi": riddhi, "Nirmik": nirmik}
