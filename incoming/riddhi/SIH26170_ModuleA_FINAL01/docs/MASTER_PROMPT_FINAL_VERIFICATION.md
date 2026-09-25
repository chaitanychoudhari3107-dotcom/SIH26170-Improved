# Master prompt — Module A final verification

Run this in a fresh session. It performs **two independent re-runs** of
`ModuleA-FINAL01`, compares them, fixes whatever is wrong, and produces the final
files for all six team members. After it completes, Module A is closed.

Paste this whole file as your first message, with the release archive and the dataset
attached or on disk.

---

## Role and standing rules

You are the working engineer on **Module A — observed-anomaly detection** for SIH 2026
problem statement 26170. Two briefs already govern you and both still apply; read them
before anything else:

- `docs/MASTER_PROMPT.md` — the base brief. Its **zero-false-positive rule** is the one
  that matters: every number, name and claim you write must trace to a file in
  `results/`, or you do not write it.
- `docs/MASTER_PROMPT_DEPLOYMENT.md` — the hardening brief, including the invariant
  that the fitted model does not change.

This file adds the verification protocol and the closing deliverables. Where it and
those two disagree, they win.

## The invariant, checked first

```bash
export SIH26170_RELEASE=/path/to/SIH26170_FINAL_RELEASE_01
python -c "import sys; sys.path.insert(0,'.'); from modulea import config; print(config.config_digest())"
```

Must print `2b2fa4da5ee36e7cc8893ecba3519e7052198f215433892c3fae6a2291d2e6a9`.

**If it does not, stop.** The fitted model has changed and nothing below is meaningful.
Report that and wait.

The runtime contract digest must read `d73ea59a16361e23790ab975f8804d7cae7afd5c9f39ab58a9b2f9c76359a200`.

---

## The two phases, and why they are separate

**Analysis** reads the dataset and writes `results/`. It is what gets compared.
**Release** compares two analysis runs, then builds the manifest and the packets.

They are separate because the packets and the manifest **embed the reproducibility
verdict**, which is produced by comparing two analysis runs. A run that also built
packets could never be compared against another one — the packets would differ by the
act of comparing. Getting this wrong is the single most confusing failure in this
pipeline, and it was hit four times before the split was made.

```
scripts/run_canonical.sh   the analysis run. Compared.        Run twice.
scripts/release.sh         compare, manifest, packets.        Run once, from run A.
```

## Step 1 · Run A — the release as shipped

Work in a clean extraction of the release archive.

```bash
python scripts/00_selfcheck.py --release $SIH26170_RELEASE
bash scripts/run_canonical.sh $SIH26170_RELEASE /path/to/unpacked/ModuleB/packet
```

**Do not run `scripts/07_freeze.py` or `scripts/08_predict_holdout.py`.** They are gated;
stage 08 is one-shot and spent. Its outputs live in `prediction/` precisely so a
re-run cannot destroy them. If `prediction/` is missing files, restore them from the
archive — never regenerate them.

Expected: selfcheck PASS, 79 tests, 138 claim checks, 0 failures.

## Step 2 · Run B — independent, from a second clean extraction

A second extraction in a different directory, with `results/` emptied first, so nothing
from run A can leak in.

```bash
rm -rf results/* packets
bash scripts/run_canonical.sh $SIH26170_RELEASE /path/to/unpacked/ModuleB/packet
```

**Why a second extraction and not just a second invocation:** a re-run in the same
directory reads files the first run left behind. That is not independence, and it is
how a stage that silently depends on a previous run's output goes unnoticed. This exact
check found two defects the first time it was performed — see §"What this caught before".

## Step 3 · Compare, then release — from run A

```bash
cd <runA>
bash scripts/release.sh $SIH26170_RELEASE <runB>/results
```

**The verdict must be `REPRODUCIBLE`: 44 of 44 files identical.** The script then writes
the manifest, builds all six packets, and runs the claim ledger with
`--with-packets`, which verifies every packet against its own checksums.

If any file in `MUST_MATCH` differs, that is a defect and you fix it. The usual cause
is a wall-clock time, an absolute path, a dictionary iteration order, or an unseeded
random draw written into an output. Fix the source of the nondeterminism; do not add
the file to `MAY_DIFFER` to make the check pass. Adding to `MAY_DIFFER` is only correct
when the content is genuinely environment-specific, and it needs a comment saying why.

If a file is `ABSENT` from one tree, a stage failed silently or depends on something it
should not. Find out which, and fix it.

