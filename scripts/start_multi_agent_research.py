#!/usr/bin/env python3
"""Scaffold multi-agent deep research for an article job.

This script does NOT spawn Claude Code subagents (only Claude Code itself can do
that). Instead it generates N sub-argument prompt template files that the main
agent can read, fill in domain specifics, and dispatch as parallel Agent tool
calls in a single message.

Usage:
    python3 scripts/start_multi_agent_research.py <job-id> [--n 5]

What it does:
    1. Reads jobs/<job-id>/intake.yaml
    2. Creates jobs/<job-id>/prompts/sub-args/ with N template files
    3. Creates raw/sub-args/ for sub-agent outputs
    4. Prints next-step instructions for the main agent

What the main agent does next:
    - Open each sub-arg template
    - Fill in domain-specific fields (主張、必收 A 級來源、反例、跨層級警示)
    - In a single message, fire N parallel Agent tool calls (run_in_background=true)
    - Wait for all N notifications
    - Hand-assemble raw/deep-research-output.md (do NOT use a subagent for this)
    - Run: python3 scripts/run_deep_research.py <job-id> integrate

See specs/multi-agent-deep-research.md for the full flow.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
import yaml

DEFAULT_N = 5

DEFAULT_REASONING_TYPES = ["D", "I", "A", "C", "Ab"]
DEFAULT_DOMAINS = [
    ("political-philosophy", "政治哲學", "D（演繹）", "規範性基礎"),
    ("cryptography", "密碼學工程", "I（歸納）", "工程可行性"),
    ("legal-precedent", "法律先例", "A（類比）", "制度模板"),
    ("causal-mechanism", "因果機制 / 實證案例", "C（因果）", "反向驗證"),
    ("boundary-conditions", "邊界條件", "Ab（溯因）", "自我批判"),
    ("comparative-cases", "跨案例比較", "I/C 混合", "經驗對照"),
]


SUB_ARG_TEMPLATE = """---
slug: sub-arg-{n}-{domain_slug}
job_id: {job_id}
status: template (待 main agent 填入領域特定內容)
domain: {domain_zh}
reasoning_type: {reasoning_type}
role: {role}
---

# Sub-Arg {n}：{domain_zh} — Research Pack Prompt Template

> **這是 main agent 用的 prompt 樣板**。main agent 必須填入下列 [TODO] 欄位，
> 然後把整段 prompt 透過 `Agent` tool 派出（`run_in_background=true`），
> 同 message 平行派 N 個 sub-arg agent。

---

# 你是博士論文研究代理 #{n}

你專責處理 Sub-Arg {n}：[TODO: 由 main agent 填入主張一句話]

## 背景

本研究包用於 article job `{job_id}`。完整脈絡見：

- `tools/research-publishing-pipeline/jobs/{job_id}/intake.yaml`（題目、核心問題、working_thesis）
- `tools/research-publishing-pipeline/jobs/{job_id}/notes/reasoning-chain-draft.md`（main agent 寫的推理鏈，含本 sub-arg 的位置與依賴）
- `tools/research-publishing-pipeline/specs/multi-agent-deep-research.md`（流程規範）

## 任務

對以下宣稱建立 ≥ 3000 中文字、≥ 30 來源（A 級 ≥ 10）的研究包：

> **Sub-Arg {n}**：[TODO: 由 main agent 填入主張完整論述]

這是博士論文章節的支撐研究，不是 blog。深度與引用嚴謹度是首要。

## 必須做到

### 1. 深度檢索（用 WebSearch + WebFetch）

[TODO: 由 main agent 列出領域對應的檢索路徑：
 - 例：政治哲學 → Google Scholar / SSRN / HeinOnline + 主要思想家全集
 - 例：密碼學 → IACR ePrint / W3C / IETF / ISO
 - 例：法律 → Westlaw / LexisNexis / 判例原文
 - 例：因果案例 → 學術 paper + 政府報告 + NGO 報告
 - 例：邊界條件 → 多領域實證 + 政策歷史]

### 2. 必收 A 級來源（要追到原文）

[TODO: 由 main agent 列出 5-10 條本領域最權威的必收引用，每條附 expected URL/DOI 與年份。例：
- Camenisch & Lysyanskaya (2001). EUROCRYPT.
- Pettit, P. (1997). Republicanism. Oxford UP.]

### 3. 多語言

[TODO: 領域對應，例：
- 政治哲學：英文 + 德文（Habermas）/ 法文（共和主義）
- 密碼學：英文為主
- 法律：判例原文 + ≥ 4 法域比較
- 中文：台灣憲政學界本土文獻]

### 4. 反例 / 反論

必須找出 ≥ 3 條能反駁主張的文獻。[TODO: 由 main agent 列出已知的反論方向]

### 5. 跨層級警示

如果主張涉及跨層級推論（個體 → 制度；政治哲學 → 工程；單一法域 → 跨法域），明確標示哪些跳躍可能失效。

### 6. 反事實

≥ 2 個 well-developed 反事實情境（含歷史對照優先）。

## 反陷阱檢查

- [ ] 不引用作者本人 mashbean
- [ ] 區分「相關性」與「因果性」；因果主張附反事實
- [ ] 區分「規範性主張」與「實證描述」
- [ ] 不憑空引用——每筆 cite 須有 URL/DOI 來源
- [ ] 不確定的標「待查核」或「[TODO-VERIFY]」
- [ ] 不只看西方案例（除非領域本就西方主導）

## 輸出格式

寫入：`tools/research-publishing-pipeline/jobs/{job_id}/raw/sub-args/sub-arg-{n}-{domain_slug}.md`

