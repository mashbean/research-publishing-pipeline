#!/usr/bin/env python3
"""
Generate a Deep Research prompt from intake + packet, and provide
integration tooling to merge Deep Research results back into the job.

Usage:
  # Step 1: Generate the prompt for Deep Research
  run_deep_research.py <job> generate-prompt

  # Step 2: After Deep Research returns, save raw output
  run_deep_research.py <job> save-raw <raw-output-file>

  # Step 3: Parse and distribute results into job structure
  run_deep_research.py <job> integrate
"""
from __future__ import annotations

import re
import sys
import yaml
from pathlib import Path

from lib import resolve_job_dir, load_state, save_state, now_iso, ROOT


# ─── Structured output section mappings ─────────────────────────────

SECTION_FILE_MAP = {
    "research_summary":  "notes/research-summary.md",
    "reasoning_chain":   "notes/reasoning-chain.md",
    "evidence_map":      "verification/evidence-map.md",
    "source_registry":   "notes/source-registry.md",
    "case_comparison":   "notes/case-comparison.md",
    "high_risk_claims":  "verification/high-risk-claims.md",
    "open_questions":    "notes/open-questions.md",
    "rewrite_warnings":  "notes/rewrite-warnings.md",
    # Legacy names (fuzzy match fallback)
    "source_notes":      "notes/source-notes.md",
    "suggested_structure": "notes/suggested-structure.md",
}

# Quality gates: sections that must exist for auto-advance
REQUIRED_SECTIONS = {"evidence_map"}
RECOMMENDED_SECTIONS = {"reasoning_chain", "case_comparison", "source_registry"}


# ─── Output format specification (appended to every prompt) ─────────

OUTPUT_FORMAT_SPEC = """
## 輸出格式要求

請使用以下結構輸出。每個章節用 `<!-- SECTION: name -->` 標記開頭。
這些標記讓下游工具可以自動拆分你的研究成果。

必要章節（按順序）：

<!-- SECTION: research_summary -->
# 研究摘要
[2-3 段概述]

<!-- SECTION: reasoning_chain -->
# 推理鏈

## 核心問題
[一句話]

## 推理路徑

### Sub-Arg 1: [名稱]
- **主張**: ...
- **推理類型**: D(演繹) / I(歸納) / A(類比) / Ab(溯因) / C(因果)
- **支撐證據**:
  1. [A/B/C 級] 來源 → 關鍵發現
- **推理強度**: 強/中/弱
- **反例/限制**: ...

### Sub-Arg N: ...

## 合成結論
- **結論**: ...
- **推理路徑**: Sub-Arg 1 (I) + Sub-Arg 2 (C) → Synthesis
- **已知盲點**: ...

<!-- SECTION: evidence_map -->
# 證據對照表

| # | 主張 | 來源 | 來源等級 | 信心度 | 查閱日期 | 備註 |
|---|------|------|---------|--------|---------|------|

<!-- SECTION: source_registry -->
# 來源清冊

## 學術文獻
- Author (Year). *Title*. Publisher. DOI/URL

## 官方文件
- Org. "Title." URL (查閱日期)

## 案例與報導
- Source. "Title." URL (查閱日期)

<!-- SECTION: case_comparison -->
# 案例正反對照

| 類別 | 成功案例 | 失敗案例 | 對照意義 |
|------|---------|---------|---------|

每個案例附結構化資料（名稱、類型、成立年、狀態、法律結構、收入模式、年收入、使用者規模、治理模式、關鍵風險）。

<!-- SECTION: high_risk_claims -->
# 高風險主張

| # | 主張 | 風險類型 | 說明 | 建議處理 |
|---|------|---------|------|---------|

風險類型：因果混淆 / 倖存者偏差 / 範疇滑移 / 數據過時 / 來源不足

<!-- SECTION: open_questions -->
# 未解問題
- [ ] ...

<!-- SECTION: rewrite_warnings -->
# 改寫注意事項
- ...
""".strip()


