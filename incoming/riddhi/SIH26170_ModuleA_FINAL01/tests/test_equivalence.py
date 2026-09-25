"""The rewritten scoring path must reproduce the inherited Better Potential core.

The rewrite exists to fix defects C3 and C4 and to make the configuration legible.
It must not quietly change the model at the same time. This asserts that on the
inherited weights the two implementations agree exactly; the release then chooses
different weights deliberately, with that change recorded in the decision log.
"""
import os
from pathlib import Path

import numpy as np
import pytest

from modulea import config
from modulea.dataio import Release
from modulea.scoring import StatisticalCore

RELEASE = os.environ.get("SIH26170_RELEASE")
INHERITED = Path("/home/claude/modulea_work")
needs_both = pytest.mark.skipif(
    not RELEASE or not Path(RELEASE).exists() or not INHERITED.exists(),
    reason="needs the release and the vendored inherited implementation")

LEGACY_WEIGHTS = {"electrical": 0.0, "temporal": 0.0, "timing": 0.0,
                  "overall_extreme": 0.10, "lot_relative": 0.90}


@needs_both
def test_matches_the_inherited_core_bit_for_bit():
    import sys
    sys.path.insert(0, str(INHERITED))
    from core import ConfigurableCore              # the vendored upstream formula

    release = Release(RELEASE)
    train, cal, hold = (release.split(s) for s in ["train", "calibration", "holdout"])
    ours = StatisticalCore(config.DEPTHS).fit(train, cal).score(hold, LEGACY_WEIGHTS)
    theirs_core = ConfigurableCore().fit(train, cal)
    theirs = theirs_core.score(theirs_core.rank_components(hold))
    assert float(np.max(np.abs(ours - theirs))) == 0.0
