# Nirmik — FINAL Module B Package

First rerun the exact V1-frozen audit/benchmark on `01_BUILD/ModuleB_Train.csv` before changing any model setting. Then calibrate once, freeze, and only then predict holdout.

Hard rules: 0h+24h only; never 96h; holdout has no 168h targets; Module B emits forecasts/evidence, fusion owns final disposition.

Dataset: SIH26170-FINAL-01.
