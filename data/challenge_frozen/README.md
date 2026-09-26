# Frozen synthetic challenge — baseline

This benchmark has **five new 64-part CMOS_A lots** generated with a fixed seed. No component measurement row was copied from the model training example or the earlier holdout. The generator draws ordinary readings around the public synthetic specification baselines, then injects the scenario patterns documented in `freeze_manifest.json`. These are **injection labels**, not verified physical defects or estimates of flight-hardware performance. This is a targeted challenge, not a representative sample of deployment prevalence.

The frozen measurement and label SHA-256 values are in `freeze_manifest.json`. The script refuses to overwrite the files or baseline report. All results use `prototype-review-policy-1`; MONITOR, HOLD, and REJECT count as **sent for review**. PROVISIONAL_PASS/PASS count as **not sent for review**.

| Scenario | Injected / controls | 24h injected reviewed | 24h controls reviewed | 168h injected reviewed | 168h controls reviewed |
| --- | ---: | ---: | ---: | ---: | ---: |
| Static-pass latent drift | 8 / 56 | 4 / 8 | 15 / 56 | 8 / 8 | 6 / 56 |
| Low-start, late drift | 8 / 56 | 0 / 8 | 15 / 56 | 8 / 8 | 7 / 56 |
| Benign high baseline | 0 / 64 | N/A | 18 / 64 (all 8 elevated controls) | N/A | 13 / 64 (all 8 elevated controls) |
| Whole-lot benign shift | 0 / 64 | N/A | 40 / 64 | N/A | 6 / 64 |
| Defect-heavy peer baseline | 32 / 32 | 32 / 32 | 6 / 32 | 4 / 32 | 5 / 32 |

Across these *constructed* cases, 24h reviews 36/48 injected parts and 94/272 controls. The 168h point-in-time decisions review 20/48 injected parts and 37/272 controls. The aggregate deliberately mixes different stressors and **must not be sold as a deployment confusion matrix**.

Key diagnosis: a 24h rule has no observable evidence of the intentionally late-only drift, so 0/8 there is expected. The peer-corruption scenario shows a temporal consistency problem: 28 of 32 injected components are PASS at 168h despite being MONITOR at 24h. Existing prior-alert history warns an operator, but it does not change the 168h matrix. The benign scenarios reveal a substantial review load, especially the 40/64 shifted lot at 24h.

To reproduce from the project root with the pinned dependencies installed:

```powershell
python scripts/frozen_synthetic_challenge.py generate
python scripts/frozen_synthetic_challenge.py evaluate
```

Run those commands in a *fresh folder*, or just inspect the already frozen CSVs and report: the generator intentionally refuses to replace a freeze. For a reproducibility check, pass `--folder` pointing to a new directory, then compare hashes and results. Do not train or tune on these files. Develop a targeted rule using separate development data, fix its review-budget rule, and evaluate it once on this frozen challenge. A newly proposed candidate after looking at these results requires an additional untouched confirmatory set for an unbiased performance claim.
