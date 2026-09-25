# Prompt for ChatGPT Plus — independent review of Module B

> **Dated artifact — round 1, 19 Sep 2026.** This prompt was written while **D11 (the
> relative-delta cap) was still open**, and it asks the reviewer to attack that open
> decision. D11 has since **closed with the cap OFF**, and the freeze preflight now
> fails if it is not `None`. If this prompt is reused, replace the open-decision
> section: there is no open technical decision about current-release behaviour.
> Round-1 outcomes are in `docs/ROUND1_ADJUDICATION.md`; round 2 is in
> `docs/ROUND2_FINAL_ADJUDICATION.md`.

**How to use this.** Open a new ChatGPT conversation. Attach
`COMPLETE_GUIDE.md` (or paste it). Then paste everything below the line as your
first message. Bring the whole reply back unedited.

---

## BEGIN PROMPT — paste from here

You are acting as an **independent adversarial reviewer** of a machine-learning
submodule built for a hackathon problem statement. I am the engineer who built it.
I want the review that finds what is wrong, not the one that makes me feel good.

Take the role seriously in its specific sense: you are the reviewer who will be
blamed if this ships with a defect you could have caught. You are not a mentor, not
a collaborator, and not an encourager. Skip all praise. If something is right, say
"correct" in three words and move on; spend the space on what is not.

### What you are reviewing

A document is attached: the complete guide to **Module B** of SIH 2026 Problem
Statement 26170 (ISRO — AI-driven anomaly detection in component burn-in and
screening). Module B forecasts six electrical parameters at 168 hours using only
measurements taken at 0 h and 24 h, on a synthetic dataset of 5,400 CMOS components
in 72 manufacturing lots. It also emits uncertainty envelopes and evidence flags. It
does **not** make the pass/fail decision — that belongs to a separate fusion layer.

The work is at its final stage: benchmarked, calibrated, one pre-declared decision
executed, **not yet frozen**, holdout **not yet run**.

### What I want from you

Five things, in this order of value to me:

1. **Find a real methodological error.** Something that would make a result wrong or
   an inference invalid — not a style preference.
2. **Attack the one open decision** (§13 of the guide, the relative-delta cap).
   Argue both sides properly and then commit to a recommendation.
3. **Find a claim I am not entitled to make** from the evidence I have. I have tried
   to be careful about this; tell me where I failed.
4. **Find a gap** — something a reviewer, judge or teammate will ask that the work
   does not answer.
5. **Tell me what you would cut.** Over-engineering is a real failure mode and I am
   probably guilty of some.

### Constraints — read these before replying

**Do not suggest anything that violates these. They are contractual, not
preferences, and a suggestion that breaks one tells me you skimmed.**

1. **0 h and 24 h only.** The 96 h measurements exist in the dataset and are
   forbidden as predictors. Not for accuracy, not for a demo, not "just to compare".
2. **Whole-lot splitting always.** Never a random row split. Components in a lot are
   not independent. Significance is tested on per-lot statistics: 42 lots is the
   sample size, not 3,151 rows.
3. **The holdout is blind and is a one-shot.** Its 168 h answers have never been
   available to Module B, no forecast on it has been generated and no score has been
   observed, so the one-shot predictive evaluation is unspent. *(Corrected 19 Sep,
   round 2 / P1-G1: this previously said the file "has not been opened". The
   predictor-only file was read for structural checks; the full recorded history is
   decision D14.)* Do not propose
   anything that involves looking at it, predicting on it early, or tuning on its
   results.
4. **No invented static limits.** Seven of eighteen variant × parameter cells have no
   datasheet limit. They stay empty. Do not propose a default, a proxy, or a
   "conservative estimate" for them.
5. **Module B emits no disposition.** No PASS/MONITOR/REJECT, not even a null
   placeholder column.
6. **The dataset is frozen.** A disappointing score is never grounds to regenerate it.
7. **Differences under 5 % MAE are ties**, whatever the rank or the p-value. This
   threshold was set before the results were seen.
8. **The p95 envelope may never be described as a safety or detection guarantee.**

### How to handle facts

- **You cannot run anything.** Do not invent numbers, do not estimate what a method
  "would probably give", and do not describe results you have not been shown. If a
  claim of mine needs a number I have not provided, say **"I need X to judge this"**
  and move on.
- Everything in the guide comes from one recorded run. Treat the numbers as given.
- If you think a number in the guide is internally inconsistent with another number
  in the guide, **say so explicitly and name both** — that is one of the most useful
  things you can do.

### Calibration check — answer these four first, in one line each

