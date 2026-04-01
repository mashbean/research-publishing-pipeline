#!/usr/bin/env python3
"""
Pipeline orchestrator — run the next available step for an article job.

Usage:
  # Run the next step automatically
  run_pipeline.py <job> next

  # Run a specific step
  run_pipeline.py <job> <step-name>

  # Show current status and what to do next
  run_pipeline.py <job> status

  # Run all steps until blocked or needs human input
  run_pipeline.py <job> auto

Available steps:
  scope, generate-prompt, integrate-research, draft, fact-check,
  rewrite, editorial-pass, publish, verify
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lib import (
    resolve_job_dir, load_state, save_state, now_iso,
    FORWARD_TRANSITIONS, TERMINAL_STATES, ROOT,
)

SCRIPTS = ROOT / "scripts"


# ─── Step definitions ──────────────────────────────────────────────────

def step_scope(job_dir: Path, state: dict) -> str | None:
    """intake → scoped: validate intake is filled."""
    import yaml
    intake = yaml.safe_load((job_dir / "intake.yaml").read_text())
    required = ["title_hint", "core_question", "audience"]
    missing = [f for f in required if not intake.get(f) or intake[f] in ("", [""])]
    if missing:
        return f"intake.yaml missing: {', '.join(missing)} — fill these before scoping"
    state["status"] = "scoped"
    state["nextStep"] = "generate deep research prompt"
    state["lastDeliverable"] = "intake.yaml"
    save_state(job_dir, state)
    return None


def step_generate_prompt(job_dir: Path, state: dict) -> str | None:
    """scoped → researching: generate deep research prompt."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "run_deep_research.py"), str(job_dir), "generate-prompt"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return f"Failed to generate prompt: {result.stderr}"
    # State is updated by run_deep_research.py
    return None


def step_integrate_research(job_dir: Path, state: dict) -> str | None:
    """researching → evidence-mapped/drafted: integrate deep research results."""
    raw = job_dir / "raw" / "deep-research-output.md"
    if not raw.exists():
        return (
            "Deep Research 結果尚未就緒。\n"
            "請將 Deep Research 輸出存到 raw/deep-research-output.md，\n"
            "或執行: run_deep_research.py <job> save-raw <file>"
        )
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "run_deep_research.py"), str(job_dir), "integrate"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return f"Integration failed: {result.stderr}"
    print(result.stdout)
    return None


def step_fact_check(job_dir: Path, state: dict) -> str | None:
    """drafted → fact-checking: validate draft exists, create fact-check template."""
    draft = None
    for name in ["research-draft.md", "blog-rewrite.md"]:
        if (job_dir / "drafts" / name).exists():
            draft = job_dir / "drafts" / name
    if not draft:
        return "No draft found in drafts/"

    fc = job_dir / "verification" / "fact-check-report.md"
    if not fc.exists():
        template = (ROOT / "templates" / "fact-check-report.md").read_text()
        fc.parent.mkdir(parents=True, exist_ok=True)
        fc.write_text(template)
        print(f"Created fact-check template: {fc}")

    state["status"] = "fact-checking"
    state["nextStep"] = "Complete fact-check-report.md → rewrite"
    state["lastDeliverable"] = f"drafts/{draft.name}"
    save_state(job_dir, state)
    return None