def generate_prompt(job_dir: Path) -> int:
    """Generate a complete Deep Research prompt from intake + packet."""
    intake_path = job_dir / "intake.yaml"
    packet_path = job_dir / "deep-research-packet.yaml"

    if not intake_path.exists():
        print(f"Missing intake.yaml in {job_dir}", file=sys.stderr)
        return 1

    intake = yaml.safe_load(intake_path.read_text())
    packet = yaml.safe_load(packet_path.read_text()) if packet_path.exists() else {}

    # Load the brief template
    brief_template = (ROOT / "prompts" / "deep-research-brief.md").read_text()

    # Build the full prompt
    sections = [brief_template, "", "---", "", "# 研究包參數", ""]

    # Core fields
    sections.append(f"## 主題\n{intake.get('title_hint', packet.get('topic', ''))}")
    sections.append(f"\n## 核心問題")
    for q in _as_list(intake.get("core_question", packet.get("core_question", []))):
        sections.append(f"- {q}")

    sections.append(f"\n## Working Thesis\n{intake.get('working_thesis', packet.get('working_thesis', ''))}")
    sections.append(f"\n## 目標讀者\n{intake.get('audience', packet.get('target_audience', ''))}")

    # Seed draft
    seed = packet.get("seed_draft", "").strip()
    if seed:
        sections.append(f"\n## Seed Draft\n```\n{seed}\n```")

    # Candidate sources
    sources = packet.get("candidate_sources", [])
    if sources and sources != [{"title": "", "url": "", "reason": ""}]:
        sections.append("\n## 候選來源")
        for s in sources:
            if isinstance(s, dict) and s.get("title"):
                sections.append(f"- **{s['title']}** — {s.get('url', '')} ({s.get('reason', '')})")

    # Must-use / must-not-use
    must_use = packet.get("must_use_sources", [])
    if must_use and must_use != [""]:
        sections.append("\n## 必須使用的來源")
        for s in must_use:
            sections.append(f"- {s}")

    must_not = packet.get("must_not_use_sources", [])
    if must_not:
        sections.append("\n## 禁止使用的來源")
        for s in must_not:
            sections.append(f"- {s}")

    # Claims to verify
    claims = packet.get("claims_to_verify", [])
    if claims and claims != [""]:
        sections.append("\n## 需要驗證的主張")
        for c in claims:
            sections.append(f"- {c}")

    # Open questions
    oq = intake.get("open_questions", packet.get("open_questions", []))
    if oq and oq != [""]:
        sections.append("\n## 待解問題")
        for q in _as_list(oq):
            sections.append(f"- {q}")

    # Source collection requirements
    sections.append("\n## 來源蒐集要求")
    sections.append("- 每個論點的成功案例必須配對至少一個失敗案例（避免倖存者偏差）")
    sections.append("- 來源必須涵蓋四象限：學術理論（正/反）× 真實案例（成功/失敗）")
    sections.append("- 核心主張必須有 A 級來源（學術論文、官方文件、審計報告）")
    sections.append("- 每個案例提供結構化資料（法律結構、收入模式、年收入、使用者規模、治理模式）")
    sections.append("- 所有數字標明年份和來源，貨幣標明幣別")

    # Constraints
    sections.append("\n## 寫作限制")
    for c in packet.get("style_constraints", []):
        sections.append(f"- {c}")
    for c in intake.get("must_avoid", []):
        sections.append(f"- 禁止：{c}")
    for c in intake.get("must_do", []):
        sections.append(f"- 必須：{c}")

    sections.append("\n## 引用規範")
    for c in packet.get("citation_constraints", []):
        sections.append(f"- {c}")

    # Reasoning requirements
    sections.append("\n## 推理要求")
    sections.append("- 每個子論點標明推理類型：D(演繹) / I(歸納) / A(類比) / Ab(溯因) / C(因果)")
    sections.append("- 因果主張必須區分「觀察到的相關性」和「驗證的因果關係」")
    sections.append("- 每個因果主張必須附帶至少一個反事實問題")
    sections.append("- 最終合成結論標明強度（強/中/弱）和已知盲點")

    # Append structured output format
    sections.append(f"\n{OUTPUT_FORMAT_SPEC}")

    prompt_text = "\n".join(sections)

    # Write to job prompts dir
    prompt_dir = job_dir / "prompts"
    prompt_dir.mkdir(exist_ok=True)
    prompt_path = prompt_dir / "deep-research-prompt.md"
    prompt_path.write_text(prompt_text)

    # Update state
    state = load_state(job_dir)
    if state["status"] == "scoped":
        state["status"] = "researching"
        state["nextStep"] = "等待 Deep Research 結果"
        state["lastDeliverable"] = "prompts/deep-research-prompt.md"
        save_state(job_dir, state)

    print(f"Prompt written to: {prompt_path}")
    print(f"Characters: {len(prompt_text)}")
    return 0


def save_raw(job_dir: Path, raw_file: str) -> int:
    """Save raw Deep Research output to the job."""
    src = Path(raw_file).resolve()
    if not src.exists():
        print(f"File not found: {src}", file=sys.stderr)
        return 1

    raw_dir = job_dir / "raw"
    raw_dir.mkdir(exist_ok=True)
    dest = raw_dir / "deep-research-output.md"
    dest.write_text(src.read_text())

    print(f"Saved to: {dest}")
    return 0


