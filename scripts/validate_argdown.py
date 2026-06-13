#!/usr/bin/env python3
"""Validate an Argdown export with the Argdown CLI."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from lib import resolve_job_dir


def find_argdown() -> Path | None:
    env_bin = os.environ.get("ARGDOWN_BIN")
    if env_bin and Path(env_bin).exists():
        return Path(env_bin)

    found = shutil.which("argdown")
    if found:
        return Path(found)

    candidates = [
        Path.home() / ".local" / "bin" / "argdown",
        Path.home() / ".local" / "share" / "codex-tools" / "argdown-cli" / "node_modules" / ".bin" / "argdown",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def resolve_input(args: argparse.Namespace) -> Path:
    if args.input:
        return Path(args.input).expanduser().resolve()
    if not args.job:
        raise ValueError("Either <job-id-or-path> or --input is required.")
    job_dir = resolve_job_dir(args.job)
    return job_dir / "final" / "argument.argdown"


def run_argdown(argdown_bin: Path, input_path: Path, export: str) -> subprocess.CompletedProcess:
    out_dir = Path(tempfile.mkdtemp(prefix=f"argdown-{export}."))
    env = os.environ.copy()
    local_bin = str(Path.home() / ".local" / "bin")
    env["PATH"] = f"{local_bin}:{env.get('PATH', '')}"
    return subprocess.run(
        [str(argdown_bin), export, str(input_path), str(out_dir), "--throwExceptions"],
        capture_output=True,
        text=True,
        env=env,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", nargs="?", help="Job id or job directory. Defaults to final/argument.argdown.")
    parser.add_argument("--input", help="Explicit .argdown input path.")
    parser.add_argument(
        "--export",
        choices=["json", "html", "map"],
        action="append",
        default=[],
        help="Argdown export command to validate. Defaults to json.",
    )
    args = parser.parse_args()

    try:
        input_path = resolve_input(args)
    except Exception as exc:
        print(f"validate_argdown.py: {exc}", file=sys.stderr)
        return 1

    if not input_path.exists():
        print(f"validate_argdown.py: Argdown file not found: {input_path}", file=sys.stderr)
        return 1

    argdown_bin = find_argdown()
    if not argdown_bin:
        print(
            "validate_argdown.py: Argdown CLI not found. Install it or set ARGDOWN_BIN.",
            file=sys.stderr,
        )
        return 1

    exports = args.export or ["json"]
    for export in exports:
        result = run_argdown(argdown_bin, input_path, export)
        if result.returncode != 0:
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            return result.returncode
        print(result.stdout, end="")

    print(f"Argdown validated: {input_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
