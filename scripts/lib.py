"""Shared utilities for research-publishing-pipeline scripts."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TZ = timezone(timedelta(hours=8))

# Valid state machine transitions (forward)
FORWARD_TRANSITIONS: dict[str, list[str]] = {
    "intake": ["scoped"],
    "scoped": ["researching"],
    "researching": ["evidence-mapped"],
    "evidence-mapped": ["drafted"],
    "drafted": ["fact-checking"],
    "fact-checking": ["rewritten", "researching"],          # backtrack: evidence gaps
    # PASS → accent-pending (opt-in accent) or readability-pending (academic default); FAIL → editorial-pass
    "rewritten": ["editorial-pass", "accent-pending", "readability-pending", "fact-checking"],
    "editorial-pass": ["accent-pending", "readability-pending", "rewritten"],
    "accent-pending": ["ready-to-publish", "rewritten"],    # accent done → ready; major issue → back to rewrite
    # Academic/no-accent branch: strip argumentative scaffolding before publish (added 2026-07-30).
    # accent-pass used to cover readability implicitly; academic mode disables it, so this
    # stage owns readability instead. See prompts/agent-readability.md.
    "readability-pending": ["ready-to-publish", "rewritten"],
    "ready-to-publish": ["published"],
    "published": ["verified", "publish-failed"],
    "verified": ["social-shared"],
    "social-shared": [],
}

# Any status can go to these exception states
EXCEPTION_STATES = {"blocked", "needs-decision", "publish-failed", "verification-failed"}

# Terminal states
TERMINAL_STATES = {"social-shared", "verified", "publish-failed", "verification-failed", "blocked"}

ALL_STATUSES = set(FORWARD_TRANSITIONS.keys()) | EXCEPTION_STATES


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def load_state(job_dir: Path) -> dict:
    return json.loads((job_dir / "state.json").read_text())


def save_state(job_dir: Path, state: dict) -> None:
    state["lastUpdated"] = now_iso()
    (job_dir / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n"
    )


def is_valid_transition(current: str, target: str) -> bool:
    if target in EXCEPTION_STATES:
        return True
    return target in FORWARD_TRANSITIONS.get(current, [])


def resolve_job_dir(job_id_or_path: str) -> Path:
    """Resolve a job-id or path to a job directory."""
    p = Path(job_id_or_path)
    if p.is_dir() and (p / "state.json").exists():
        return p.resolve()
    candidate = ROOT / "jobs" / job_id_or_path
    if candidate.is_dir() and (candidate / "state.json").exists():
        return candidate.resolve()
    raise FileNotFoundError(f"Cannot find job: {job_id_or_path}")
