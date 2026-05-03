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

# 「不是 A 而是 B」的偽裝變體 — LLM 換皮繞過禁則最常見的形式
PSEUDO_BANNED_PATTERNS = [
    (r"真正的?[^，。\n]{0,15}是", "「真正的 X 是 Y」（不是…而是…的偽裝變體）"),
    (r"答案不在[^，。\n]{0,15}[，,]", "「答案不在 X，在 Y」變體"),
    (r"關鍵不在[^，。\n]{0,15}[，,]", "「關鍵不在 X，是 Y」變體"),
    (r"真正承重的是", "critic 審稿語滲透：「真正承重的是」"),
    (r"真正的關卡是", "critic 審稿語滲透：「真正的關卡是」"),
    (r"真正讓[^，。\n]{0,10}的是", "「真正讓 X 的是 Y」變體"),
    (r"真正壓垮", "「真正壓垮」變體"),
]

# critic / fact-check 的審稿語不該散落在 blog 正文
CRITIC_LEAK_PATTERNS = [
    (r"請當[^，。\n]*來讀", "critic 審稿語：『請當 X 來讀』"),
    (r"這條因果鏈缺", "critic 審稿語：『這條因果鏈缺』"),
    (r"方法論風險", "critic 審稿語：『方法論風險』"),
    (r"範疇滑移", "critic 審稿語：『範疇滑移』（出現在正文應寫進註腳或自然消化）"),
    (r"工作假設", "critic 審稿語：『工作假設』（同上）"),
    (r"待查核", "未消化的查核痕跡（散落正文）"),
    (r"代表性[調研]查樣本", "critic 審稿語：『代表性樣本』"),
    (r"缺\s*RCT\s*直接驗證", "critic 審稿語：『缺 RCT 直接驗證』"),
    (r"診斷層級錯位", "critic 審稿語：『診斷層級錯位』"),
]

EM_DASH_THRESHOLD = 3  # 全文 `——` 超過 3 次標 WARNING（LLM 高頻指紋）

# 正向掃描：mashbean lexicon 命中（不足 3 個 → WARNING，不 FAIL）
ACCENT_LEXICON = [
    "啊哈", "嘻嘻", "颯爽", "家己", "歹勢", "超級懶",
    "歪腦筋", "圖一樂", "大哉問", "龍蝦", "三壁",
    "貼心怪", "動動嘴巴", "跌跌撞撞", "多轉一個彎",
    "於是我", "沒想到", "我以為", "我想說",
    "純以誌之", "是以為記",
    "皮克敏", "達克效應", "精神時光屋", "整風",
    "（遠目", "XD", "（聽起來",
]
ACCENT_MIN_HITS = 3

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
    (r"mashbean,?\s*20\d{2}", "自我引用 placeholder"),
    (r"filecite", "filecite 殘留"),
    (r"【\d+†source】", "PDF source 殘留"),
]

REQUIRED_FRONTMATTER_FIELDS = ["title", "description"]
REQUIRED_FRONTMATTER_ALTERNATIVES = [("date", "pubDate")]


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


def check_footnote_format(text: str) -> list[dict]:
    """P3: Check that references use numbered list format for blog-pro CitationTooltip."""
    issues = []
    # Find the references section
    ref_match = re.search(r"^##\s*(參考資料|參考來源|引用資料|[Rr]eferences)\s*$", text, re.MULTILINE)
    if not ref_match:
        return issues  # No references section, skip check

    ref_section = text[ref_match.end():]

    # Check for bad formats: <sup>N</sup> at start of line in references
    bad_sup = re.finditer(r"^\s*<sup>\d+</sup>", ref_section, re.MULTILINE)
    for m in bad_sup:
        line_no = text[:ref_match.end() + m.start()].count("\n") + 1
        issues.append({
            "type": "Footnote 格式錯誤（應用編號列表）",
            "line": line_no,
            "match": m.group().strip()[:60],
        })

    # Check for [^N]: format in references
    bad_bracket = re.finditer(r"^\s*\[\^\d+\]:", ref_section, re.MULTILINE)
    for m in bad_bracket:
        line_no = text[:ref_match.end() + m.start()].count("\n") + 1
        issues.append({
            "type": "Footnote 格式錯誤（應用編號列表）",
            "line": line_no,
            "match": m.group().strip()[:60],
        })

    return issues


