"""
Stage 0 — prove the environment and the inputs are what we think they are.

Run this first, and run it again before the freeze. It checks nothing about
model quality; it checks that the code, the library versions and the input files
are the ones the rest of the results will claim to have used.

The holdout is HASHED here, never read. A SHA-256 proves the delivery is the one
moduleb.holdout_manifest describes without opening a single measurement; the
declared structure supplies the row and lot counts this stage used to parse out
of the file (decision D14).
"""
from _common import ROOT, Stage, header, show, written

import json
import platform
import subprocess
import sys

import numpy as np
import pandas as pd

from moduleb import config, dataio, decisions, holdout_manifest, serving
from moduleb.constants import DATASET_ID


def main() -> int:
    with Stage("STAGE 0 — self check") as st:
        import scipy
        import sklearn

        header("environment")
        env = dict(python=sys.version.split()[0], platform=platform.platform(),
                   numpy=np.__version__, pandas=pd.__version__,
                   scikit_learn=sklearn.__version__, scipy=scipy.__version__)
        for k, v in env.items():
            print(f"  {k:14s} {v}")

        header("digests")
        print(f"  model config    {config.frozen_config_digest()}")
        print(f"  runtime contract {serving.runtime_contract_digest()}")
        print("  Any change to a number in the FROZEN_V1 block changes the model digest")
        print("  and invalidates every frozen artifact produced under the old one. The")
        print("  runtime digest moves when serving behaviour changes without touching a")
        print(f"  fitted parameter — serving contract {serving.SERVING_CONTRACT_VERSION}.")

        header("release decisions")
        failures = decisions.check_release_decisions()
        for d in decisions.RELEASE_DECISIONS:
            print(f"  {d.id:4s} {d.statement}")
        if failures:
            for f in failures:
                print(f"  FAIL {f}")
            raise SystemExit("a recorded release decision no longer holds")
        print(f"  all {len(decisions.RELEASE_DECISIONS)} recorded decisions hold")

        header("input files")
        rows = []
        for name in ("train", "calibration", "holdout", "specs", "dictionary",
                     "contract", "version"):
            p = dataio.PATHS[name]
            rows.append(dict(file=name, exists=p.exists(),
                             bytes=p.stat().st_size if p.exists() else 0,
                             sha256=dataio.file_sha256(p)[:32] if p.exists() else ""))
        show(pd.DataFrame(rows), "{:,.0f}")

        header("dataset identity")
        meta = dataio.load_dataset_version()
        print(json.dumps({k: meta[k] for k in ("dataset_id", "status",
                                               "generator_version_public", "split_id",
                                               "rows", "lots")}, indent=2))
        assert meta["dataset_id"] == DATASET_ID

        header("splits load and pass every guard")
        splits = {n: dataio.load_split(n) for n in ("train", "calibration")}
        for s in splits.values():
            print("  " + s.describe())

        header("holdout — hashed, not opened")
        holdout_manifest.verify_delivery_hash(dataio.file_sha256(dataio.PATHS["holdout"]))
        print(f"  delivery hash matches moduleb.holdout_manifest: "
              f"{holdout_manifest.SHA256[:32]}")
        print(f"  declared structure: {holdout_manifest.N_ROWS} rows, "
              f"{holdout_manifest.N_LOTS} lots, {holdout_manifest.N_COLUMNS} columns, "
              f"targets={holdout_manifest.HAS_TARGETS}")
        print("  This stage does not read the file. Decision D14: the structural facts")
        print("  come from the declared manifest, and exactly one gated stage opens the")
        print("  contents — scripts/12_predict_holdout.py, after the freeze.")

        total = sum(s.n_rows for s in splits.values()) + holdout_manifest.N_ROWS
        lots = sum(s.n_lots for s in splits.values()) + holdout_manifest.N_LOTS
        print(f"  totals: {total} rows / {lots} lots "
              f"(manifest says {meta['rows']} / {meta['lots']}; "
              f"holdout contribution declared, not read)")
        assert total == meta["rows"], "row count disagrees with the dataset manifest"
        assert lots == meta["lots"], "lot count disagrees with the dataset manifest"

        header("unit tests")
        r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                           cwd=ROOT, capture_output=True, text=True)
        print(r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-400:])
        if r.returncode != 0:
            print(r.stdout[-3000:])
            raise SystemExit("unit tests failed; fix them before trusting any result below")

        out = pd.DataFrame(rows)
        written(dataio.write_result(out, "00_input_hashes.csv"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
