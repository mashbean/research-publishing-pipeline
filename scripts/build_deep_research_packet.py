#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: build_deep_research_packet.py <job-dir>", file=sys.stderr)
        return 1

    job_dir = Path(sys.argv[1]).resolve()
    intake = job_dir / "intake.yaml"
    packet = job_dir / "deep-research-packet.yaml"

    if not intake.exists():
        print(f"missing intake: {intake}", file=sys.stderr)
        return 1
    if packet.exists():
        print(packet)
        return 0

    template = (ROOT / "templates" / "deep-research-packet.yaml").read_text()
    packet.write_text(template)
    print(packet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
