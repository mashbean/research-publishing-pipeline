# Research Publishing Pipeline — Claude Code 操作指南

本目錄是研究文章自動生產線。當使用者要求寫文章、做研究、發稿時，請依照此指南操作。

## 啟動條件

當使用者說以下任何一種話時，啟動 pipeline：
- 「寫一篇文章」「幫我寫 blog」
- 「研究 X 主題」
- 「啟動 article job」
- 提供了題目 + 來源 + 核心問題

## 模式判定（在 Step 0 之前先決定）

**預設行為（自 2026-05-03 起）= 學術／無 accent**。mashbean-accent 改為 opt-in，僅當 intake.yaml 顯式啟用時才套用。

intake.yaml 的兩個欄位決定走哪條路徑：

| `apply_mashbean_accent` | `core_question` 結構 | 模式 | Spec |
|---|---|---|---|
| `false` 或未設（**預設**） | ≥ 4 個獨立 sub-arg | **學術 + multi-agent**（無 accent） | [specs/mashbean-accent-opt-in.md](specs/mashbean-accent-opt-in.md) + [specs/multi-agent-deep-research.md](specs/multi-agent-deep-research.md) |
| `false` 或未設（**預設**） | ≤ 3 個 sub-arg | **學術 + single-agent**（無 accent） | [specs/mashbean-accent-opt-in.md](specs/mashbean-accent-opt-in.md) |
| `true` 或 `content_goal: personal_blog` | 任意 | **Blog（含 mashbean-accent）** | [specs/mashbean-accent-opt-in.md](specs/mashbean-accent-opt-in.md) §「Opt-in」 |

**預設不啟用 mashbean-accent**：editor agent 不引入 lexicon、不寫自嘲、不寫括號 meta、不下跨領域比喻；`run_editorial_pass.py` 直接推進到 ready-to-publish。
**Opt-in accent 模式**：editor 與 writer 套用 mashbean-accent skill；editorial-pass 通過後推進到 accent-pending 等 accent subagent。
**Multi-agent 模式**會把 Step 3 deep research 拆成 5+1 個平行 subagent，整合工作由 main agent 直接做。

學術模式輸出預設發布到 **blog-pro**（pro.mashbean.net），accent 模式才發到 mashbean.net。

**Legacy 別名（向後相容）**：`formal_academic: true` / `content_goal: academic_paper` 仍被識別為「無 accent」信號（與預設一致，不再需要手動設定）。

## Pipeline 操作流程

### Step 0: 建立 Job

```bash
python3 scripts/start_article_job.py <job-id> \
  --title "..." --audience "..." --core-question "..." --thesis "..."
```

### Step 1: 論證架構驗證（P1 新增，人工確認後才往下）

在進入 deep research 之前，**必須先驗證核心論證的推理鏈是否成立**。

1. 根據 intake.yaml 中的 core_question 和 thesis，產出 1 頁的推理鏈草稿（可直接輸出到對話中，不需要存檔）
2. 推理鏈草稿必須包含：
   - 核心問題 → 3-5 個子論點 → 合成結論
   - **每個推理跳躍的明確標示**：「從 A 推論到 B，依據是什麼？這個推論是類比、歸納、還是因果？」
   - **最脆弱的假設**：整條推理鏈最可能被質疑的 1-2 個環節
   - **如果 thesis 涉及跨層級推論**（例如從國家層級推到個人層級、從一個場域推到所有場域），必須明確標示並論證為什麼推論成立
3. **暫停，等待使用者確認**推理鏈成立後，才進入 Step 2

這一步的目的是避免「研究了大量素材後才發現推理方向不對」的浪費。如果推理鏈在這一步就被質疑，應該在修正論證方向後再進入 deep research。

### Step 2: 自動推進到 Deep Research

```bash
python3 scripts/run_pipeline.py <job-id> auto
```

Pipeline 會自動：intake → scoped → researching，然後停下等 Deep Research。

### Step 3: Research（用 subagent）

#### 3a. Single-agent 流程（標準 blog）

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

#### 3b. Multi-agent 流程（學術 + ≥4 sub-arg）

完整流程詳見 [specs/multi-agent-deep-research.md](specs/multi-agent-deep-research.md)。摘要：

