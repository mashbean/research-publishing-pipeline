#!/usr/bin/env python3
"""Verify live URL after publish and update job state."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from urllib.request import Request, urlopen

from lib import resolve_job_dir, load_state, save_state, now_iso


def fetch_text(url: str, limit: int = 65536) -> str:
    req = Request(url, headers={"User-Agent": "OpenClaw research-publishing-pipeline/1.0"})
    try:
        with urlopen(req, timeout=20) as resp:
            return resp.read(limit).decode("utf-8", errors="replace")
    except Exception as urllib_error:
        try:
            result = subprocess.run(
                [
                    "curl", "--fail", "--location", "--silent", "--show-error",
                    "--max-time", "20", "--user-agent",
                    "OpenClaw research-publishing-pipeline/1.0", url,
                ],
                check=True,
                capture_output=True,
            )
            return result.stdout[:limit].decode("utf-8", errors="replace")
        except (subprocess.CalledProcessError, FileNotFoundError) as curl_error:
            raise RuntimeError(f"urllib failed: {urllib_error}; curl failed: {curl_error}") from curl_error


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "usage: verify_publish.py <job-id-or-path> <url> <expected-string> "
            "[--canonical-url <url>]",
            file=sys.stderr,
        )
        return 1

    job_ref = sys.argv[1]
    url = sys.argv[2]
    expected = sys.argv[3]

    canonical_url = None
    if "--canonical-url" in sys.argv:
        idx = sys.argv.index("--canonical-url")
        canonical_url = sys.argv[idx + 1]

    try:
        job_dir = resolve_job_dir(job_ref)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    # Fetch and check
    try:
        body = fetch_text(url)
        ok = expected in body
    except Exception as e:
        ok = False
        body = f"Fetch error: {e}"

    result = {
        "url": url,
        "expected": expected,
        "matched": ok,
        "at": now_iso(),
    }

    # Write live-check.json
    check_path = job_dir / "publish" / "live-check.json"
    check_path.parent.mkdir(parents=True, exist_ok=True)

    # Append to existing checks or create new
    existing_checks = []
    if check_path.exists():
        try:
            data = json.loads(check_path.read_text())
            existing_checks = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            pass
    existing_checks.append(result)
    check_path.write_text(json.dumps(existing_checks, ensure_ascii=False, indent=2) + "\n")

    # Update state
    state = load_state(job_dir)
    if ok:
        state["status"] = "verified"
        state["nextStep"] = ""
        state["blockedReason"] = ""
        state["lastDeliverable"] = "publish/live-check.json"
        if canonical_url:
            state.setdefault("publish", {})["canonicalUrl"] = canonical_url
        elif url:
            state.setdefault("publish", {})["canonicalUrl"] = url
        versions = state.setdefault("versions", [])
        versions.append({"note": f"Live URL 驗證通過: {url}", "at": now_iso()})
    else:
        state["status"] = "verification-failed"
        state["blockedReason"] = f"Expected '{expected}' not found at {url}"
        state["nextStep"] = "Check deploy status, retry verification"

    save_state(job_dir, state)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
