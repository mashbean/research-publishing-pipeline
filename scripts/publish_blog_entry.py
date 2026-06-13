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
        "extraFiles": [str(path) for path in optional_assets],
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
        "extraFiles": [str(path) for path in optional_assets],
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
