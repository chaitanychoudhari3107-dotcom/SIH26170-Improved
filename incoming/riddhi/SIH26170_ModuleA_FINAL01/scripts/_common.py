import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
RESULTS = ROOT / "results"
RESULTS.mkdir(exist_ok=True)
MODELS = ROOT / "models"
MODELS.mkdir(exist_ok=True)
# Spent, frozen, hashed release artifacts. Deliberately NOT under results/, which is
# regenerable and may be cleared: the one-shot holdout run cannot be reproduced, so its
# output must not live where a clean re-run would delete it.
PREDICTION = ROOT / "prediction"
PREDICTION.mkdir(exist_ok=True)


def release_arg(parser):
    parser.add_argument("--release", required=True,
                        help="root of SIH26170_FINAL_RELEASE_01")
    return parser
