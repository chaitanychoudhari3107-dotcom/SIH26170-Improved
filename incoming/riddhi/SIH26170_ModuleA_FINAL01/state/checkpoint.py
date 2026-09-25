"""Durable progress record, so an interrupted session can be resumed exactly.

Every stage in the hardening phase calls `mark()` when it finishes. The file it
writes is the handover: `CONTINUATION.md` explains how to read it, and a fresh
session needs nothing else to pick up where this one stopped.

This is deliberately dumb — a JSON file and two functions. A resume mechanism that
can itself fail is worse than none, because it tells you work is safe when it is not.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

PATH = Path(__file__).resolve().parent / "CHECKPOINT.json"


def read() -> dict:
    return json.loads(PATH.read_text())


def write(state: dict) -> None:
    state["updated_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    PATH.write_text(json.dumps(state, indent=2))


def mark(step: str, status: str, detail: str = "", artifacts: list | None = None,
         next_action: str | None = None, blocked_on: str | None = None) -> dict:
    """Record one step. `status` is DONE, FAILED or SKIPPED."""
    if status not in {"DONE", "FAILED", "SKIPPED"}:
        raise ValueError("status must be DONE, FAILED or SKIPPED")
    state = read()
    state["steps"] = [s for s in state["steps"] if s["step"] != step]
    state["steps"].append({
        "step": step, "status": status, "detail": detail,
        "artifacts": artifacts or [],
        "at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    state["steps"].sort(key=lambda s: s["step"])
    if next_action is not None:
        state["next_action"] = next_action
    state["blocked_on"] = blocked_on
    write(state)
    return state


def summary() -> str:
    state = read()
    done = [s["step"] for s in state["steps"] if s["status"] == "DONE"]
    failed = [s["step"] for s in state["steps"] if s["status"] == "FAILED"]
    lines = [f"phase      : {state['phase']}",
             f"updated    : {state['updated_utc']}",
             f"done       : {len(done)} step(s)"]
    lines += [f"             - {s}" for s in done]
    if failed:
        lines.append(f"FAILED     : {', '.join(failed)}")
    lines.append(f"next action: {state['next_action']}")
    if state.get("blocked_on"):
        lines.append(f"BLOCKED ON : {state['blocked_on']}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary())
