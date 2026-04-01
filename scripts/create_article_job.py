#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "jobs" / "_example"
TEMPLATE_STATE = ROOT / "templates" / "state.json"

JOB_SUBDIRS = [
    "raw",
    "sources",
    "notes",
    "drafts",
    "verification",
    "final",
    "publish",
    "prompts",
]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: create_article_job.py <job-id>", file=sys.stderr)
        return 1

    job_id = sys.argv[1].strip()
    if not job_id:
        print("job-id must not be empty", file=sys.stderr)
        return 1

    target = ROOT / "jobs" / job_id
    if target.exists():
        print(f"job already exists: {target}", file=sys.stderr)
        return 1

    # Copy example if it exists, otherwise create from scratch
    if EXAMPLE.exists():
        shutil.copytree(EXAMPLE, target)
    else:
        target.mkdir(parents=True)

    # Ensure all required subdirectories exist
    for subdir in JOB_SUBDIRS:
        (target / subdir).mkdir(exist_ok=True)

    # Copy templates
    shutil.copy2(ROOT / "templates" / "intake.yaml", target / "intake.yaml")
    shutil.copy2(ROOT / "templates" / "deep-research-packet.yaml", target / "deep-research-packet.yaml")
    shutil.copy2(ROOT / "templates" / "fact-check-report.md", target / "verification" / "fact-check-report.md")

    # Initialize state
    state = json.loads(TEMPLATE_STATE.read_text())
    state["jobId"] = job_id
    (target / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")

    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