## Step 4 · Fix anything you find

You have standing approval to fix, without asking, anything that:

- does not move `config_digest` or `runtime_contract_digest`;
- does not change any value in `prediction/`;
- does not require re-running a gated stage.

After **every** fix: re-run the affected stage, re-run `scripts/10_verify_claims.py`,
and add a check for whatever you fixed so the next person cannot reintroduce it. The
claim count only goes up.

Anything that *would* move a digest or a prediction goes in
`docs/FUTURE_RELEASE_ITEMS.md` instead, with the reasoning. The holdout is spent; there
is nothing left to validate a model change against.

Record each fix with `state/checkpoint.py` so an interrupted session resumes cleanly.

## Step 5 · Confirm the deliverables

`scripts/release.sh` has already written all six role-scoped packets into `packets/`,
each with its own letter, the same `RELEASE_IDENTITY.json`, and its own
`SHA256SUMS.txt`. The zips are byte-deterministic — fixed entry timestamps — so two
release runs from identical analysis produce identical archives. Confirm:

- six zips exist;
- every one carries the same `model_config` and `runtime_contract` digest;
- every `SHA256SUMS.txt` verifies;
- `RELEASE_MANIFEST.json` records the test and claim counts, both passing.

Then mark the checkpoint `FINAL_VERIFICATION_COMPLETE` and report, in plain language:
what the two runs agreed on, what you fixed, what you deliberately did not fix, and
which packet goes to whom.

---

## What this protocol caught the first time it was run

Stated so you know the check earns its keep, and so you recognise the shapes.

6. **A results file that could never match.** `00_selfcheck.csv` recorded pytest's
   wall-clock duration, so no two runs could ever be byte-identical. Now it records
   counts.
7. **A pipeline that could not run clean.** `run_all.py` failed on an emptied
   `results/`, because stages 14 and 15 read the **gated** stage 08's one-shot output
   from it. Regenerable analysis and immutable release artifacts were sharing a
   directory. The frozen predictions now live in `prediction/`, and `run_all.py`
   refuses to start if they are absent rather than failing four stages later.

3. **A provenance baseline that could erase itself.** The at-freeze source hash list
   lived in `results/`. Clearing that directory destroyed it, and stage 17 then silently
   re-baselined to "nothing changed since freeze" — which is precisely how a post-freeze
   change disappears from the record. It now lives in `models/` and stage 17 **refuses**
   to recreate it without an explicit flag.
4. **Four layers of circularity between the ledger, the packets and the comparison.**
   The claim ledger checked the reproducibility verdict; the packets embedded the claim
   count; the packet checks only fired when packets existed. Each made the two runs
   unable to converge. Resolved by the analysis/release split above.
5. **A results file no stage produced.** `09_ranking_comparison.json` had been written
   by an ad-hoc command, so a clean run could not regenerate it. Folded into stage 09.

Earlier passes caught two more worth recognising:

8. **A figure quoted from the wrong budget.** The headline nested estimate was reported
   from a 3% run while the release ships at 1%. Caught by `10_verify_claims.py` when the
   stage was re-run under the current config. If you see a claim check fail after you
   change a config value, that is this failure mode, and the document is wrong, not the
   check.
9. **A latent serving crash.** A statistical rank of exactly 1.0 mapped onto the
   out-of-specification floor, which would make the contract validator refuse the frame.

## Rules for this session specifically

- **Two runs, then compare. Never one run and an assertion that it would reproduce.**
- **A failing check is information, not an obstacle.** Never edit a check to make it
  pass. If the check is genuinely wrong, say so explicitly and explain why before
  changing it.
- **Do not re-run gated stages.** Not to "confirm", not to "regenerate", not for a
  cleaner file.
- **Report the inconvenient result at the same volume as the convenient one.**
- **If you cannot support a statement, the correct output is the statement that you
  cannot.**

## Definition of done

- Two independent runs, verdict `REPRODUCIBLE`, 44 of 44.
- `config_digest` unchanged; `prediction/` unchanged.
- Tests and claim checks both passing, counts recorded in `RELEASE_MANIFEST.json`.
- Six packets built, each verifying its own checksums.
- `state/CHECKPOINT.json` shows `FINAL_VERIFICATION_COMPLETE` with `blocked_on` null.
- `docs/FUTURE_RELEASE_ITEMS.md` lists everything found and deliberately not fixed.

After that, Module A is closed. Anything further is a future release.
