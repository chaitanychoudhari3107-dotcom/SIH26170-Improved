import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modulea.constants import EPOCHS, PARAMETERS   # noqa: E402

RELEASE_ENV = "SIH26170_RELEASE"


def _synthetic(n_lots=4, per_lot=40, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for lot in range(n_lots):
        variant = ["CMOS_A", "CMOS_B", "CMOS_C"][lot % 3]
        for i in range(per_lot):
            row = {"component_id": f"T{lot:02d}{i:03d}", "lot_id": f"L{lot:02d}",
                   "device_family": "DIGITAL_CMOS", "device_variant": variant}
            for j, p in enumerate(PARAMETERS):
                base = 1.0 + 0.3 * j
                walk = np.cumsum(rng.normal(0, 0.004, 4))
                for e, v in zip(EPOCHS, base * (1 + walk)):
                    row[f"{p}_{e}h"] = float(abs(v) + 0.01)
            rows.append(row)
    return pd.DataFrame(rows)


@pytest.fixture
def synthetic():
    return _synthetic


@pytest.fixture
def lot_sizes():
    def sizes(frame):
        return frame.groupby("lot_id").size().to_dict()
    return sizes
