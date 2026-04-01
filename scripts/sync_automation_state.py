#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTOMATION_STATE = Path.home() / '.openclaw' / 'workspace' / 'memory' / 'automation-state.json'
TZ = timezone(timedelta(hours=8))


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec='seconds')


def load_state() -> dict:
    if AUTOMATION_STATE.exists():
        return json.loads(AUTOMATION_STATE.read_text())
    return {}


def save_state(state: dict) -> None:
    AUTOMATION_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')


def start(job_id: str, task_note: str, next_deliverable: str) -> int:
    ts = now_iso()
    state = load_state()
    state.update({
        'activeWork': True,
        'mode': 'active',
        'taskTitle': job_id,
        'taskNote': task_note,
        'nextDeliverable': next_deliverable,
        'blockedReason': '',
        'lastDeliverable': f'Started article job {job_id}.',
        'lastDeliverableAt': ts,
        'lastMeaningfulProgressAt': ts,
        'stallMinutes': 0,
        'lastUpdated': ts,
    })
    save_state(state)
    print(AUTOMATION_STATE)
    return 0


def end(summary: str) -> int:
    ts = now_iso()
    state = load_state()
    state.update({
        'activeWork': False,
        'mode': 'idle',
        'taskTitle': '',
        'taskNote': '',
        'nextDeliverable': '',
        'blockedReason': '',
        'lastDeliverable': summary,
        'lastDeliverableAt': ts,
        'lastMeaningfulProgressAt': ts,
        'stallMinutes': 0,
        'lastUpdated': ts,
    })
    save_state(state)
    print(AUTOMATION_STATE)
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        print('usage: sync_automation_state.py start <job-id> <task-note> <next-deliverable> | end <summary>', file=sys.stderr)
        return 1
    action = sys.argv[1]
    if action == 'start':
        if len(sys.argv) != 5:
            return 1
        return start(sys.argv[2], sys.argv[3], sys.argv[4])
    if action == 'end':
        if len(sys.argv) != 3:
            return 1
        return end(sys.argv[2])
    print(f'unknown action: {action}', file=sys.stderr)
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
