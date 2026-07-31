#!/usr/bin/env python3
"""Attribute GitHub Actions runs to a specific commit SHA.

Why this module exists
----------------------
`gh run list --limit 1` returns the newest run *across all workflows*, which is
the wrong answer twice over:

1. GitHub needs a few seconds to register the run for a freshly pushed commit,
   so right after `git push` the newest run is still the **previous** commit's.
2. Repos with more than one workflow (deploy + PR check) interleave runs, so the
   newest run may belong to a different workflow entirely.

Both bit us on 2026-07-30: commit b6024bd1 recorded run 30528951869, which
actually belonged to e3dcddbe and had finished hours earlier. Verification then
read "deploy success" off a stale build while the live URL was still 404.

The rule here: a run is only ever attributed to a commit by matching `headSha`.
When no run can be matched we raise — we never fall back to "the newest one".
"""
from __future__ import annotations

import json
import subprocess
import time

# Fields we pull for every run. `headSha` is the one that matters.
RUN_FIELDS = "databaseId,headSha,status,conclusion,workflowName,createdAt,url,event"

# Used only to disambiguate when several workflows ran on the same commit and
# the caller did not name one explicitly.
DEPLOY_HINTS = ("deploy", "pages", "publish", "release")


class DeployRunNotFound(RuntimeError):
    """No GitHub Actions run could be attributed to a commit SHA."""


class DeployRunTimeout(RuntimeError):
    """A matched run did not reach a terminal state in time."""


def _gh(cmd: list, cwd) -> str:
    """Default command runner. Tests inject a fake in its place."""
    result = subprocess.run(
        cmd, cwd=str(cwd), check=True, capture_output=True, text=True
    )
    return result.stdout


def sha_matches(a: str, b: str) -> bool:
    """Compare SHAs tolerantly: either may be an abbreviation of the other.

    Requires at least 7 shared characters so a truncated/empty value can never
    match everything.
    """
    a = (a or "").strip().lower()
    b = (b or "").strip().lower()
    if not a or not b:
        return False
    n = min(len(a), len(b))
    if n < 7:
        return False
    return a[:n] == b[:n]


def list_runs(repo_dir, limit: int = 50, runner=None) -> list:
    runner = runner or _gh
    out = runner(
        ["gh", "run", "list", "--limit", str(limit), "--json", RUN_FIELDS], repo_dir
    )
    if not (out or "").strip():
        return []
    data = json.loads(out)
    return data if isinstance(data, list) else []


def find_runs_for_sha(
    sha: str, repo_dir, limit: int = 50, workflow: str = None, runner=None
) -> list:
    """Runs whose headSha is `sha`, newest first. Never falls back to latest."""
    if not sha:
        raise ValueError("find_runs_for_sha requires a non-empty commit SHA")
    runs = [
        r for r in list_runs(repo_dir, limit=limit, runner=runner)
        if sha_matches(r.get("headSha", ""), sha)
    ]
    if workflow:
        runs = [r for r in runs if r.get("workflowName") == workflow]
    return runs


def pick_deploy_run(runs: list, workflow: str = None) -> dict:
    """Choose the deploy run among several that share a commit SHA.

    A caller-supplied `workflow` is authoritative. Otherwise a single candidate
    is taken as-is, and only when a commit triggered several workflows do we
    fall back to name hints. Callers record the full list either way, so an
    ambiguous pick stays auditable.
    """
    if not runs:
        raise DeployRunNotFound("no runs to pick from")
    if workflow:
        named = [r for r in runs if r.get("workflowName") == workflow]
        if not named:
            raise DeployRunNotFound(
                "no run named {!r} among {}".format(
                    workflow, [r.get("workflowName") for r in runs]
                )
            )
        return named[0]
    if len(runs) == 1:
        return runs[0]
    hinted = [
        r for r in runs
        if any(h in (r.get("workflowName") or "").lower() for h in DEPLOY_HINTS)
    ]
    if len(hinted) == 1:
        return hinted[0]
    return (hinted or runs)[0]


def wait_for_run_for_sha(
    sha: str,
    repo_dir,
    timeout: float = 120.0,
    interval: float = 5.0,
    workflow: str = None,
    runner=None,
    sleeper=None,
    on_wait=None,
) -> list:
    """Poll until GitHub registers a run for `sha`.

    Raises DeployRunNotFound on timeout rather than returning an unrelated run —
    a wrong run ID is worse than no run ID, because it reads as a green deploy.
    """
    sleeper = sleeper or time.sleep
    attempts = max(1, int(timeout // interval) + 1)
    for attempt in range(attempts):
        runs = find_runs_for_sha(
            sha, repo_dir, workflow=workflow, runner=runner
        )
        if runs:
            return runs
        if attempt < attempts - 1:
            if on_wait:
                on_wait(attempt + 1, attempts)
            sleeper(interval)
    raise DeployRunNotFound(
        "no GitHub Actions run registered for commit {} after {:.0f}s"
        "{}".format(sha[:12], timeout, " (workflow={})".format(workflow) if workflow else "")
    )


def get_run(run_id, repo_dir, runner=None) -> dict:
    runner = runner or _gh
    out = runner(
        ["gh", "run", "view", str(run_id), "--json", RUN_FIELDS], repo_dir
    )
    return json.loads(out) if (out or "").strip() else {}


def wait_for_run_completion(
    run_id,
    repo_dir,
    timeout: float = 900.0,
    interval: float = 15.0,
    runner=None,
    sleeper=None,
    on_wait=None,
) -> dict:
    """Poll a single run until `status == "completed"`."""
    sleeper = sleeper or time.sleep
    attempts = max(1, int(timeout // interval) + 1)
    run = {}
    for attempt in range(attempts):
        run = get_run(run_id, repo_dir, runner=runner)
        if run.get("status") == "completed":
            return run
        if attempt < attempts - 1:
            if on_wait:
                on_wait(attempt + 1, attempts, run.get("status") or "unknown")
            sleeper(interval)
    raise DeployRunTimeout(
        "run {} still {!r} after {:.0f}s".format(
            run_id, run.get("status") or "unknown", timeout
        )
    )


def resolve_deploy_run(
    sha: str,
    repo_dir,
    timeout: float = 120.0,
    interval: float = 5.0,
    workflow: str = None,
    runner=None,
    sleeper=None,
    on_wait=None,
) -> dict:
    """SHA → {"run": <primary>, "runs": [...]}. Raises if nothing matches."""
    runs = wait_for_run_for_sha(
        sha, repo_dir, timeout=timeout, interval=interval,
        workflow=workflow, runner=runner, sleeper=sleeper, on_wait=on_wait,
    )
    return {"run": pick_deploy_run(runs, workflow=workflow), "runs": runs}