def step_editorial_pass(job_dir: Path, state: dict) -> str | None:
    """rewritten → editorial-pass or ready-to-publish: run automated checks."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "run_editorial_pass.py"), str(job_dir), "--auto-advance"],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        state["status"] = "editorial-pass"
        state["nextStep"] = "Fix editorial issues → re-run editorial pass"
        state["lastDeliverable"] = "verification/editorial-pass-report.md"
        save_state(job_dir, state)
        return "Editorial pass found issues — see verification/editorial-pass-report.md"
    # State updated by run_editorial_pass.py --auto-advance
    return None


def step_publish(job_dir: Path, state: dict) -> str | None:
    """ready-to-publish → published: needs repo + target path."""
    publish = state.get("publish", {})
    repo = publish.get("repo", "")
    target_file = publish.get("file", "")
    if not repo or not target_file:
        return (
            "publish.repo 和 publish.file 必須設定。\n"
            "使用 update_job_state.py 設定:\n"
            f"  update_job_state.py {state['jobId']} --publish-repo <path> --publish-file <path>"
        )

    title = state.get("title", state["jobId"])
    commit_msg = f"feat(blog): publish {title}"

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "publish_blog_entry.py"),
         str(job_dir), repo, target_file, commit_msg],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        return f"Publish failed: {result.stderr}"
    return None


def step_verify(job_dir: Path, state: dict) -> str | None:
    """published → verified: verify live URL."""
    publish = state.get("publish", {})
    canonical = publish.get("canonicalUrl", "")
    if not canonical:
        return (
            "canonicalUrl 尚未設定。\n"
            "使用 update_job_state.py 設定:\n"
            f"  update_job_state.py {state['jobId']} --canonical-url <url>"
        )

    title = state.get("title", "")
    if not title:
        return "Job title not set — cannot verify"

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_publish.py"),
         str(job_dir), canonical, title],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode not in (0, 2):
        return f"Verification error: {result.stderr}"
    return None


def step_validate(job_dir: Path, state: dict) -> str | None:
    """Run completeness check for current status."""
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_job_completeness.py"), str(job_dir)],
        capture_output=True, text=True,
    )
    print(result.stdout)
    return None


# ─── Status → step mapping ──────────────────────────────────────────

NEXT_STEP: dict[str, callable] = {
    "intake": step_scope,
    "scoped": step_generate_prompt,
    "researching": step_integrate_research,
    "evidence-mapped": step_fact_check,  # skip straight if evidence-mapped
    "drafted": step_fact_check,
    "fact-checking": None,  # needs human: complete fact-check-report
    "rewritten": step_editorial_pass,
    "editorial-pass": step_editorial_pass,
    "ready-to-publish": step_publish,
    "published": step_verify,
}

# Steps that can be triggered on demand (not just from NEXT_STEP)
NAMED_STEPS = {
    "scope": step_scope,
    "generate-prompt": step_generate_prompt,
    "integrate-research": step_integrate_research,
    "fact-check": step_fact_check,
    "editorial-pass": step_editorial_pass,
    "publish": step_publish,
    "verify": step_verify,
    "validate": step_validate,
}

# Steps that need human input
HUMAN_REQUIRED = {
    "fact-checking": "Complete fact-check-report.md, then update state to 'rewritten'",
    "blocked": "Resolve blocked reason, then update state",
    "needs-decision": "Make decision, then update state",
}


def show_status(job_dir: Path) -> int:
    state = load_state(job_dir)
    status = state["status"]

    print(f"Job:    {state['jobId']}")
    print(f"Title:  {state.get('title', '(not set)')}")
    print(f"Status: {status}")

    if status in TERMINAL_STATES:
        print(f"→ Terminal state reached.")
        return 0

    if status in HUMAN_REQUIRED:
        print(f"→ Needs human: {HUMAN_REQUIRED[status]}")
        return 0

    step_fn = NEXT_STEP.get(status)
    if step_fn:
        print(f"→ Next auto step: {step_fn.__name__}")
    else:
        print(f"→ No automatic step available")

    if state.get("nextStep"):
        print(f"→ Planned: {state['nextStep']}")
    if state.get("blockedReason"):
        print(f"→ Blocked: {state['blockedReason']}")

    # Completeness
    subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_job_completeness.py"), str(job_dir)],
        capture_output=False,
    )
    return 0


def run_next(job_dir: Path) -> int:
    state = load_state(job_dir)
    status = state["status"]

    if status in TERMINAL_STATES:
        print(f"Job is in terminal state: {status}")
        return 0

    if status in HUMAN_REQUIRED:
        print(f"Waiting for human input: {HUMAN_REQUIRED[status]}")
        return 1

    step_fn = NEXT_STEP.get(status)
    if not step_fn:
        print(f"No automatic step for status: {status}")
        return 1

    print(f"Running: {step_fn.__name__} (status: {status})")
    blocked = step_fn(job_dir, state)
    if blocked:
        print(f"\nBlocked: {blocked}")
        return 1

    # Reload state (step may have updated it)
    state = load_state(job_dir)
    save_state(job_dir, state)
    print(f"\n→ Status: {state['status']}")
    return 0


def run_auto(job_dir: Path) -> int:
    """Run steps until blocked or terminal."""
    max_steps = 10
    for i in range(max_steps):
        state = load_state(job_dir)
        status = state["status"]

        if status in TERMINAL_STATES:
            print(f"\n{'='*40}")
            print(f"Reached terminal state: {status}")
            return 0

        if status in HUMAN_REQUIRED:
            print(f"\n{'='*40}")
            print(f"Paused — needs human: {HUMAN_REQUIRED[status]}")
            return 0

        step_fn = NEXT_STEP.get(status)
        if not step_fn:
            print(f"\n{'='*40}")
            print(f"No auto step for: {status}")
            return 0

        print(f"\n{'='*40}")
        print(f"Step {i+1}: {step_fn.__name__} (status: {status})")
        blocked = step_fn(job_dir, state)
        if blocked:
            print(f"\nBlocked: {blocked}")
            return 1

        # Reload
        state = load_state(job_dir)
        save_state(job_dir, state)

    print(f"\nReached max steps ({max_steps})")
    return 0


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        return 1

    job_ref = sys.argv[1]
    action = sys.argv[2]

    try:
        job_dir = resolve_job_dir(job_ref)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    if action == "status":
        return show_status(job_dir)
    elif action == "next":
        return run_next(job_dir)
    elif action == "auto":
        return run_auto(job_dir)
    elif action in NAMED_STEPS:
        state = load_state(job_dir)
        print(f"Running: {action} (status: {state['status']})")
        blocked = NAMED_STEPS[action](job_dir, state)
        if blocked:
            print(f"\nBlocked: {blocked}")
            return 1
        state = load_state(job_dir)
        save_state(job_dir, state)
        print(f"\n→ Status: {state['status']}")
        return 0
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        print(f"Available: status, next, auto, {', '.join(sorted(NAMED_STEPS))}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
