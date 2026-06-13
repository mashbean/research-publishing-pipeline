#!/usr/bin/env python3
"""Validate that a job has the required deliverables for its current status."""
from __future__ import annotations

import sys
from pathlib import Path

from lib import resolve_job_dir, load_state


# Required deliverables by status (cumulative — each stage adds to prior)
REQUIRED_FILES: dict[str, list[str]] = {
    "intake": [
        "intake.yaml",
    ],
    "scoped": [
        "intake.yaml",
    ],
    "researching": [
        "intake.yaml",
        "deep-research-packet.yaml",
    ],
    "evidence-mapped": [
        "intake.yaml",
        "deep-research-packet.yaml",
        "verification/evidence-map.md",
        "notes/reasoning-chain.md",
    ],
    "drafted": [
        "intake.yaml",
        "verification/evidence-map.md",
        "notes/reasoning-chain.md",
        "drafts/research-draft.md",
    ],
    "fact-checking": [
        "intake.yaml",
        "verification/evidence-map.md",
        "notes/reasoning-chain.md",
        "drafts/research-draft.md",
        "verification/fact-check-report.md",
    ],
    "rewritten": [
        "intake.yaml",
        "verification/evidence-map.md",
        "verification/fact-check-report.md",
        "drafts/blog-rewrite.md",
    ],
    "editorial-pass": [
        "intake.yaml",
        "verification/evidence-map.md",
        "verification/fact-check-report.md",
        "verification/editorial-pass-report.md",
    ],
    "ready-to-publish": [
        "intake.yaml",
        "verification/evidence-map.md",
        "verification/fact-check-report.md",
        "final/*",   # at least one file in final/
    ],
    "published": [
        "final/*",
    ],
    "verified": [
        "final/*",
        "publish/live-check.json",
    ],
}


def glob_check(job_dir: Path, pattern: str) -> bool:
    """Check if a glob pattern matches any file."""
    if "*" in pattern:
        return bool(list(job_dir.glob(pattern)))
    return (job_dir / pattern).exists()


def validate(job_dir: Path, status: str | None = None) -> dict:
    state = load_state(job_dir)
    check_status = status or state["status"]
    required = list(REQUIRED_FILES.get(check_status, []))
    if check_status in {"ready-to-publish", "published", "verified", "social-shared"}:
        if (job_dir / "final" / "argmap.yaml").exists():
            required.append("final/argument.argdown")
            required.append("final/argdown-render/*/index.html")
            required.append("final/argdown-render/*/map.svg")

    present = []
    missing = []
    for req in required:
        if glob_check(job_dir, req):
            present.append(req)
        else:
            missing.append(req)

    return {
        "jobId": state["jobId"],
        "status": check_status,
        "complete": len(missing) == 0,
        "present": present,
        "missing": missing,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: validate_job_completeness.py <job-id-or-path> [--status <status>]", file=sys.stderr)
        return 1

    status_override = None
    if "--status" in sys.argv:
        idx = sys.argv.index("--status")
        status_override = sys.argv[idx + 1]
        sys.argv.pop(idx)
        sys.argv.pop(idx)

    try:
        job_dir = resolve_job_dir(sys.argv[1])
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    result = validate(job_dir, status_override)

    print(f"Job: {result['jobId']}")
    print(f"Status: {result['status']}")
    print(f"Complete: {'✓' if result['complete'] else '✗'}")
    if result["present"]:
        print(f"Present ({len(result['present'])}):")
        for f in result["present"]:
            print(f"  ✓ {f}")
    if result["missing"]:
        print(f"Missing ({len(result['missing'])}):")
        for f in result["missing"]:
            print(f"  ✗ {f}")

    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