def integrate(job_dir: Path) -> int:
    """Parse raw Deep Research output and distribute into job structure."""
    raw_path = job_dir / "raw" / "deep-research-output.md"
    if not raw_path.exists():
        print(f"No raw output found at {raw_path}", file=sys.stderr)
        print("Run 'save-raw' first, or place output at raw/deep-research-output.md", file=sys.stderr)
        return 1

    raw = raw_path.read_text()
    written = []

    # ── Strategy 1: Parse structured <!-- SECTION: name --> markers ──
    structured_sections = _parse_structured_sections(raw)
    if structured_sections:
        print(f"Found {len(structured_sections)} structured sections")
        for name, content in structured_sections.items():
            target_rel = SECTION_FILE_MAP.get(name)
            if target_rel and content.strip():
                target = job_dir / target_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content.strip() + "\n")
                written.append(target_rel)
                print(f"  → {target_rel} ({len(content)} chars)")

    # ── Strategy 2: Fallback to fuzzy header matching ──
    if not written:
        print("No structured markers found, trying fuzzy header matching...")
        header_sections = _split_sections(raw)
        fuzzy_mappings = {
            "verification/evidence-map.md": ["evidence.map", "evidence map", "證據對照"],
            "notes/source-notes.md": ["source.notes", "source notes", "來源筆記", "來源清冊"],
            "verification/high-risk-claims.md": ["high.risk", "high risk", "高風險"],
            "notes/research-summary.md": ["research.summary", "research summary", "研究摘要"],
            "notes/reasoning-chain.md": ["reasoning", "推理鏈", "推理路徑"],
            "notes/case-comparison.md": ["case.comparison", "案例", "正反對照"],
            "notes/suggested-structure.md": ["suggested.structure", "structure", "建議結構"],
        }
        for target_rel, patterns in fuzzy_mappings.items():
            content = _find_section(header_sections, patterns)
            if content:
                target = job_dir / target_rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content.strip() + "\n")
                written.append(target_rel)

    # ── Strategy 3: Last resort — whole file as research draft ──
    if not written:
        draft = job_dir / "drafts" / "research-draft.md"
        draft.parent.mkdir(parents=True, exist_ok=True)
        draft.write_text(raw)
        written.append("drafts/research-draft.md")
        print("No sections matched — saved entire output as research draft")

    # ── Quality gates ──
    missing_required = []
    missing_recommended = []
    for section in REQUIRED_SECTIONS:
        target_rel = SECTION_FILE_MAP.get(section, "")
        if target_rel and not (job_dir / target_rel).exists():
            missing_required.append(section)
    for section in RECOMMENDED_SECTIONS:
        target_rel = SECTION_FILE_MAP.get(section, "")
        if target_rel and not (job_dir / target_rel).exists():
            missing_recommended.append(section)

    # ── Update state ──
    state = load_state(job_dir)
    if state["status"] == "researching":
        if missing_required:
            state["status"] = "needs-decision"
            state["blockedReason"] = f"Missing required sections: {', '.join(missing_required)}"
            state["nextStep"] = "Re-run Deep Research or manually create missing sections"
        elif (job_dir / "verification" / "evidence-map.md").exists():
            state["status"] = "evidence-mapped"
            state["nextStep"] = "build reasoning chain → write research draft"
        else:
            state["status"] = "drafted"
            state["nextStep"] = "fact-check research draft"

        state["lastDeliverable"] = written[-1]
        versions = state.setdefault("versions", [])
        versions.append({"note": "Deep Research 結果整合完成", "at": now_iso()})
        save_state(job_dir, state)

    # ── Report ──
    print(f"\nIntegrated {len(written)} files:")
    for w in written:
        print(f"  ✓ {w}")
    if missing_recommended:
        print(f"\nRecommended but missing:")
        for m in missing_recommended:
            print(f"  △ {m}")
    if missing_required:
        print(f"\nRequired but missing (status → needs-decision):")
        for m in missing_required:
            print(f"  ✗ {m}")

    return 0


# ─── Parsing helpers ─────────────────────────────────────────────────

def _parse_structured_sections(text: str) -> dict[str, str]:
    """Parse <!-- SECTION: name --> markers."""
    pattern = r'<!--\s*SECTION:\s*(\w+)\s*-->'
    parts = re.split(pattern, text)
    sections = {}
    # parts alternates: [preamble, name1, content1, name2, content2, ...]
    i = 1
    while i < len(parts) - 1:
        name = parts[i].strip()
        content = parts[i + 1].strip()
        if name and content:
            sections[name] = content
        i += 2
    return sections


def _split_sections(text: str) -> list[tuple[str, str]]:
    """Split markdown into (header, content) pairs by headers."""
    parts = re.split(r"^(#{1,3}\s+.+)$", text, flags=re.MULTILINE)
    sections = []
    current_header = ""
    for part in parts:
        if re.match(r"^#{1,3}\s+", part):
            current_header = part.strip().lstrip("#").strip().lower()
        else:
            if current_header:
                sections.append((current_header, part.strip()))
    return sections


def _find_section(sections: list[tuple[str, str]], patterns: list[str]) -> str | None:
    """Find a section whose header matches any of the patterns."""
    for header, content in sections:
        for p in patterns:
            if p.lower() in header.lower():
                return content
    return None


def _as_list(v) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        return [v]
    return []


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: run_deep_research.py <job> <generate-prompt|save-raw|integrate> [args...]", file=sys.stderr)
        return 1

    job_id = sys.argv[1]
    action = sys.argv[2]

    try:
        job_dir = resolve_job_dir(job_id)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        return 1

    if action == "generate-prompt":
        return generate_prompt(job_dir)
    elif action == "save-raw":
        if len(sys.argv) < 4:
            print("usage: run_deep_research.py <job> save-raw <file>", file=sys.stderr)
            return 1
        return save_raw(job_dir, sys.argv[3])
    elif action == "integrate":
        return integrate(job_dir)
    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
