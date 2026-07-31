#!/usr/bin/env python3
"""Verify a published article is actually live, then update job state.

Two checks run, with a deliberate hierarchy:

1. **Live content — authoritative.** The canonical URL must serve the article's
   own text: the title *and* a feature string lifted from the body. Only this
   decides `verified` vs `verification-failed`.
2. **Deploy run — diagnostic.** The GitHub Actions run for the published commit,
   re-resolved by `headSha` rather than trusted from state.

The run never carries the verdict by itself. On 2026-07-30 a stale run ID (left
over from an earlier commit) reported success while the live URL still 404'd;
believing it would have marked a broken publish `verified`. So a green run with
missing content is reported as a contradiction, and an in-flight run makes us
wait rather than fail early.
"""
from __future__ import annotations

import html
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lib import resolve_job_dir, load_state, save_state, now_iso
from deploy_run import (
    DeployRunNotFound,
    DeployRunTimeout,
    resolve_deploy_run,
    wait_for_run_completion,
)

USER_AGENT = "OpenClaw research-publishing-pipeline/1.0"

# Characters that Markdown/HTML rendering may rewrite (escaping, emphasis,
# links, smart typography). A feature string containing any of them is not
# guaranteed to survive into the page verbatim, so we skip it.
UNSAFE_FEATURE_CHARS = set('<>&"\'*_`[]()#|~\\{}')

# Sentence terminators: CJK ones always end a sentence; ASCII ones only when
# followed by whitespace, so "1.36 億元" is not split mid-number.
SENTENCE_SPLIT = re.compile(r"(?<=[。！？])|(?<=[.!?])(?=\s)")

BLOCK_PREFIXES = ("#", ">", "-", "*", "+", "|", "!", "```", ":::", "<")
ORDERED_LIST = re.compile(r"^\d+[.)]\s")

LIVE_RETRIES = 3
LIVE_RETRY_INTERVAL = 10.0
DEPLOY_TIMEOUT = 600.0
FETCH_LIMIT = 4_000_000


def strip_frontmatter(text: str) -> str:
    """Drop a leading YAML frontmatter block.

    The opening `---` sits at offset 0 with no newline before it, so it is not
    itself a `\\n---` delimiter — skip past it before looking for the closing one.
    Without this the `description:` field leaks into the body-feature search, and
    a description also renders into `<meta>`, so the "body is live" check would
    pass on a page that rendered no body at all.
    """
    if not text.startswith("---"):
        return text
    parts = text[3:].split("\n---", 1)
    if len(parts) < 2:
        return text
    remainder = parts[1]
    newline = remainder.find("\n")
    return remainder[newline + 1:] if newline != -1 else ""


def derive_body_feature(md_text: str, min_len: int = 16, max_len: int = 60) -> str:
    """Pull a distinctive plain-text sentence out of the article body.

    Used to prove the *body* is live, not just that a route resolves — a title
    can appear in an index page, a nav card, or a stub that renders no content.
    """
    for line in strip_frontmatter(md_text).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(BLOCK_PREFIXES) or ORDERED_LIST.match(stripped):
            continue
        for sentence in SENTENCE_SPLIT.split(stripped):
            candidate = sentence.strip()
            if len(candidate) < min_len:
                continue
            if any(c in UNSAFE_FEATURE_CHARS for c in candidate):
                continue
            return candidate[:max_len]
    return ""


