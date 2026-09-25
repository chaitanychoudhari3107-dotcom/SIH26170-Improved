# Master prompt — Module A, pre-integration hardening

Standing brief for the phase between "the model is frozen" and "Anushka can build
fusion on it". It sits **on top of** `docs/MASTER_PROMPT.md`, which still governs; where
they overlap, the rules there win. Read both before touching anything.

---

## Where we are

`ModuleA-FINAL01` is frozen. The configuration was selected under nested
leave-one-lot-out, the one-shot holdout run is spent, and the numbers are recorded.
That work is **finished and is not the job**.

The job now is the gap between a model that scores well and a component another
engineer can build on without reading its internals. Module B closed that gap: 102
tests, 210 machine-checked claims, a runtime contract with its own digest, per-teammate
packets, a provenance addendum explaining why one digest moved and why that is not a
build mismatch. Module A has less. Closing that difference is the whole of this phase.

## The one thing that must not happen

**The fitted model does not change in this phase.**

```
config_digest            2b2fa4da5ee36e7c…
runtime_contract_digest  d73ea59a16361e23…
```

Both are checked at the start of every resume and by `scripts/10_verify_claims.py`. If
a change you are about to make would move either, it does not belong here — it belongs
in `docs/FUTURE_RELEASE_ITEMS.md` as a candidate for the next release.

This is not bureaucracy. Every number in `docs/VALIDATION_SUMMARY.md` describes one
specific artifact. Change the artifact during a documentation pass and every one of
those numbers becomes a claim about something that no longer exists — which is the
first-kind false positive the base brief forbids, committed at scale.

The corollary, which is harder: **a flaw found now is written down, not fixed.** If
hardening turns up something that needs the model to change, that is a finding for the
next release and a line in the limitations, not a quiet edit. The holdout is spent;
there is nothing left to validate a change against.

---

## What "ready for integration" means, concretely

Anushka should never have to read Module A's internals, ask what a column means, or
discover a constraint by hitting it. Six tests of that:

1. **The interface is self-describing.** Output contract, runtime contract, data
   dictionary and a worked example ship together, and the runtime contract has its own
   digest so a mismatch is detectable rather than arguable.
2. **Every failure is loud.** A partial lot, an unknown variant, a malformed value, a
   future column — each raises with a message that says what to do. Nothing degrades
   quietly into a plausible-looking number.
3. **The join is proved, not assumed.** Module A's output has actually been joined to
   Module B's frozen holdout predictions, the coverage checked both ways, and the result
   recorded. "It should join on component_id" is not the same statement.
4. **The score's meaning is written down and measured.** Including what it is *not*:
   not a probability, not calibrated, not comparable across epochs.
5. **Robustness is measured, not asserted.** Row order, column order, lot subsetting,
   duplicated input, unit scaling, injected noise — each with a recorded result.
6. **Every number in the packet is traceable** to a file in `results/`, and
   `scripts/10_verify_claims.py` enforces it.

## Rules specific to this phase

1. **Add a test before adding a claim.** The claim count and the test count only move
   up. A document that grows without `10_verify_claims.py` growing is a document that
   has outrun its evidence.
2. **A robustness result that is bad is still a result.** If scoring turns out to depend
   on row order, that goes in the integration note in bold, not in a backlog.
3. **Never write a number into a packet by hand.** Packets are built by a script that
   reads `results/`. A hand-copied figure is a figure that will drift.
4. **Mark the checkpoint after every stage.** `state/checkpoint.py mark(...)`. A session
   can end at any moment and the next one starts from that file; a stage that ran but
   did not mark is a stage that will be run again or, worse, assumed.
5. **Packets are derived, never authored.** Every teammate packet is built from the same
   release and carries the same `RELEASE_IDENTITY.json`. Two packets disagreeing on
   `model_config` or `runtime_contract` means one is from a different build.
6. **Say what was not tested.** The list of untested things is part of the deliverable,
   not an admission.

## The failure modes this phase is guarding against

Named, because each has already happened once on this problem statement:

- **A score that does not mean what the consumer assumes.** RC2 shipped
  `max(core, residual)`; 54 of its PASS rows outranked the weakest REVIEW row. Anyone
  who built a fusion rule by thresholding that column built it on sand.
- **A documented number that no longer matches the code.** Prevented by stage 10, which
  is why every new claim needs its check in the same edit.
- **A constraint discovered at integration time.** Partial lots are the candidate here:
  Module A is meaningless on one, and the only place that can be learned early is the
  integration note.
- **A confident statement that measurement does not support.** "Never raises a false
  positive" instead of "no observed false positive in 5,076 normals, 95% upper bound
  0.06%".

## Definition of done

- `state/CHECKPOINT.json` shows every hardening stage DONE and `blocked_on` null.
- Test count and claim count both recorded in `RELEASE_MANIFEST.json`, both passing.
- `config_digest` unchanged from `2b2fa4da5ee36e7c…`.
- An integration packet exists, built by script, that a reader who has never seen this
  repository can consume.
- `docs/FUTURE_RELEASE_ITEMS.md` lists everything found and deliberately not fixed.