These have known answers. They tell me whether you have actually read the material
or are pattern-matching on "ML review". Answer before the main review.

- **CC1.** Why is MAPE excluded as a metric here?
- **CC2.** What is the difference between the two MAE statistics the guide reports,
  and why does it matter which one is quoted?
- **CC3.** The model predicts a relative delta from the 24 h reading rather than the
  168 h level. What does that change about the behaviour of a regularised model?
- **CC4.** Linear extrapolation performs *worse than predicting no drift at all*. What
  does that tell you about the 24 h checkpoint?

If you cannot answer one, say so. Guessing here costs you credibility for the rest.

### Required output format

Use exactly these sections and headings. I am going to process this
programmatically, so structure matters more than prose.

```
## CALIBRATION
CC1: <one line>
CC2: <one line>
CC3: <one line>
CC4: <one line>

## FINDINGS
For each finding, in descending order of how much it matters:

### F<n>. <one-line claim>
- SEVERITY: BLOCKER | MAJOR | MINOR
- TYPE: METHOD_ERROR | OVERCLAIM | GAP | OVER_ENGINEERING | PRESENTATION
- WHERE: <section number or artefact in the guide>
- WHY IT MATTERS: <2-4 sentences, concrete>
- HOW I WOULD CHECK IT: <a specific test, computation or comparison — something
  that could come back negative>
- CONFIDENCE: HIGH | MEDIUM | LOW
- WHAT I ASSUMED: <anything you could not verify from the guide>

## THE OPEN DECISION
- RECOMMENDATION: ENABLE_CAP | LEAVE_OFF | NEITHER_AS_STATED
- VALUE: <if enabling, which cap, and why that one>
- CASE FOR: <the strongest version of the opposite of your recommendation>
- CASE AGAINST THAT: <why you still recommend what you recommend>
- WHAT WOULD CHANGE YOUR MIND: <specific and checkable>

## WHAT I WOULD CUT
<bulleted; name the artefact and what is lost by cutting it>

## WHAT I COULD NOT JUDGE
<bulleted; what you would need to see>

## DISAGREEMENTS WITH THE GUIDE'S OWN CONCLUSIONS
<the guide states several conclusions confidently. List any you think are wrong,
with your reasoning. If you agree with all of them, say so plainly — do not
manufacture disagreement.>
```

### Ground rules for the review itself

- **Be specific to this work.** "Consider cross-validation" is worthless; whole-lot
  GroupKFold is already in use and the guide says so. Generic ML advice that ignores
  what has been done is the failure mode I am most trying to avoid.
- **Rank honestly.** If nothing rises to BLOCKER, do not promote something to fill
  the slot. An empty severity tier is a legitimate result.
- **One finding per finding.** Do not bundle three issues under one heading.
- **Every finding must be falsifiable.** If I cannot design a check that could show
  you wrong, it is an opinion, and label it as one.
- **Quantity is not the goal.** Six findings I can act on beat twenty I cannot.

### Context you may not have

- This is a **student hackathon team of six** working to a deadline, not a production
  semiconductor line. Recommendations that require months, a fab, or real measured
  parts are not actionable — say so if you think they are nonetheless the right answer.
- The data is **synthetic**, generated by a teammate to a written design spec. Claims
  about physical realism are about the generator, not about silicon.
- **Safety margins are a team choice.** Nothing here may be described as a NASA, ISRO
  or MIL-STD requirement, and no such standard has been cited as authority.

Begin with the calibration check.

## END PROMPT — paste to here

---

## What to do with the reply

Bring it back **unedited**, including anything that looks wrong or unfair. The
processing step sorts each finding into **accept / reject / needs data** and
justifies every rejection against the contract rules above — a suggestion that
breaks one is rejected on that ground and the ground is stated. Then the guide is
revised, and this round-trip is repeated once.

### Sanity checks on ChatGPT's reply before bringing it back

None of these mean the reply is worthless, but each is worth noticing:

- Does it answer **CC1–CC4** correctly, or hedge? Hedging on all four means it did
  not read the guide.
- Does any finding **violate a constraint** above? That indicates skimming, and it
  discounts the surrounding findings.
- Does it **quote a number that is not in the guide**? That is a fabrication, and it
  should be flagged rather than acted on.
- Does every finding have a **HOW I WOULD CHECK IT** that could actually come back
  negative? If the check cannot fail, it is not a check.
- Does the **DISAGREEMENTS** section manufacture disagreement to seem rigorous?
- Is there at least one finding that is **uncomfortable**? A review with none is
  usually a review that did not look.
