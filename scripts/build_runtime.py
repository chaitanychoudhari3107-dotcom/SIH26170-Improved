"""Reconstruct the prototype serving bundle; never reads holdout targets.

Module A is recovered byte-for-byte from the delivered ZIP. Module B is a
REHEARSAL rebuild because the repository does not include its original artifact.
It must not inherit the published benchmark's performance claims.
"""
from pathlib import Path
import hashlib
import json
import sys
import zipfile
import platform

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend/runtime"))
from moduleb import dataio, freeze


def main():
    out = ROOT / "data/runtime"
    out.mkdir(exist_ok=True)
    source = ROOT / "incoming/nirmik/SIH26170_ModuleB_FINAL01_RC2"
    specs = ROOT / "data/reference/Device_Specs.csv"
    train = dataio.load_split("train", source / "data/01_BUILD/ModuleB_Train.csv")
    calibration = dataio.load_split("calibration", source / "data/02_CALIBRATE/ModuleB_Calibration.csv")
    dataio.PATHS["specs"] = specs
    base, limits = dataio.load_specs(specs)
    freeze.freeze(train, calibration, base, limits, out / "module_b.joblib",
                  team_signoff=freeze.REHEARSAL_SIGNOFF, release_state=freeze.REHEARSAL)
    receipt = json.loads((ROOT / "incoming/riddhi/SIH26170_ModuleA_FINAL01/models/FREEZE_RECEIPT.json").read_text())
    with zipfile.ZipFile(ROOT / "incoming/SIH26170_ModuleA_FINAL01.zip") as archive:
        blob = archive.read("SIH26170_ModuleA_FINAL01/models/module_a_final01.joblib")
    if hashlib.sha256(blob).hexdigest() != receipt["artifact_sha256"]:
        raise RuntimeError("Module A archive hash does not match the delivered receipt")
    (out / "module_a.joblib").write_bytes(blob)
    import sklearn, pandas, numpy
    metadata = {
        "version": "operational-prototype-1", "release_state": "RESEARCH_PROTOTYPE",
        "module_a_source": "Original delivered artifact; runtime lot manifest supplied by operator",
        "module_b_source": "Reconstructed REHEARSAL artifact fitted only on delivered train and calibration lots",
        "limitations": "Synthetic data. Module B rebuild is not the original evaluated artifact. No production qualification or guaranteed coverage.",
        "training_input_hashes": {"train": train.sha256, "calibration": calibration.sha256},
        "artifact_hashes": {name: hashlib.sha256((out / name).read_bytes()).hexdigest()
                            for name in ("module_a.joblib", "module_b.joblib")},
        "spec_sha256": hashlib.sha256(specs.read_bytes()).hexdigest(),
        "versions": {"python": platform.python_version(), "pandas": pandas.__version__, "numpy": numpy.__version__, "scikit_learn": sklearn.__version__},
    }
    (out / "runtime_manifest.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
