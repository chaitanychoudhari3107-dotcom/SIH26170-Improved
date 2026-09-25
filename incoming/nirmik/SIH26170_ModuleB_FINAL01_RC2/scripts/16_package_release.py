"""
Stage 16 — package the release candidate.

Writes `SHA256SUMS.txt` over every shipped file, then builds the core release ZIP.
Deliberately excluded: caches, the rehearsal outputs in `results/dryrun/`, any
previously built ZIP, and anything under `models/` — a frozen artifact is produced by
stage 11 on the owner's machine and is never shipped inside the source package.

    python scripts/16_package_release.py --out /tmp/build

The ZIP's own SHA-256 is printed and is what the custody packet records.
"""
from _common import ROOT, Stage, header, written

import argparse
import hashlib
import zipfile
from pathlib import Path

INCLUDE_DIRS = ("moduleb", "scripts", "tests", "notebooks", "docs", "data", "results")
INCLUDE_FILES = ("README.md", "requirements.txt", "run_all.py", ".gitignore",
                 "RELEASE_MANIFEST.json",
                 # The freeze RECEIPT travels; the frozen artifact itself does not.
                 # The receipt carries every digest needed to verify a prediction, and
                 # a distributed copy that lacks it cannot check the two receipts
                 # against each other — which showed up as a clean-room count mismatch
                 # between the owner's tree and the shipped one.
                 "models/FREEZE_RECEIPT.json")
# Matched on whole PATH SEGMENTS, never as substrings. A substring test here once
# dropped `moduleb/models.py` from the ZIP because the string "models" also names the
# frozen-artifact directory — the clean-room audit caught it as a circular-import
# failure on a package that was simply missing a module.
EXCLUDE_DIR_NAMES = ("__pycache__", ".pytest_cache", ".ipynb_checkpoints", "models")
EXCLUDE_RELDIRS = ("results/dryrun",)
EXCLUDE_SUFFIX = (".pyc", ".zip", ".joblib")


def shipped_files(root: Path) -> list[Path]:
    out = []
    for name in INCLUDE_FILES:
        if (root / name).exists():
            out.append(root / name)
    out = [p for p in out if p.suffix not in (".joblib",)]
    for d in INCLUDE_DIRS:
        for p in sorted((root / d).rglob("*")):
            if not p.is_file():
                continue
            rel_path = p.relative_to(root)
            rel = rel_path.as_posix()
            if any(part in EXCLUDE_DIR_NAMES for part in rel_path.parts[:-1]):
                continue
            if any(rel.startswith(x + "/") for x in EXCLUDE_RELDIRS):
                continue
            if p.suffix in EXCLUDE_SUFFIX:
                continue
            out.append(p)
    return sorted(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT.parent / "build"),
                    help="directory to write the ZIP into")
    ap.add_argument("--name", default="SIH26170_ModuleB_FINAL01_RC2")
    a = ap.parse_args()

    with Stage("STAGE 16 — package the release candidate"):
        files = shipped_files(ROOT)

        header("16.1 checksums")
        lines = []
        for p in files:
            rel = p.relative_to(ROOT).as_posix()
            if rel == "SHA256SUMS.txt":
                continue
            h = hashlib.sha256(p.read_bytes()).hexdigest()
            lines.append(f"{h}  {rel}")
        (ROOT / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n")
        print(f"  {len(lines)} files hashed")
        written(ROOT / "SHA256SUMS.txt")

        header("16.2 zip")
        outdir = Path(a.out)
        outdir.mkdir(parents=True, exist_ok=True)
        zip_path = outdir / f"{a.name}.zip"
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
            for p in shipped_files(ROOT) + [ROOT / "SHA256SUMS.txt"]:
                z.write(p, Path(a.name) / p.relative_to(ROOT))
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        print(f"  {zip_path}")
        print(f"  bytes   {zip_path.stat().st_size:,}")
        print(f"  sha256  {digest}")
        (outdir / f"{a.name}.zip.sha256").write_text(f"{digest}  {zip_path.name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
