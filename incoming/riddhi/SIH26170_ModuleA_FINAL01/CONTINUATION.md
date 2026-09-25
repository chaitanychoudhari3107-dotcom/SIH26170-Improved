# If this work was interrupted — start here

This file plus `state/CHECKPOINT.json` is everything a fresh session needs. No
conversation history is required.

```bash
export SIH26170_RELEASE=/path/to/SIH26170_FINAL_RELEASE_01
python state/checkpoint.py          # what is done, what is next, what is blocked
```

## Read these three things, in order

1. `state/CHECKPOINT.json` — the machine-readable record. Every hardening stage marks
   itself DONE, FAILED or SKIPPED with the artifacts it wrote. `next_action` is the
   single next thing to do; `blocked_on` is non-null only if something needs a human.
2. `docs/MASTER_PROMPT_DEPLOYMENT.md` — the standing brief for this phase. It sets the
   rules; nothing below overrides them.
3. `docs/RUNBOOK.md` — how to run anything.

## Then verify the state is what the checkpoint claims

```bash
python scripts/00_selfcheck.py --release $SIH26170_RELEASE     # hashes, tests
python scripts/10_verify_claims.py                              # docs vs results/
python -c "from modulea import config; print(config.config_digest())"
```

The third command must print `2b2fa4da5ee36e7cc8893ecba3519e7052198f215433892c3fae6a2291d2e6a9`.
**If it does not, the fitted model has changed and the hardening phase has failed its
own invariant.** Stop and report that, rather than continuing and producing numbers
that do not describe the frozen artifact.

## The two states you might find

**`next_action` names a stage that has not run.** Run it, let it mark itself, run
`scripts/10_verify_claims.py`, continue to the next. Stages are independent and
ordered; none needs a previous one's in-memory state, only its files.

**A step is marked FAILED.** Its `detail` says why. Fix that, re-run that stage only,
and do not skip ahead — a later stage quoting a number from a failed one is exactly the
kind of unsupported claim the master prompt exists to prevent.

## What must not change while resuming

- The fitted model. This phase adds verification, documentation and packaging. If a
  change would move `config_digest`, it does not belong in this phase — record it in
  `docs/FUTURE_RELEASE_ITEMS.md` instead.
- The frozen artifact `models/module_a_final01.joblib` and its receipt.
- The holdout prediction files. They were hashed when written; stage 09 refuses to
  score a file that changed afterwards, and that refusal is a feature.

## If the dataset is missing

Everything except stages 00–09 can run without it. The dataset is
`SIH26170_FINAL_RELEASE_01`, verified by the three SHA-256 values in
`modulea/dataio.py`. Ask Nirmik; do not substitute another version, and do not compare
any number produced from a different version against the ones recorded here.