1. **平行派 5 個 Opus sub-arg agents**（同一 message、平行 Agent calls）。每個 prompt 含領域、主張、必收 A 級來源 5-10 條、≥30 來源/≥10 A 級規模、輸出位置 `raw/sub-args/sub-arg-N-<topic>.md`。
2. **整合不派 subagent**——main agent 直接用 Bash 提取每份 sub-arg 的 § 1 主張重述 + § 待開發，然後 Write 一份 `raw/deep-research-output.md`，含 8 個 SECTION marker。歷史教訓：subagent 整合會 stall 在 600 秒 watchdog。
3. **可選：外部 cross-validation**：
   ```bash
   python3 scripts/run_external_deep_research.py <job-id>
   ```
   獨立 Anthropic API 路徑（Opus 4.7 + adaptive thinking + web_search）跑第二意見。
4. 最後跑 `python3 scripts/run_deep_research.py <job-id> integrate` 把 8 個 SECTION 拆到 notes/ + verification/。

整合檔的 `<!-- SECTION: rewrite_warnings -->` **必須** 列出 sub-arg agent 在文獻檢索後對主張的修訂版（如「pseudonymous vs real-name identification 區分」、「accountable pseudonymity 是政治經濟成就」等），否則下游 writer 容易回退到 intake.yaml 原版命題。

### Step 4: Writer（用 subagent）

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

### Step 5: Critic（用 subagent）

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

### Step 6: Writer rewrite（用 subagent）

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

### Step 7: Editor（用 subagent）

```
Agent(
  description="Editorial pass for <job-id>",
  subagent_type="general-purpose",
  prompt="你是編輯代理。讀取 <job-dir>/prompts/agent-editor.md 的完整指令，\n讀取 blog-rewrite.md，執行結構審查、禁則巡檢、語氣校準，\n產出 final/article-final.md。完成後執行：\npython3 scripts/run_editorial_pass.py <job-dir> --auto-advance"
)
```

### Step 7.5: Accent Pass（用 subagent，**僅 opt-in accent 模式**）

> **預設模式不會走到這一步**。`run_editorial_pass.py` 在 `apply_mashbean_accent: true` 未設時直接從 editorial-pass 推進到 `ready-to-publish`。Step 7.5 僅在 intake.yaml 含 `apply_mashbean_accent: true` 或 `content_goal: personal_blog` 時觸發。詳見 [specs/mashbean-accent-opt-in.md](specs/mashbean-accent-opt-in.md)。

opt-in accent 模式下，editorial-pass 通過後會推進到 `accent-pending`，等 accent subagent 套用 mashbean-accent skill。

這個階段專責「讓文章讀起來像 mashbean 本人寫的」——修開頭、加自嘲、加括號 meta 吐槽、加跨領域比喻、改結尾為回望式收束。前面所有 agent 都被「研究正確性」目標壓著會把人味磨掉，這個階段是專門救援。

```
Agent(
  description="Accent pass for <job-id>",
  subagent_type="general-purpose",
  prompt="你是 accent 代理。讀取 prompts/agent-accent.md 的完整指令，\n以及 mashbean-accent skill（/Users/mashbean/.claude/skills/mashbean-accent/）。\n讀取 final/article-final.md 與 verification/editorial-pass-report.md，\n執行 accent 潤色，**直接覆寫** final/article-final.md。\n完成後執行：python3 scripts/run_editorial_pass.py <job-dir> --auto-advance\n（PASS 且狀態為 accent-pending → 自動推進到 ready-to-publish）"
)
```

完成後狀態會自動推進到 `ready-to-publish`（editorial-pass 重跑時會偵測到狀態是 `accent-pending` 並推進）。

**accent-pass 的紅線**：
- 不動引用編號 `<sup>N</sup>` 與參考資料區
- 不新增實證主張
- 不刪掉誠實邊界的限定語（但可以把語氣口語化）
- 自檢清單九項至少命中六項，少於六項必須補

### Step 7.6: Argmap（用 subagent，**僅 civic-proof 系列或 opt-in**）

> **觸發條件**：intake.yaml 含 `generate_argmap: true`，或 `notes` 含 `civic-proof` 系列關鍵字（W1/W2/W3/.../博論章節對應）。一次性 blog 文章不執行。

