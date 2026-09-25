"""Shared fixtures.

Lot size is 35, above moduleb.config.MIN_LOT_COHORT. Until 19 Sep it was 20,
which is smaller than any real FINAL-01 lot (68-82) and smaller than the serving
contract now permits — the fixture was quietly exercising a request shape
production refuses. A small synthetic frame is used wherever a test is about
behaviour rather than about FINAL-01 itself, so the suite runs in seconds and
still exercises the real code paths."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from moduleb.constants import PARAMS, VARIANTS  # noqa: E402


def _synthetic(n_lots_per_variant=6, n_per_lot=35, seed=7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    base = {p: 1.0 + 0.5 * i for i, p in enumerate(PARAMS)}
    cid = 0
    for vi, v in enumerate(VARIANTS):
        for li in range(n_lots_per_variant):
            lot = f"{v}_LOT{li:02d}"
            lot_age = 1.0 + 0.02 * li
            for _ in range(n_per_lot):
                cid += 1
                r = {"component_id": f"C{cid:05d}", "lot_id": lot,
                     "device_family": "DIGITAL_CMOS", "device_variant": v}
                for p in PARAMS:
                    x0 = base[p] * (1 + 0.1 * vi) * float(rng.lognormal(0, 0.05))
                    x24 = x0 * (1 + 0.01 * lot_age + rng.normal(0, 0.004))
                    x168 = x24 * (1 + 0.03 * lot_age + 0.6 * (x24 / x0 - 1) + rng.normal(0, 0.006))
                    r[f"{p}_0h"], r[f"{p}_24h"], r[f"{p}_168h"] = x0, x24, x168
                rows.append(r)
    return pd.DataFrame(rows)


def expected_sizes(df) -> dict[str, int]:
    """The request metadata a caller supplies to prove each lot is complete.

    In production this comes from the lot traveller or the request; in the tests
    the fixture frame IS the complete delivery, so its own group sizes are the
    declared sizes. Tests that want an INCOMPLETE delivery drop rows from the
    frame and keep these sizes, which is exactly the situation the serving
    contract has to catch."""
    return {str(k): int(v) for k, v in df.groupby("lot_id").size().items()}


@pytest.fixture(scope="session")
def synth():
    return _synthetic()


@pytest.fixture(scope="session")
def specs():
    from moduleb import dataio
    return dataio.load_specs()


@pytest.fixture(scope="session")
def synth_feat(synth, specs):
    from moduleb.features import add_features, make_folds
    base, _ = specs
    f = add_features(synth, base)
    f["fold"] = make_folds(f, 4)
    return f
