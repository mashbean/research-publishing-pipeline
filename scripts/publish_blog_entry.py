#!/usr/bin/env python3
"""Publish article to blog repo: copy file, git commit+push, update job state."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lib import resolve_job_dir, load_state, save_state, now_iso


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True, text=True)


def main() -> int:
    if len(sys.argv) < 5:
        print(
            "usage: publish_blog_entry.py <job-id-or-path> <repo-dir> "
            "<target-path-in-repo> <commit-message>",
            file=sys.stderr,
        )
        return 1

    job_ref = sys.argv[1]
    repo_dir = Path(sys.argv[2]).resolve()
    target_rel = Path(sys.argv[3])
    commit_message = sys.argv[4]

    try:
        job_dir = resolve_job_dir(job_ref)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    state = load_state(job_dir)

    # Find the latest final article
    final_dir = job_dir / "final"
    candidates = sorted(final_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        print("No article found in final/ directory", file=sys.stderr)
        return 1
    source = candidates[0]

    # Copy to repo
    target = repo_dir / target_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source.read_text())

    # Git operations
    try:
        run(["git", "add", str(target_rel)], repo_dir)
        run(["git", "commit", "-m", commit_message], repo_dir)
        result = run(["git", "push"], repo_dir)
    except subprocess.CalledProcessError as e:
        state["status"] = "publish-failed"
        state["blockedReason"] = f"Git operation failed: {e.stderr[:200]}"
        state["nextStep"] = "Fix git error and retry publish"
        save_state(job_dir, state)
        print(f"Publish failed: {e.stderr}", file=sys.stderr)
        return 1

    # Get commit SHA
    try:
        sha_result = run(["git", "rev-parse", "HEAD"], repo_dir)
        commit_sha = sha_result.stdout.strip()
    except subprocess.CalledProcessError:
        commit_sha = ""

    # Try to get deploy run ID (GitHub Actions)
    deploy_run = ""
    try:
        gh_result = run(
            ["gh", "run", "list", "--limit", "1", "--json", "databaseId", "-q", ".[0].databaseId"],
            repo_dir,
        )
        deploy_run = gh_result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Update state
    state["status"] = "published"
    state["nextStep"] = "等待 deploy 完成 → live URL 驗證"
    state["lastDeliverable"] = f"commit {commit_sha[:8]}"
    state["blockedReason"] = ""
    state.setdefault("publish", {}).update({
        "repo": str(repo_dir),
        "file": str(target_rel),
        "deployRun": deploy_run,
        "commitSha": commit_sha,
    })
    versions = state.setdefault("versions", [])
    versions.append({"note": f"Published to {target_rel}", "at": now_iso()})
    save_state(job_dir, state)

    # Write publish record
    publish_record = {
        "action": "publish",
        "source": str(source),
        "target": str(target),
        "commitSha": commit_sha,
        "deployRun": deploy_run,
        "at": now_iso(),
    }
    record_path = job_dir / "publish" / "publish-record.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(publish_record, ensure_ascii=False, indent=2) + "\n")

    print(f"Published: {source.name} → {target_rel}")
    print(f"Commit: {commit_sha[:8]}")
    if deploy_run:
        print(f"Deploy run: {deploy_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
