"""Shared plumbing for the runner scripts: path setup, section headers, and a
consistent way to record that a stage passed or failed.

Each script under scripts/ is a thin front end. All the logic lives in the
moduleb package, so a script can be read top to bottom in a minute and the thing
it calls can be unit tested.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd  # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 80)
pd.set_option("display.max_rows", 300)

FMT = lambda x: f"{x:,.5f}" if isinstance(x, float) else str(x)   # noqa: E731


def header(title: str) -> None:
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def sub(title: str) -> None:
    print(f"\n--- {title} " + "-" * max(0, 70 - len(title)))


def show(df: pd.DataFrame, floatfmt: str = "{:,.5f}") -> None:
    print(df.to_string(index=False, float_format=lambda x: floatfmt.format(x)))


class Stage:
    """Context manager that times a stage and turns an exception into a clear,
    non-zero exit instead of a half-written results file."""

    def __init__(self, name: str):
        self.name = name

    def __enter__(self):
        header(self.name)
        self.t0 = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        dt = time.time() - self.t0
        if exc_type is None:
            print(f"\n[OK] {self.name} ({dt:.1f}s)")
            return False
        print(f"\n[FAILED] {self.name} ({dt:.1f}s): {exc_type.__name__}: {exc}", file=sys.stderr)
        return False


def written(path) -> None:
    print(f"[written] {Path(path).relative_to(ROOT)}")