固定章節結構：

```markdown
# Sub-Arg {n}: [Title] — Research Pack

## 1. 主張重述與論證版本
   - 1.1 原始主張
   - 1.2 文獻檢索後的修正主張（建議採用）
   - 1.3 推理類型與強度評估

## 2. 文獻檢索路徑

## 3. 機制 / 案例 / 制度比較表（核心，依領域調整）

## 4. 核心引用清單（≥ 30，A 級 ≥ 10）
   ### A 級
   ### B 級
   ### C 級

## 5. 推理鏈與證據對照表

## 6. 跨層級警示

## 7. 反事實情境（≥ 2）

## 8. 待開發 / 訪談需求

## 9. 對其他 Sub-Arg 的銜接

## 附錄：反陷阱檢查表
```

## 工作配置

- 預估 30-60 分鐘
- 每筆核心 paper 都要追到 PDF / DOI / 判例原文
- 不只看英文（領域允許時）
- 完成後不要執行 pipeline 推進腳本，main agent 會處理整合

開始。
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scaffold multi-agent deep research prompt templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("job_id", help="Job ID (e.g. 2026-05-02-...)")
    parser.add_argument(
        "--n",
        type=int,
        default=DEFAULT_N,
        help=f"Number of sub-arg agents (default: {DEFAULT_N}). Min 4, max 6.",
    )
    parser.add_argument(
        "--domains",
        nargs="*",
        help=(
            "Override default domain slugs. Provide N space-separated slugs. "
            "If omitted, uses defaults: political-philosophy, cryptography, "
            "legal-precedent, causal-mechanism, boundary-conditions."
        ),
    )
    args = parser.parse_args()

    if not (4 <= args.n <= 6):
        sys.exit(f"Error: --n must be 4-6 (got {args.n})")

    repo_root = Path(__file__).parent.parent.resolve()
    job_dir = repo_root / "jobs" / args.job_id
    if not job_dir.exists():
        sys.exit(f"Error: job not found: {job_dir}")

    intake_path = job_dir / "intake.yaml"
    if not intake_path.exists():
        sys.exit(f"Error: intake.yaml not found in {job_dir}")

    intake = yaml.safe_load(intake_path.read_text()) or {}
    title = intake.get("title_hint", "(untitled)")
    # Pipeline default since 2026-05-03: no accent. apply_mashbean_accent is opt-in.
    apply_accent = bool(intake.get("apply_mashbean_accent")) or intake.get("content_goal") == "personal_blog"
    accent_mode = "opt-in (mashbean accent)" if apply_accent else "default (no accent)"

    # Build domains list
    if args.domains:
        if len(args.domains) != args.n:
            sys.exit(f"Error: --domains expects {args.n} slugs, got {len(args.domains)}")
        domains = [
            (slug, "[TODO]", "[TODO]", "[TODO]")
            for slug in args.domains
        ]
    else:
        domains = DEFAULT_DOMAINS[: args.n]

    # Create directories
    prompts_dir = job_dir / "prompts" / "sub-args"
    raw_dir = job_dir / "raw" / "sub-args"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Generate templates
    written: list[Path] = []
    for i, (slug, zh, rtype, role) in enumerate(domains, start=1):
        template = SUB_ARG_TEMPLATE.format(
            n=i,
            domain_slug=slug,
            job_id=args.job_id,
            domain_zh=zh,
            reasoning_type=rtype,
            role=role,
        )
        target = prompts_dir / f"sub-arg-{i}-{slug}.md"
        target.write_text(template)
        written.append(target)

    # Print next steps
    rel_prompts = prompts_dir.relative_to(repo_root)
    rel_raw = raw_dir.relative_to(repo_root)

    print(f"Scaffolded {args.n} sub-arg prompt templates for job: {args.job_id}")
    print(f"Title: {title}")
    print(f"Accent mode: {accent_mode}")
    print()
    print("Templates written to:")
    for p in written:
        print(f"  → {p.relative_to(repo_root)}")
    print()
    print(f"Sub-arg outputs will land in: {rel_raw}/")
    print()
    print("=" * 70)
    print("Next steps for the main agent:")
    print("=" * 70)
    print()
    print(f"1. Read each template in {rel_prompts}/ and fill in [TODO] fields:")
    print("   - 主張一句話 + 完整論述")
    print("   - 領域對應的檢索路徑")
    print("   - 必收 A 級來源 5-10 條")
    print("   - 已知反論方向")
    print("   - 多語言要求（依領域）")
    print()
    print("2. In a single message, dispatch N parallel Agent tool calls:")
    print()
    print("   for i in 1..N:")
    print("     Agent(")
    print(f'       description="Sub-Arg N: <領域>",')
    print('       subagent_type="general-purpose",')
    print('       model="opus",')
    print(f'       prompt=<filled template from {rel_prompts}/sub-arg-N-...md>,')
    print('       run_in_background=True,')
    print("     )")
    print()
    print(f"3. Wait for all {args.n} task notifications.")
    print()
    print("4. Main agent (NOT subagent) hand-assembles raw/deep-research-output.md")
    print("   using Bash to extract § 1 主張 + § 待開發 from each sub-arg, then Write.")
    print("   See specs/multi-agent-deep-research.md → Step 3.")
    print()
    print("5. (Optional) Cross-validation:")
    print(f"   python3 scripts/run_external_deep_research.py {args.job_id}")
    print()
    print("6. Push to pipeline:")
    print(f"   python3 scripts/run_deep_research.py {args.job_id} integrate")
    print()
    print("Full spec: specs/multi-agent-deep-research.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
