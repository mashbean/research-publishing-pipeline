#!/usr/bin/env python3
"""Automated editorial pass: check style violations, frontmatter, prompt leaks."""
from __future__ import annotations

import re
import sys
import yaml
from pathlib import Path

from lib import resolve_job_dir, load_state, save_state, now_iso


# --- Style rules from style-policy-zh.md ---

BANNED_PATTERNS = [
    (r"不是[^，。\n]{0,20}，\s*而是", "「不是……而是……」句型"),
    (r"不只[^，。\n]{0,20}，\s*而是", "「不只……而是……」句型"),
    (r"不是\s*A[^，。\n]{0,10}，\s*而是\s*B", "「不是A而是B」句型"),
    (r"不[^，。\n]{0,15}，\s*而[^，。\n]{0,15}", "「不……而……」句型"),
]

REPORT_TONE_PATTERNS = [
    (r"本文將", "報告腔：「本文將」"),
    (r"本文依據", "報告腔：「本文依據」"),
    (r"研究目的在於", "報告腔：「研究目的在於」"),
    (r"本研究", "報告腔：「本研究」"),
    (r"綜上所述", "報告腔：「綜上所述」"),
]

PROMPT_LEAK_PATTERNS = [
    (r"我要維持的語氣", "Prompt 洩漏"),
    (r"這裡需要更正式", "Prompt 洩漏"),
    (r"請根據以下", "Prompt 洩漏"),
    (r"你的任務是", "Prompt 洩漏"),
    (r"我需要你", "Prompt 洩漏"),
]

SELF_CITATION_PATTERNS = [
    # TODO: Add your own name pattern, e.g.:
    # (r"yourname,?\s*20\d{2}", "自我引用 placeholder"),
    (r"filecite", "filecite 殘留"),
    (r"【\d+†source】", "PDF source 殘留"),
]

REQUIRED_FRONTMATTER_FIELDS = ["title", "date", "description"]


def find_article(job_dir: Path) -> Path | None:
    """Find the most recent final article."""
    final_dir = job_dir / "final"
    if not final_dir.exists():
        return None
    candidates = sorted(final_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def extract_frontmatter(text: str) -> dict | None:
    """Extract YAML frontmatter from markdown."""
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1))
    except Exception:
        return None


def check_patterns(text: str, patterns: list[tuple[str, str]]) -> list[dict]:
    issues = []
    for pattern, label in patterns:
        for m in re.finditer(pattern, text):
            line_no = text[:m.start()].count("\n") + 1
            issues.append({
                "type": label,
                "line": line_no,
                "match": m.group()[:60],
            })
    return issues


def count_colons_in_body(text: str) -> list[dict]:
    """Check colon overuse in body text (not in frontmatter, headers, code blocks)."""
    issues = []
    in_frontmatter = False
    in_code = False
    for i, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_frontmatter or in_code:
            continue
        if stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("-"):
            continue
        # Body text with colon that isn't a URL
        colon_count = len(re.findall(r"(?<!http)(?<!https)：", stripped))
        if colon_count >= 2:
            issues.append({
                "type": "正文冒號過多",
                "line": i,
                "match": stripped[:60],
            })
    return issues


def run_checks(article_path: Path) -> dict:
    text = article_path.read_text()
    report = {
        "article": str(article_path.name),
        "passed": True,
        "frontmatter": {"ok": True, "issues": []},
        "style_violations": [],
        "report_tone": [],
        "prompt_leaks": [],
        "self_citations": [],
        "colon_overuse": [],
        "summary": "",
    }

    # Frontmatter check
    fm = extract_frontmatter(text)
    if fm is None:
        report["frontmatter"]["ok"] = False
        report["frontmatter"]["issues"].append("Missing or invalid YAML frontmatter")
    else:
        for field in REQUIRED_FRONTMATTER_FIELDS:
            if not fm.get(field):
                report["frontmatter"]["ok"] = False
                report["frontmatter"]["issues"].append(f"Missing required field: {field}")

    # Style checks
    report["style_violations"] = check_patterns(text, BANNED_PATTERNS)
    report["report_tone"] = check_patterns(text, REPORT_TONE_PATTERNS)
    report["prompt_leaks"] = check_patterns(text, PROMPT_LEAK_PATTERNS)
    report["self_citations"] = check_patterns(text, SELF_CITATION_PATTERNS)
    report["colon_overuse"] = count_colons_in_body(text)

    # Overall pass/fail
    has_issues = (
        not report["frontmatter"]["ok"]
        or report["style_violations"]
        or report["prompt_leaks"]
        or report["self_citations"]
    )
    report["passed"] = not has_issues

    # Build summary
    counts = {
        "禁用句型": len(report["style_violations"]),
        "報告腔": len(report["report_tone"]),
        "Prompt 洩漏": len(report["prompt_leaks"]),
        "自引殘留": len(report["self_citations"]),
        "冒號過多": len(report["colon_overuse"]),
        "Frontmatter 問題": len(report["frontmatter"]["issues"]),
    }
    parts = [f"{k}: {v}" for k, v in counts.items() if v > 0]
    if parts:
        report["summary"] = "FAIL — " + ", ".join(parts)
    else:
        report["summary"] = "PASS — 所有檢查通過"

    return report


def format_report(report: dict) -> str:
    lines = [
        f"# Editorial Pass Report",
        f"",
        f"Article: `{report['article']}`",
        f"Result: **{report['summary']}**",
        f"",
    ]

    if report["frontmatter"]["issues"]:
        lines.append("## Frontmatter Issues")
        for issue in report["frontmatter"]["issues"]:
            lines.append(f"- {issue}")
        lines.append("")

    for section, key in [
        ("禁用句型", "style_violations"),
        ("報告腔", "report_tone"),
        ("Prompt 洩漏", "prompt_leaks"),
        ("自引殘留", "self_citations"),
        ("冒號過多", "colon_overuse"),
    ]:
        items = report[key]
        if items:
            lines.append(f"## {section} ({len(items)})")
            for item in items:
                lines.append(f"- L{item['line']}: `{item['match']}`")
            lines.append("")

    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_editorial_pass.py <job-id-or-path> [--auto-advance]", file=sys.stderr)
        return 1

    auto_advance = "--auto-advance" in sys.argv

    try:
        job_dir = resolve_job_dir(sys.argv[1])
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    article = find_article(job_dir)
    if not article:
        print("No article found in final/ directory", file=sys.stderr)
        return 1

    report = run_checks(article)
    report_text = format_report(report)

    # Write report
    report_path = job_dir / "verification" / "editorial-pass-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text)
    print(report_text)

    # Auto-advance state if passed
    if auto_advance and report["passed"]:
        state = load_state(job_dir)
        if state["status"] in ("rewritten", "editorial-pass"):
            state["status"] = "ready-to-publish"
            state["lastDeliverable"] = "verification/editorial-pass-report.md"
            state["nextStep"] = "frontmatter 確認 → commit → push → deploy → live URL 驗證"
            save_state(job_dir, state)
            print(f"\n→ State advanced to ready-to-publish")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
