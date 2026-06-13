# research-publishing-pipeline

研究文章自動生產線 v2。

目標是把題目、線索、Deep Research 協作、查核、重寫、發稿與線上驗證，收斂成一條可重複執行的工作流，讓豆泥未來提供問題與資料後，可以半自動到自動地產出研究型 blog 文章。

## 核心原則

1. writing pipeline 與 repo pipeline 分離
2. 先有 evidence map，再有 publish draft
3. Deep Research 不從空白開始，要吃 packet（自動產生）
4. citation sanitation 必須獨立成一步
5. push 不算完成，live URL 驗證才算完成
6. stalled 不能只回報，必須自動升級或自動續推
7. 研究 job 一旦啟動，就自動進入 10 分鐘 active reminder 模式，直到結案為止
8. 每個狀態轉換都自動回寫 state.json

## Quick Start

```bash
# 1. 建立新文章 job（一個指令搞定）
python3 scripts/start_article_job.py my-article \
  --title "文章標題" \
  --audience "目標讀者" \
  --core-question "核心問題" \
  --thesis "working thesis" \
  --publish-repo external/blog

# 2. 查看狀態
python3 scripts/run_pipeline.py my-article status

# 3. 自動跑到需要人工介入為止
python3 scripts/run_pipeline.py my-article auto
```

## 目錄結構

- `specs/workflow.md`：整體工作流與狀態機
- `specs/citation-policy.md`：引用與自引清理規則
- `specs/style-policy-zh.md`：中文寫作與禁則
- `specs/publish-policy.md`：發稿、deploy、live verify 規則
- `specs/automation-contract.md`：job 啟動、續推、結案如何接到 10 分鐘強制提醒模式
- `templates/intake.yaml`：文章 intake 模板
- `templates/deep-research-packet.yaml`：Deep Research 標準輸入包
- `templates/fact-check-report.md`：查核報告模板
- `templates/publish-checklist.md`：發稿前後檢查表
- `templates/pro-article-final-pass-checklist.md`：pro 站 AI 文章最後一輪檢查表
- `templates/state.json`：文章 job 狀態檔模板
- `scripts/start_article_job.py`：單指令建立 job、生成 packet、切 active reminder 的啟動入口
- `specs/other-computer-agent-quickstart.md`：另一台電腦上的 agent 啟動研究 quickstart
- `references/case-study-2026-03-28-2026-03-29.md`：本次兩篇文章的案例整理
- `jobs/_example/`：單篇文章的資料夾結構範例
- `prompts/`：各 subagent 的 prompt 檔（agent-writer.md、agent-critic.md、agent-editor.md 等）
- `CLAUDE.md`：Claude Code 操作指南（主 agent 的 pipeline 步驟）
