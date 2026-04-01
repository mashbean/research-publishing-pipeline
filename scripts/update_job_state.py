#!/usr/bin/env python3
"""Advance or update a job's state with transition validation."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from lib import (
    resolve_job_dir, load_state, save_state,
    is_valid_transition, now_iso, ALL_STATUSES,
)


def main() -> int:
    p = argparse.ArgumentParser(description="Update job state with transition validation")
    p.add_argument("job", help="Job ID or path to job directory")
    p.add_argument("--status", help="New status (must be valid transition)")
    p.add_argument("--next-step", help="Description of next step")
    p.add_argument("--last-deliverable", help="Path to last deliverable (relative to job dir)")
    p.add_argument("--blocked-reason", help="Why the job is blocked")
    p.add_argument("--title", help="Update article title")
    p.add_argument("--publish-repo", help="Target publish repo")
    p.add_argument("--publish-file", help="Target file path in repo")
    p.add_argument("--deploy-run", help="Deploy workflow run ID")
    p.add_argument("--canonical-url", help="Canonical URL after publish")
    p.add_argument("--add-version-note", help="Add a version note to versions[]")
    p.add_argument("--force", action="store_true", help="Skip transition validation")
    args = p.parse_args()

    try:
        job_dir = resolve_job_dir(args.job)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    state = load_state(job_dir)
    current = state.get("status", "intake")

    # Status transition
    if args.status:
        if args.status not in ALL_STATUSES:
            print(f"Unknown status: {args.status}. Valid: {sorted(ALL_STATUSES)}", file=sys.stderr)
            return 1
        if not args.force and not is_valid_transition(current, args.status):
            print(
                f"Invalid transition: {current} → {args.status}. "
                f"Use --force to override.",
                file=sys.stderr,
            )
            return 1
        state["status"] = args.status

    # Deliverable validation
    if args.last_deliverable:
        deliverable_path = job_dir / args.last_deliverable
        if not deliverable_path.exists():
            print(f"Deliverable not found: {deliverable_path}", file=sys.stderr)
            return 1
        state["lastDeliverable"] = args.last_deliverable

    # Simple field updates
    if args.next_step:
        state["nextStep"] = args.next_step
    if args.blocked_reason:
        state["blockedReason"] = args.blocked_reason
    if args.title:
        state["title"] = args.title
    if args.publish_repo:
        state.setdefault("publish", {})["repo"] = args.publish_repo
    if args.publish_file:
        state.setdefault("publish", {})["file"] = args.publish_file
    if args.deploy_run:
        state.setdefault("publish", {})["deployRun"] = args.deploy_run
    if args.canonical_url:
        state.setdefault("publish", {})["canonicalUrl"] = args.canonical_url

    # Version tracking
    if args.add_version_note:
        versions = state.setdefault("versions", [])
        versions.append({"note": args.add_version_note, "at": now_iso()})

    save_state(job_dir, state)
    print(f"[{state['jobId']}] {current} → {state['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
