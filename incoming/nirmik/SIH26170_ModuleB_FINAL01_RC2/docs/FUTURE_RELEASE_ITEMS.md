# Future release items — NOT part of this release

Everything in this file is deliberately **out of scope** for `ModuleB-FINAL01-RC2`.
It is here so that the current release has no open technical decision and nobody has
to guess whether an idea was forgotten or declined.

Nothing below changes the frozen configuration, the runtime contract, the recorded
decisions or any documented number in this package. Acting on any of it produces a
**new release with new digests**, and it must not be done between team sign-off and
the one-shot holdout run.

---

## Model work

**F-1 · An independently-bounded extrapolation cap.**
D11 closed with `FORECAST_REL_DELTA_CAP = None` because every candidate value was
post-hoc on calibration. A cap fixed *independently* of the calibration outcome — from
a physical drift limit Tanisha can source, or from the generator's own design record —
would reopen the decision legitimately. The evidence is already measured in
`results/07_cap_sweep.csv`; what is missing is a bound that does not come from the data
it would be judged on.

**F-2 · Separate treatment for `Input_Leakage_Current`.**
It is the one parameter that loses to the median-ratio baseline on calibration, and
27.7 % of its error sits on one component of 906. A heavier-tailed model, a log-target,
or a per-variant treatment are all plausible. None is defensible as a late change to a
release that has already been benchmarked, and all of them would have to be re-tested
on a fresh whole-lot protocol.

**F-3 · Cluster-conformal coverage.**
The envelope's coverage is measured, not derived, because the units are whole lots with
within-lot correlation and no cluster-conformal derivation exists for the implemented
score construction (review finding F2). Deriving one — or adopting a published
construction and re-fitting the offsets under it — would let the package say something
stronger than "measured on twelve lots".

**F-4 · Conditional coverage on the worst-drifting decile.**
Tail coverage runs 0.407–0.769 against a nominal 0.95. That is reported rather than
fixed. A conditional or quantile-adaptive envelope is the obvious next attempt; it is a
redesign, not a tune.

## Engineering

**F-5 · A per-lot expected-size feed.**
The serving contract accepts declared per-lot sizes or a custodian file attestation.
In a real line, the expected size would come from the lot traveller or the MES, and
Module B would read it rather than being told. That integration does not exist here
and is Anushka's layer, not Module B's.

**F-6 · A signed release manifest.**
`RELEASE_MANIFEST.json` carries its own digest, which detects accidental drift but not
a deliberate edit by someone who can also recompute the digest. Signing it with a key
Chaitany holds would close that, and is worth doing only if the team adopts key
management for the whole release.

**F-7 · Reason-code precision and recall.**
Module B measures how often each `B_` code fires and nothing else, because it has no
correctness label for its own codes. Scoring the codes needs the evaluator's hidden
truth and therefore belongs to Sanskruti's layer, after the blind evaluation — never
inside Module B.

## Receipts and evaluator-facing provenance

*Both raised by Sanskruti on 21 Sep 2026 while verifying the RC2 handoff. Neither
changes this release; both are fair and are scheduled rather than argued with.*

**F-9 · `expected` counts read as `null` when the proof was a file attestation.**
`HOLDOUT_PREDICTION_RECEIPT.json` records `completeness.expected` as `null` for every
lot, because the proof used was the custodian's whole-file attestation (SHA-256, rows,
lots) rather than declared per-lot sizes — so there were no per-lot numbers to record.
`null` reads like a missing value rather than a deliberate "not applicable under this
proof". The receipt should say which it is.

**F-10 · `lot_id` is not in the prediction output.**
The output contract is `component_id`-keyed, so an evaluator cannot independently check
the per-lot counts the receipt asserts without a separate map. Adding `lot_id` to the
contract would change the output-contract digest and therefore the release, so it did
not happen here; a `component_id → lot_id` map ships alongside instead. Worth folding
into the contract in the next release.

## Documentation

**F-8 · A judge-facing one-pager.**
`docs/COMPLETE_GUIDE.md` is the engineering record and is long on purpose.
A two-page version for the presentation is a presentation task, and the numbers for it
must be quoted from `results/`, never re-derived by hand.
