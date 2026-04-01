#!/usr/bin/env python3
"""One-command article job starter with rich intake parameters."""
from __future__ import annotations

import argparse
import subprocess
import sys
import yaml
from pathlib import Path

from lib import ROOT, now_iso

SCRIPTS = ROOT / "scripts"


def run(cmd: list[str]) -> str:
    out = subprocess.check_output(cmd, text=True)
    return out.strip()


def main() -> int:
    p = argparse.ArgumentParser(description="Start a new article job")
    p.add_argument("job_id", help="Job identifier (e.g., 2026-03-30-topic-name)")
    p.add_argument("--title", required=True, help="Article title hint")
    p.add_argument("--audience", default="", help="Target audience description")
    p.add_argument("--core-question", action="append", default=[], help="Core research question(s)")
    p.add_argument("--thesis", default="", help="Working thesis")
    p.add_argument("--sources", action="append", default=[], help="Known source URLs")
    p.add_argument("--must-do", action="append", default=[], help="Must-do constraints")
    p.add_argument("--must-avoid", action="append", default=[], help="Additional must-avoid items")
    p.add_argument("--publish-repo", default="", help="Target publish repo path")
    p.add_argument("--notes", default="", help="Additional notes")
    p.add_argument("--task-note", default="", help="Task note for automation state")
    p.add_argument("--next-deliverable", default="evidence map", help="Next expected deliverable")
    p.add_argument("--no-automation", action="store_true", help="Skip automation state activation")
    args = p.parse_args()

    # Create job
    job_path = run([sys.executable, str(SCRIPTS / "create_article_job.py"), args.job_id])
    job_dir = Path(job_path)

    # Build deep research packet
    run([sys.executable, str(SCRIPTS / "build_deep_research_packet.py"), job_path])

    # Enrich intake.yaml
    intake_path = job_dir / "intake.yaml"
    intake = yaml.safe_load(intake_path.read_text())

    intake["title_hint"] = args.title
    if args.audience:
        intake["audience"] = args.audience
    if args.core_question:
        intake["core_question"] = args.core_question
    if args.thesis:
        intake["working_thesis"] = args.thesis
    if args.sources:
        intake["known_sources"] = args.sources
    if args.must_do:
        intake["must_do"] = args.must_do
    if args.must_avoid:
        intake["must_avoid"] = intake.get("must_avoid", []) + args.must_avoid
    if args.publish_repo:
        intake.setdefault("publish_target", {})["repo"] = args.publish_repo
    if args.notes:
        intake["notes"] = args.notes

    intake_path.write_text(yaml.dump(intake, allow_unicode=True, default_flow_style=False, sort_keys=False))

    # Update state.json with title
    import json
    from lib import load_state, save_state
    state = load_state(job_dir)
    state["title"] = args.title
    state["status"] = "intake"
    state["nextStep"] = "scope → generate deep research prompt"
    if args.publish_repo:
        state.setdefault("publish", {})["repo"] = args.publish_repo
    save_state(job_dir, state)

    # Activate automation
    if not args.no_automation:
        task_note = args.task_note or f"Article: {args.title}"
        run([
            sys.executable, str(SCRIPTS / "sync_automation_state.py"),
            "start", args.job_id, task_note, args.next_deliverable,
        ])

    print(f"Job created: {job_path}")
    print(f"Title: {args.title}")
    print(f"Next: Fill intake details → run_deep_research.py {args.job_id} generate-prompt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