把已通過 editorial-pass（與 accent-pass，若有）的最終稿轉成 v2 argmap YAML。argmap 是已通過論證的視覺化結構，不是新分析——argmap pass 不重新做研究、不引入新 claim、不修改文章。

```
Agent(
  description="Argmap pass for <job-id>",
  subagent_type="general-purpose",
  prompt="你是 argmap 代理。讀取 prompts/agent-argmap.md 的完整指令。\n讀取 final/article-final.md、intake.yaml、notes/reasoning-chain.md（若有）、\nverification/fact-check-report.md（若有）、verification/rewrite-warnings.md（若有），\n產出 final/argmap.yaml。發稿時會由 publish 一起推到 blog-pro。\n\n結構參考：external/blog-pro/src/content/argmaps/2026-05-02-accountability-without-identification.yaml（v2 範本主檔）。"
)
```

完成後驗證 YAML 可解析：

```bash
python3 -c "import yaml; yaml.safe_load(open('jobs/<job-id>/final/argmap.yaml'))"
```

接著產出 Argdown 交換格式與本地渲染檔：

```bash
python3 scripts/run_pipeline.py <job-id> argdown
```

這會從 `final/argmap.yaml` deterministic 轉換成 `final/argument.argdown`，再輸出
`final/argdown-render/<slug>/index.html` 與 `final/argdown-render/<slug>/map.svg`。
Argdown 是公開交換／視覺化輸出，不是第二套正本；不得新增 claim、不得重寫文章、不得取代 `argmap.yaml`。
轉換器會把正文清成 Argdown parser-safe 文字；完整公式與 rich text 仍以 `argmap.yaml` 為準。

若要分段除錯，可單獨執行：

```bash
python3 scripts/generate_argdown.py <job-id>
python3 scripts/validate_argdown.py <job-id>
python3 scripts/render_argdown_assets.py <job-id>
```

argmap.yaml 上線後會自動被 blog-pro 的 master map（`/civic-proof-map/`）抓到——
透過 `getCollection("argmaps")` 動態查詢，**不需要手動編輯** `src/pages/civic-proof-map.astro`。
僅當文章引入了 19 篇 dissertation outline 之外的全新母命題時，才需要手動補 main map 的
`articles` 與 `crossLinks`。

### Step 8: Publish + Verify

```bash
python3 scripts/run_pipeline.py <job-id> publish
python3 scripts/run_pipeline.py <job-id> verify
```

**若有 `final/argmap.yaml`**：發稿時 publish 腳本必須把它一併推到
`external/blog-pro/src/content/argmaps/<slug>.yaml`，與 report 在同一個 commit
（或同一個 gh api PUT 批次）。argmap collection 用 glob loader 自動 pick up，
不需要修改 content.config.ts。

若有 `final/argmap.yaml` 但缺 `final/argument.argdown`，`run_pipeline.py publish`
會先自動補跑 argdown step。publish 腳本也會把 `final/argument.argdown` 複製到
`external/blog-pro/src/content/argdowns/<slug>.argdown`，並把 HTML/SVG 渲染資產輸出到
`external/blog-pro/public/argdown/<slug>/`，讓 `/argmaps/<slug>/` 在頁尾直接顯示 SVG 圖表與 source。

### Step 9: Social Share（用 subagent）

文章驗證上線後，自動產生社群分享文。

```
Agent(
  description="Generate social posts for <job-id>",
  subagent_type="general-purpose",
  prompt="你是社群分享代理。讀取 <job-dir>/prompts/agent-social.md 的完整指令，\n然後讀取 <job-dir> 中的 final/*.md、intake.yaml、publish/publish-record.json，\n產出 social/facebook.md 和 social/threads.md。"
)
```

完成後結案：
```bash
python3 scripts/update_job_state.py <job-id> --status social-shared --last-deliverable social/
python3 scripts/sync_automation_state.py end "Published + social ready: <title>"
```

## 狀態檢查

隨時可以查看 job 狀態：
```bash
python3 scripts/run_pipeline.py <job-id> status
```

## Subagent 使用原則

