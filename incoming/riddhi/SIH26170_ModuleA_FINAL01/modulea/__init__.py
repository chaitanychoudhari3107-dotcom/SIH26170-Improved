"""Module A — observed-anomaly detection for SIH 26170 burn-in screening.

Module A answers one question: does this component already look abnormal, relative
to its normal references and to the other components in its own lot?

It emits a score, a disposition of PASS or MONITOR, and its evidence. It never
emits REJECT — the final PASS / MONITOR / REJECT belongs to fusion.

Read `docs/MODEL_CARD.md` before using any output.
"""
from modulea.constants import DATASET_ID, MODEL_VERSION

__all__ = ["DATASET_ID", "MODEL_VERSION"]