def find_article(job_dir: Path):
    final_dir = job_dir / "final"
    if not final_dir.exists():
        return None
    candidates = sorted(final_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def _fetch_via_curl(url: str, timeout: int, urllib_error) -> tuple:
    """Fallback path: urllib can fail where curl succeeds (TLS/proxy quirks).

    No `--fail` here — a 404 body and its status code are more useful than an
    opaque error while a deploy is still propagating.
    """
    try:
        result = subprocess.run(
            [
                "curl", "--location", "--silent", "--show-error",
                "--max-time", str(timeout), "--user-agent", USER_AGENT,
                "--header", "Cache-Control: no-cache",
                "--write-out", "\n%{http_code}", url,
            ],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as curl_error:
        return 0, f"urllib failed: {urllib_error}; curl failed: {curl_error}"

    raw = result.stdout.decode("utf-8", errors="replace")
    body, _, code = raw.rpartition("\n")
    try:
        return int(code.strip()), body[:FETCH_LIMIT]
    except ValueError:
        return 0, raw[:FETCH_LIMIT]


def fetch_page(url: str, timeout: int = 20) -> tuple:
    """Return (status, body). Status 0 means the request never completed."""
    req = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            # Ask intermediaries for the freshly deployed page, not a cached 404.
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            status = getattr(resp, "status", None) or resp.getcode()
            return status, resp.read(FETCH_LIMIT).decode("utf-8", errors="replace")
    except HTTPError as e:
        try:
            body = e.read(FETCH_LIMIT).decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return e.code, body
    except (URLError, OSError) as urllib_error:
        return _fetch_via_curl(url, timeout, urllib_error)


def check_expectations(body: str, expected: list) -> list:
    """Match each expected string against the page, tolerating HTML escaping."""
    unescaped = html.unescape(body)
    return [
        {
            "label": item["label"],
            "text": item["text"],
            "matched": bool(item["text"]) and (item["text"] in body or item["text"] in unescaped),
        }
        for item in expected
    ]


def check_deploy(state: dict, timeout: float, verbose: bool = True) -> dict:
    """Re-resolve the deploy run for the published commit, by SHA.

    Never trusts `publish.deployRun` on its own — that is exactly the field the
    old "newest run wins" lookup got wrong.
    """
    publish = state.get("publish", {})
    repo = publish.get("repo", "")
    sha = publish.get("commitSha", "")
    recorded = str(publish.get("deployRun", "") or "")
    info = {"commitSha": sha, "recordedRun": recorded}

    if not sha:
        info["error"] = "publish.commitSha not recorded — cannot attribute a run"
        return info
    if not repo or not Path(repo).is_dir():
        info["error"] = f"publish.repo missing or not a directory: {repo!r}"
        return info

    repo_dir = Path(repo)
    try:
        resolved = resolve_deploy_run(
            sha,
            repo_dir,
            timeout=60.0,
            workflow=publish.get("deployWorkflow") or None,
            on_wait=(lambda n, total: print(f"  looking for run for {sha[:8]} ({n}/{total})..."))
            if verbose else None,
        )
    except Exception as e:  # not found / gh missing / auth / transport
        info["error"] = f"{type(e).__name__}: {str(e)[:200]}"
        return info

    run = resolved["run"]
    run_id = str(run.get("databaseId", ""))
    info["run"] = run_id
    info["headSha"] = run.get("headSha", "")
    info["workflow"] = run.get("workflowName", "")

    if recorded and recorded != run_id:
        # The bug this module was written to catch: state points at a run that
        # belongs to some other commit.
        info["recordedRunMismatch"] = True

    if run.get("status") != "completed":
        try:
            run = wait_for_run_completion(
                run_id,
                repo_dir,
                timeout=timeout,
                on_wait=(lambda n, total, st: print(f"  deploy run {run_id} is {st} ({n}/{total})..."))
                if verbose else None,
            )
        except (DeployRunTimeout, OSError, json.JSONDecodeError, subprocess.CalledProcessError) as e:
            info["error"] = f"{type(e).__name__}: {str(e)[:200]}"

    info["status"] = run.get("status", "")
    info["conclusion"] = run.get("conclusion", "")
    return info


def take_opt(argv: list, name: str, default: str = "") -> str:
    if name not in argv:
        return default
    idx = argv.index(name)
    if idx + 1 >= len(argv):
        raise SystemExit(f"{name} requires a value")
    value = argv[idx + 1]
    del argv[idx:idx + 2]
    return value


def take_all(argv: list, name: str) -> list:
    values = []
    while name in argv:
        values.append(take_opt(argv, name))
    return values


def take_flag(argv: list, name: str) -> bool:
    if name in argv:
        argv.remove(name)
        return True
    return False


def main() -> int:
    argv = sys.argv[1:]
    canonical_url = take_opt(argv, "--canonical-url") or None
    extra_expect = take_all(argv, "--expect")
    no_deploy_check = take_flag(argv, "--no-deploy-check")
    no_body_check = take_flag(argv, "--no-body-check")
    deploy_timeout = float(take_opt(argv, "--deploy-timeout", str(DEPLOY_TIMEOUT)))
    retries = max(1, int(take_opt(argv, "--retries", str(LIVE_RETRIES))))
    retry_interval = float(take_opt(argv, "--retry-interval", str(LIVE_RETRY_INTERVAL)))

    if len(argv) < 3:
        print(
            "usage: verify_publish.py <job-id-or-path> <url> <expected-string> "
            "[--canonical-url <url>] [--expect <string>]... [--no-deploy-check] "
            "[--no-body-check] [--deploy-timeout <sec>] [--retries <n>] "
            "[--retry-interval <sec>]",
            file=sys.stderr,
        )
        return 1

    job_ref, url, expected = argv[0], argv[1], argv[2]

    try:
        job_dir = resolve_job_dir(job_ref)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    state = load_state(job_dir)

    # ── Build the expectation set ───────────────────────────────────────
    expectations = [{"label": "title", "text": expected}]
    for text in extra_expect:
        expectations.append({"label": "expect", "text": text})

    if not no_body_check:
        article = find_article(job_dir)
        if article:
            feature = derive_body_feature(article.read_text())
            if feature:
                expectations.append({"label": "body", "text": feature})
            else:
                print("Note: no clean body feature string could be derived — title only")
        else:
            print("Note: no final/*.md found — title only")

    # ── Deploy run (diagnostic, resolved by SHA) ────────────────────────
    deploy = None
    if not no_deploy_check:
        deploy = check_deploy(state, deploy_timeout)
        if deploy.get("run"):
            print(
                f"Deploy run: {deploy['run']} ({deploy.get('workflow', '')}) "
                f"@ {deploy.get('headSha', '')[:8]} "
                f"→ {deploy.get('status', '')}/{deploy.get('conclusion', '')}"
            )
            if deploy.get("recordedRunMismatch"):
                print(
                    f"  NOTE: state recorded run {deploy['recordedRun']}, which is not "
                    f"the run for commit {deploy.get('commitSha', '')[:8]}. "
                    f"Using {deploy['run']}."
                )
        else:
            print(f"Deploy run: unresolved — {deploy.get('error', 'unknown')}")

    # ── Live content (authoritative) ────────────────────────────────────
    status, body, checks, ok = 0, "", [], False
    for attempt in range(retries):
        status, body = fetch_page(url)
        checks = check_expectations(body, expectations)
        ok = bool(checks) and all(c["matched"] for c in checks)
        if ok:
            break
        if attempt < retries - 1:
            missing = ", ".join(c["label"] for c in checks if not c["matched"])
            print(
                f"  live check miss (HTTP {status}, missing: {missing}) — "
                f"retrying in {retry_interval:.0f}s"
            )
            time.sleep(retry_interval)

    result = {
        "url": url,
        "httpStatus": status,
        "expected": expected,
        "checks": checks,
        "matched": ok,
        "at": now_iso(),
    }
    if deploy is not None:
        result["deploy"] = deploy

    # A green deploy that does not serve the article is the exact contradiction
    # this script exists to surface, rather than resolve in the deploy's favour.
    contradiction = ""
    if not ok and deploy and deploy.get("conclusion") == "success":
        contradiction = (
            f"deploy run {deploy.get('run')} succeeded for commit "
            f"{deploy.get('commitSha', '')[:8]} but {url} does not serve the article "
            f"(HTTP {status})"
        )
        result["contradiction"] = contradiction

    # ── Persist ─────────────────────────────────────────────────────────
    check_path = job_dir / "publish" / "live-check.json"
    check_path.parent.mkdir(parents=True, exist_ok=True)
    existing_checks = []
    if check_path.exists():
        try:
            data = json.loads(check_path.read_text())
            existing_checks = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            pass
    existing_checks.append(result)
    check_path.write_text(json.dumps(existing_checks, ensure_ascii=False, indent=2) + "\n")

    if ok:
        state["status"] = "verified"
        state["nextStep"] = ""
        state["blockedReason"] = ""
        state["lastDeliverable"] = "publish/live-check.json"
        state.setdefault("publish", {})["canonicalUrl"] = canonical_url or url
        if deploy and deploy.get("run"):
            # Correct the record so downstream readers get the right run.
            state["publish"]["deployRun"] = deploy["run"]
            state["publish"]["deployRunSha"] = deploy.get("headSha", "")
        versions = state.setdefault("versions", [])
        versions.append({"note": f"Live URL 驗證通過: {url}", "at": now_iso()})
    else:
        missing = ", ".join(c["label"] for c in checks if not c["matched"]) or "unknown"
        state["status"] = "verification-failed"
        state["blockedReason"] = (
            contradiction or f"HTTP {status}, missing on page: {missing} — {url}"
        )
        state["nextStep"] = "Check deploy status, retry verification"

    save_state(job_dir, state)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if contradiction:
        print(f"\nCONTRADICTION: {contradiction}", file=sys.stderr)
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