1. **research / writer / critic / editor / social 用 subagent**：這些任務吃大量 context，用 subagent 保護主對話
2. **狀態管理留在 main agent**：`update_job_state.py` 和 `run_pipeline.py` 由主對話執行
3. **publish 操作留在 main agent**：git 操作需要用戶確認，不要在 subagent 中執行
4. **subagent 之間不共享 context**：每個 subagent 重新讀檔，不依賴前一個 subagent 的記憶
5. **並行限制**：research + writer 可以對不同文章並行，但同一文章的 writer 和 critic 必須串行
6. **結構變更後必須檢查推理鏈**（P2 新增）：當使用者要求刪除章節、重組結構、或大幅修改論證方向時，主 agent 在轉發給 subagent 之前應附加指令：「完成修改後，重新檢查推理鏈是否完整。如果刪除的內容原本支撐某個論點，該論點是否仍有其他支撐？如有推理斷裂，請標示並建議補救方案，而非無聲地執行刪除。」
7. **整合大型 subagent 輸出由 main agent 直接做**：當需要把多份 subagent 輸出（總計 ≥ 200KB）合成為單一檔案時，**不要派 integrator subagent**——歷史教訓：subagent 在 600 秒 watchdog 視窗內無法產出 100KB+ 的單檔輸出，會 stall。改由 main agent 用 Bash 提取 + Write 直接做。

## 預設無 accent + Multi-agent 模式（2026-05-03 起）

**Pipeline 預設行為已從「accent」翻轉為「學術／無 accent」**。原本 `formal_academic: true` 是 opt-in 跳過 accent，現在反過來：什麼都不設 = 無 accent，`apply_mashbean_accent: true` 才走 accent 流程。

兩個關鍵旗標：

- **`apply_mashbean_accent: true`**（opt-in，預設 false）：套用 mashbean-accent skill，走 accent-pending 階段；輸出對應 blog（mashbean.net）。詳見 [specs/mashbean-accent-opt-in.md](specs/mashbean-accent-opt-in.md)。
- **Multi-agent 模式**（命題含 ≥ 4 sub-arg）：Step 3 deep research 由 5 個平行 Opus subagent + main agent 整合 + 可選外部 cross-validation 完成。與 accent 旗標獨立，兩者可組合。詳見 [specs/multi-agent-deep-research.md](specs/multi-agent-deep-research.md)。

mashbean-accent 不再是 pipeline 的預設語氣。它仍可在 pipeline 外的個人 blog 寫作（例如直接呼叫 mashbean-accent skill 寫一篇日記式文章）使用。

### 外部 cross-validation 工具

`scripts/run_external_deep_research.py` 用 Anthropic API 直接跑 Opus 4.7 + adaptive thinking + web_search + Task Budgets，提供獨立第二意見：

```bash
pip3 install anthropic              # 一次性安裝
# 把 ANTHROPIC_API_KEY 寫進 AI-Agent 根目錄的 .env

python3 scripts/run_external_deep_research.py <job-id>
```

腳本會自動讀 `.env`（即使 sandbox 把 ANTHROPIC_API_KEY 設為空字串也能 fallback），預設 effort=`xhigh`、max_uses=30、task_budget=250000。輸出 `raw/external-deep-research-claude.md`。

**已知限制**：`web_search_20260209` 內建 dynamic filtering 使用 server-side Python sandbox。若 Claude 把長文寫到 sandbox 內部檔案，該檔無法 export 回 host filesystem，stream 只剩摘要。這時視為「軟通過」（無新矛盾即可），不強求完整外部研究包。

## 啟動範例（學術 + multi-agent）

```bash
# Step 0
python3 scripts/start_article_job.py 2026-05-02-<slug> \
  --title "..." \
  --core-question "..." \
  --thesis "..."

# 編輯 intake.yaml 加 formal_academic: true 與 content_goal: academic_paper

# Step 1: main agent 做推理鏈，暫停確認

# Step 2: main agent 同一 message 平行派 5 個 sub-arg agents（每個 prompt 含領域 + 必收 A 級）

# Step 3: 5 個都完成後，main agent 用 Bash 提取 + Write 整合 deep-research-output.md

# Step 4 (optional): 外部 cross-validation
python3 scripts/run_external_deep_research.py 2026-05-02-<slug>

# Step 5: 推進 pipeline
python3 scripts/run_deep_research.py 2026-05-02-<slug> integrate

# Step 6+: writer → critic → rewrite → editor（學術模式自動跳 accent）
```
