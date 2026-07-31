#!/usr/bin/env python3
"""Publish article to blog repo: copy file, git commit+push, update job state."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from lib import resolve_job_dir, load_state, save_state, now_iso
from deploy_run import DeployRunNotFound, resolve_deploy_run

# How long to wait for GitHub to register a workflow run for the pushed commit.
DEPLOY_RUN_TIMEOUT = 120.0
DEPLOY_RUN_INTERVAL = 5.0


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), check=True, capture_output=True, text=True)


def take_opt(argv: list[str], name: str, default: str = "") -> str:
    """Pop `--name value` out of argv so positional parsing stays simple."""
    if name not in argv:
        return default
    idx = argv.index(name)
    if idx + 1 >= len(argv):
        raise SystemExit(f"{name} requires a value")
    value = argv[idx + 1]
    del argv[idx:idx + 2]
    return value


def take_flag(argv: list[str], name: str) -> bool:
    if name in argv:
        argv.remove(name)
        return True
    return False


def slug_from_argmap(path: Path, fallback: str) -> str:
    if not path.exists():
        return fallback

    try:
        import yaml
        data = yaml.safe_load(path.read_text())
        if isinstance(data, dict) and isinstance(data.get("slug"), str) and data["slug"].strip():
            return data["slug"].strip()
    except Exception:
        pass

    for line in path.read_text().splitlines():
        if line.startswith("slug:"):
            return line.split(":", 1)[1].strip().strip("'\"") or fallback
    return fallback


def copy_optional_argmap_assets(job_dir: Path, repo_dir: Path, target_rel: Path) -> list[Path]:
    final_dir = job_dir / "final"
    argmap_yaml = final_dir / "argmap.yaml"
    argdown = final_dir / "argument.argdown"
    slug = slug_from_argmap(argmap_yaml, target_rel.stem)
    staged: list[Path] = []

    if argmap_yaml.exists() and (repo_dir / "src" / "content" / "argmaps").exists():
        rel = Path("src/content/argmaps") / f"{slug}.yaml"
        target = repo_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(argmap_yaml.read_text())
        staged.append(rel)

    if not argdown.exists():
        return staged

    if (repo_dir / "src" / "content").exists():
        rel = Path("src/content/argdowns") / f"{slug}.argdown"
        target = repo_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(argdown.read_text())
        staged.append(rel)

    if (repo_dir / "public").exists():
        render_script = Path(__file__).resolve().parent / "render_argdown_assets.py"
        result = subprocess.run(
            [
                sys.executable,
                str(render_script),
                "--input",
                str(argdown),
                "--output-dir",
                str(repo_dir / "public" / "argdown"),
                "--slug",
                slug,
            ],
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        staged.append(Path("public/argdown") / slug)

    return staged


def main() -> int:
    argv = sys.argv[1:]
    deploy_workflow = take_opt(argv, "--deploy-workflow")
    deploy_timeout = float(take_opt(argv, "--deploy-run-timeout", str(DEPLOY_RUN_TIMEOUT)))
    skip_deploy_run = take_flag(argv, "--no-deploy-run")

    if len(argv) < 4:
        print(
            "usage: publish_blog_entry.py <job-id-or-path> <repo-dir> "
            "<target-path-in-repo> <commit-message> "
            "[--deploy-workflow <name>] [--deploy-run-timeout <sec>] [--no-deploy-run]",
            file=sys.stderr,
        )
        return 1

    job_ref = argv[0]
    repo_dir = Path(argv[1]).resolve()
    target_rel = Path(argv[2])
    commit_message = argv[3]

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

    try:
        optional_assets = copy_optional_argmap_assets(job_dir, repo_dir, target_rel)
    except RuntimeError as e:
        state["status"] = "publish-failed"
        state["blockedReason"] = f"Argdown render failed: {str(e)[:200]}"
        state["nextStep"] = "Fix Argdown render error and retry publish"
        save_state(job_dir, state)
        print(f"Publish failed: {e}", file=sys.stderr)
        return 1

    # Git operations
    try:
        run(["git", "add", str(target_rel), *[str(path) for path in optional_assets]], repo_dir)
        run(["git", "commit", "-m", commit_message], repo_dir)
        result = run(["git", "push"], repo_dir)
    except subprocess.CalledProcessError as e:
        state["status"] = "publish-failed"
        state["blockedReason"] = f"Git operation failed: {e.stderr[:200]}"
        state["nextStep"] = "Fix git error and retry publish"
        save_state(job_dir, state)
        print(f"Publish failed: {e.stderr}", file=sys.stderr)
        return 1

    # Get commit SHA — this is what the deploy run must be matched against.
    try:
        sha_result = run(["git", "rev-parse", "HEAD"], repo_dir)
        commit_sha = sha_result.stdout.strip()
    except subprocess.CalledProcessError:
        commit_sha = ""

    # Resolve the GitHub Actions run *for this commit*. GitHub takes a few
    # seconds to register it, so poll on headSha instead of grabbing the newest
    # run — the newest run right after a push is still the previous commit's.
    deploy_run = ""
    deploy_run_sha = ""
    deploy_run_url = ""
    deploy_run_workflow = ""
    deploy_runs: list[dict] = []
    deploy_run_error = ""

    if skip_deploy_run:
        deploy_run_error = "skipped (--no-deploy-run)"
    elif not commit_sha:
        deploy_run_error = "commit SHA unavailable — cannot attribute a deploy run"
    else:
        try:
            resolved = resolve_deploy_run(
                commit_sha,
                repo_dir,
                timeout=deploy_timeout,
                interval=DEPLOY_RUN_INTERVAL,
                workflow=deploy_workflow or None,
                on_wait=lambda n, total: print(
                    f"  waiting for GitHub to register a run for {commit_sha[:8]} "
                    f"({n}/{total})..."
                ),
            )
            primary = resolved["run"]
            deploy_runs = resolved["runs"]
            deploy_run = str(primary.get("databaseId", ""))
            deploy_run_sha = primary.get("headSha", "")
            deploy_run_url = primary.get("url", "")
            deploy_run_workflow = primary.get("workflowName", "")
        except (DeployRunNotFound, subprocess.CalledProcessError, FileNotFoundError,
                json.JSONDecodeError, ValueError) as e:
            deploy_run_error = f"{type(e).__name__}: {str(e)[:200]}"

    # Update state
    state["status"] = "published"
    state["nextStep"] = "等待 deploy 完成 → live URL 驗證"
    state["lastDeliverable"] = f"commit {commit_sha[:8]}"
    state["blockedReason"] = ""
    publish_state = {
        "repo": str(repo_dir),
        "file": str(target_rel),
        "extraFiles": [str(path) for path in optional_assets],
        "deployRun": deploy_run,
        "deployRunSha": deploy_run_sha,
        "deployRunUrl": deploy_run_url,
        "deployWorkflow": deploy_run_workflow,
        "deployRunError": deploy_run_error,
        "commitSha": commit_sha,
    }
    if len(deploy_runs) > 1:
        # Several workflows fired on this commit; keep them all so an ambiguous
        # pick can be audited later.
        publish_state["deployRunCandidates"] = [
            {"id": str(r.get("databaseId", "")), "workflow": r.get("workflowName", "")}
            for r in deploy_runs
        ]
    state.setdefault("publish", {}).update(publish_state)
    if deploy_run_error and not skip_deploy_run:
        state["nextStep"] = (
            "無法為本次 commit 找到 deploy run — 手動確認 deploy 後再跑 verify"
        )
    versions = state.setdefault("versions", [])
    versions.append({"note": f"Published to {target_rel}", "at": now_iso()})
    save_state(job_dir, state)

    # Write publish record
    publish_record = {
        "action": "publish",
        "source": str(source),
        "target": str(target),
        "extraFiles": [str(path) for path in optional_assets],
        "commitSha": commit_sha,
        "deployRun": deploy_run,
        "deployRunSha": deploy_run_sha,
        "deployRunUrl": deploy_run_url,
        "deployWorkflow": deploy_run_workflow,
        "deployRunError": deploy_run_error,
        "at": now_iso(),
    }
    record_path = job_dir / "publish" / "publish-record.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(publish_record, ensure_ascii=False, indent=2) + "\n")

    print(f"Published: {source.name} → {target_rel}")
    print(f"Commit: {commit_sha[:8]}")
    if deploy_run:
        print(f"Deploy run: {deploy_run} ({deploy_run_workflow}) @ {deploy_run_sha[:8]}")
        if len(deploy_runs) > 1:
            others = ", ".join(
                f"{r.get('databaseId')} ({r.get('workflowName')})" for r in deploy_runs[1:]
            )
            print(f"  note: commit also triggered {others}")
    elif skip_deploy_run:
        print("Deploy run: not looked up (--no-deploy-run)")
    else:
        # Loud, on stdout, because run_pipeline.py only echoes stdout on success.
        print(
            f"WARNING: no deploy run recorded for {commit_sha[:8]} — {deploy_run_error}\n"
            f"  The push itself succeeded. Deliberately NOT falling back to the "
            f"newest run: an unrelated run ID reads as a green deploy.\n"
            f"  Check manually: gh run list --json databaseId,headSha "
            f"--jq '.[] | select(.headSha==\"{commit_sha}\")'"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