def count_em_dash(text: str) -> list[dict]:
    """全文 `——` 次數（LLM 高頻指紋）。超過 EM_DASH_THRESHOLD 標 WARNING。"""
    issues = []
    body = strip_frontmatter_and_refs(text)
    matches = list(re.finditer(r"——", body))
    if len(matches) > EM_DASH_THRESHOLD:
        issues.append({
            "type": f"`——` 過多（{len(matches)} 次，上限 {EM_DASH_THRESHOLD}）",
            "line": 0,
            "match": f"全文出現 {len(matches)} 次 ——，建議改寫為括號或逗號鋪陳",
        })
    return issues


def count_accent_hits(text: str) -> dict:
    """正向掃描：mashbean lexicon 命中數。"""
    body = strip_frontmatter_and_refs(text)
    hits = []
    for word in ACCENT_LEXICON:
        if word in body:
            hits.append(word)
    return {
        "count": len(hits),
        "hits": hits,
        "min_required": ACCENT_MIN_HITS,
        "below_min": len(hits) < ACCENT_MIN_HITS,
    }


def strip_frontmatter_and_refs(text: str) -> str:
    """移除 frontmatter 與 ## 參考資料 區段，只留正文。"""
    body = re.sub(r"^---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.DOTALL)
    ref_match = re.search(r"^##\s*(參考資料|參考來源|引用資料|[Rr]eferences)\s*$", body, re.MULTILINE)
    if ref_match:
        body = body[:ref_match.start()]
    return body


def run_checks(article_path: Path) -> dict:
    text = article_path.read_text()
    report = {
        "article": str(article_path.name),
        "passed": True,
        "frontmatter": {"ok": True, "issues": []},
        "style_violations": [],
        "pseudo_violations": [],
        "critic_leaks": [],
        "report_tone": [],
        "prompt_leaks": [],
        "self_citations": [],
        "colon_overuse": [],
        "em_dash_overuse": [],
        "accent": {"count": 0, "hits": [], "below_min": True},
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
        for alternatives in REQUIRED_FRONTMATTER_ALTERNATIVES:
            if not any(fm.get(field) for field in alternatives):
                report["frontmatter"]["ok"] = False
                report["frontmatter"]["issues"].append(
                    "Missing required field: " + " or ".join(alternatives)
                )

    # Body-only text for accent / em-dash / pseudo / critic checks
    body = strip_frontmatter_and_refs(text)

    # Style checks
    report["style_violations"] = check_patterns(text, BANNED_PATTERNS)
    report["pseudo_violations"] = check_patterns(body, PSEUDO_BANNED_PATTERNS)
    report["critic_leaks"] = check_patterns(body, CRITIC_LEAK_PATTERNS)
    report["report_tone"] = check_patterns(text, REPORT_TONE_PATTERNS)
    report["prompt_leaks"] = check_patterns(text, PROMPT_LEAK_PATTERNS)
    report["self_citations"] = check_patterns(text, SELF_CITATION_PATTERNS)
    report["colon_overuse"] = count_colons_in_body(text)
    report["em_dash_overuse"] = count_em_dash(text)
    report["accent"] = count_accent_hits(text)

    # P3: Footnote format check for blog-pro compatibility
    report["footnote_format"] = check_footnote_format(text)

    # Overall pass/fail — accent 命中不足與 em-dash 過多都是 WARNING（不 FAIL，但回報）
    has_issues = (
        not report["frontmatter"]["ok"]
        or report["style_violations"]
        or report["pseudo_violations"]
        or report["critic_leaks"]
        or report["prompt_leaks"]
        or report["self_citations"]
        or report["footnote_format"]
    )
    report["passed"] = not has_issues

    # Build summary
    counts = {
        "禁用句型": len(report["style_violations"]),
        "偽裝變體": len(report["pseudo_violations"]),
        "critic 審稿語洩漏": len(report["critic_leaks"]),
        "報告腔": len(report["report_tone"]),
        "Prompt 洩漏": len(report["prompt_leaks"]),
        "自引殘留": len(report["self_citations"]),
        "冒號過多": len(report["colon_overuse"]),
        "Frontmatter 問題": len(report["frontmatter"]["issues"]),
        "Footnote 格式": len(report["footnote_format"]),
    }
    parts = [f"{k}: {v}" for k, v in counts.items() if v > 0]
    warnings = []
    if report["em_dash_overuse"]:
        warnings.append(f"`——` 過多")
    if report["accent"]["below_min"]:
        warnings.append(f"accent 命中不足（{report['accent']['count']}/{ACCENT_MIN_HITS}）")
    if parts:
        report["summary"] = "FAIL — " + ", ".join(parts)
    elif warnings:
        report["summary"] = "PASS (with warnings) — " + ", ".join(warnings)
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
        ("偽裝變體（『真正的 X 是 Y』類）", "pseudo_violations"),
        ("critic 審稿語洩漏正文", "critic_leaks"),
        ("報告腔", "report_tone"),
        ("Prompt 洩漏", "prompt_leaks"),
        ("自引殘留", "self_citations"),
        ("冒號過多", "colon_overuse"),
        ("`——` 過多（WARNING）", "em_dash_overuse"),
        ("Footnote 格式", "footnote_format"),
    ]:
        items = report[key]
        if items:
            lines.append(f"## {section} ({len(items)})")
            for item in items:
                lines.append(f"- L{item['line']}: `{item['match']}`")
            lines.append("")

    accent = report.get("accent", {})
    if accent:
        marker = "⚠️ WARNING" if accent.get("below_min") else "✓ PASS"
        lines.append(f"## mashbean-accent 正向掃描 ({marker})")
        lines.append(f"- 命中: {accent['count']} / 建議至少 {accent['min_required']}")
        if accent.get("hits"):
            lines.append(f"- 命中詞: {', '.join(accent['hits'])}")
        if accent.get("below_min"):
            lines.append(f"- 建議：spawn accent-pass subagent 重新潤色")
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

    # Detect mashbean-accent opt-in from intake.yaml.
    #
    # Pipeline default (since 2026-05-03): no accent, ready-to-publish straight
    # after editorial-pass. mashbean-accent is opt-in only — set
    # `apply_mashbean_accent: true` in intake.yaml to enable it.
    #
    # Backwards-compat: `formal_academic: true` and `content_goal: academic_paper`
    # are still recognized as explicit no-accent signals (now redundant with
    # default behavior, but harmless).
    intake_path = job_dir / "intake.yaml"
    apply_accent = False
    if intake_path.exists():
        try:
            intake = yaml.safe_load(intake_path.read_text()) or {}
            apply_accent = bool(intake.get("apply_mashbean_accent")) or intake.get("content_goal") == "personal_blog"
        except Exception:
            pass

    # Auto-advance state if passed
    if auto_advance and report["passed"]:
        state = load_state(job_dir)
        if state["status"] in ("rewritten", "editorial-pass"):
            if apply_accent:
                # Opt-in: route through accent-pending for mashbean-accent pass
                state["status"] = "accent-pending"
                state["lastDeliverable"] = "verification/editorial-pass-report.md"
                state["nextStep"] = "spawn accent subagent → 套用 mashbean-accent skill → 覆寫 final/article-final.md → 推進到 ready-to-publish"
                save_state(job_dir, state)
                accent = report.get("accent", {})
                print(f"\n→ State advanced to accent-pending (apply_mashbean_accent=true)")
                print(f"  (accent 命中 {accent.get('count', 0)}/{ACCENT_MIN_HITS}{'，需 accent-pass 補強' if accent.get('below_min') else '，已達標但仍可潤色'})")
            else:
                # Default (academic / formal): skip accent entirely
                state["status"] = "ready-to-publish"
                state["lastDeliverable"] = "final/article-final.md (no-accent default)"
                state["nextStep"] = "frontmatter 確認 → commit → push → deploy → live URL 驗證"
                save_state(job_dir, state)
                print(f"\n→ State advanced to ready-to-publish (no-accent default; set apply_mashbean_accent: true to opt in)")
        elif state["status"] == "accent-pending":
            # Re-run after accent-pass: advance to ready-to-publish
            state["status"] = "ready-to-publish"
            state["lastDeliverable"] = "final/article-final.md (accent-pass complete)"
            state["nextStep"] = "frontmatter 確認 → commit → push → deploy → live URL 驗證"
            save_state(job_dir, state)
            print(f"\n→ State advanced to ready-to-publish (accent-pass complete)")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
