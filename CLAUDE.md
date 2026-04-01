# Research Publishing Pipeline — Claude Code 操作指南

本目錄是研究文章自動生產線。當使用者要求寫文章、做研究、發稿時，請依照此指南操作。

## 啟動條件

當使用者說以下任何一種話時，啟動 pipeline：
- 「寫一篇文章」「幫我寫 blog」
- 「研究 X 主題」
- 「啟動 article job」
- 提供了題目 + 來源 + 核心問題

## Pipeline 操作流程

### Step 0: 建立 Job

```bash
python3 scripts/start_article_job.py <job-id> \
  --title "..." --audience "..." --core-question "..." --thesis "..."
```

### Step 1: 自動推進到 Deep Research

```bash
python3 scripts/run_pipeline.py <job-id> auto
```

Pipeline 會自動：intake → scoped → researching，然後停下等 Deep Research。

### Step 2: Research（用 subagent）

啟動 research subagent：

```
Agent(
  description="Research for article <job-id>",
  subagent_type="general-purpose",
  prompt="你是研究代理。讀取 <job-dir>/prompts/agent-research.md 的完整指令，\n然後讀取 <job-dir>/intake.yaml 和 <job-dir>/deep-research-packet.yaml，\n執行研究任務並將結果寫入 <job-dir>/verification/ 和 <job-dir>/notes/。\n完成後執行：python3 scripts/run_deep_research.py <job-id> integrate"
)
```

或者，如果使用者已經從 ChatGPT/Claude Deep Research 拿到結果：
```bash
python3 scripts/run_deep_research.py <job-id> save-raw <file>
python3 scripts/run_deep_research.py <job-id> integrate
```

### Step 3: Writer（用 subagent）

啟動 writer subagent 寫研究草稿：

```
Agent(
  description="Write research draft for <job-id>",
  subagent_type="general-purpose",
  prompt="你是寫作代理。讀取 <job-dir>/prompts/agent-writer.md 的完整指令，\n然後讀取 <job-dir> 中的 intake.yaml、evidence-map.md、source-notes.md，\n產出 drafts/research-draft.md。語言：繁體中文。"
)
```

完成後推進狀態：
```bash
python3 scripts/update_job_state.py <job-id> --status drafted --last-deliverable drafts/research-draft.md
```

### Step 4: Critic（用 subagent）

```
Agent(
  description="Fact-check draft for <job-id>",
  subagent_type="general-purpose",
  prompt="你是查核代理。讀取 <job-dir>/prompts/agent-critic.md 的完整指令，\n然後讀取 <job-dir> 中的 drafts/research-draft.md 和 verification/evidence-map.md，\n產出 verification/fact-check-report.md。"
)
```

根據 critic 的 Decision：
- 「可進入 blog rewrite」→ `update_job_state.py --status fact-checking`
- 「需要補研究」→ 回到 Step 2

### Step 5: Writer rewrite（用 subagent）

```
Agent(
  description="Blog rewrite for <job-id>",
  subagent_type="general-purpose",
  prompt="你是寫作代理（改寫模式）。讀取 <job-dir>/prompts/agent-writer.md，\n讀取 research-draft.md 和 fact-check-report.md，\n產出 drafts/blog-rewrite.md。重點：轉成 blog 文體，套用所有禁則。"
)
```

```bash
python3 scripts/update_job_state.py <job-id> --status rewritten --last-deliverable drafts/blog-rewrite.md
```

### Step 6: Editor（用 subagent）

```
Agent(
  description="Editorial pass for <job-id>",
  subagent_type="general-purpose",
  prompt="你是編輯代理。讀取 <job-dir>/prompts/agent-editor.md 的完整指令，\n讀取 blog-rewrite.md，執行結構審查、禁則巡檢、語氣校準，\n產出 final/article-final.md。完成後執行：\npython3 scripts/run_editorial_pass.py <job-dir> --auto-advance"
)
```

### Step 7: Publish + Verify

```bash
python3 scripts/run_pipeline.py <job-id> publish
python3 scripts/run_pipeline.py <job-id> verify
python3 scripts/sync_automation_state.py end "Published: <title>"
```

## 狀態檢查

隨時可以查看 job 狀態：
```bash
python3 scripts/run_pipeline.py <job-id> status
```

## Subagent 使用原則

1. **research / writer / critic / editor 用 subagent**：這些任務吃大量 context，用 subagent 保護主對話
2. **狀態管理留在 main agent**：`update_job_state.py` 和 `run_pipeline.py` 由主對話執行
3. **publish 操作留在 main agent**：git 操作需要用戶確認，不要在 subagent 中執行
4. **subagent 之間不共享 context**：每個 subagent 重新讀檔，不依賴前一個 subagent 的記憶
5. **並行限制**：research + writer 可以對不同文章並行，但同一文章的 writer 和 critic 必須串行
