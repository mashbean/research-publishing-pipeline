# Multi-Agent Deep Research Spec

當核心命題的論證需要橫跨多個學科或論證類型時，**單一 research subagent 無法在合理 watchdog 視窗內完成深度檢索**。本 spec 定義 *5+1+1 multi-agent 模式*，把 deep research 階段拆成多個平行 Opus subagent，再加一個輕量整合 + 可選外部 cross-validation。

第一次成功應用：[2026-05-02-accountability-without-identification](../jobs/2026-05-02-accountability-without-identification/)（5 sub-arg × 6 sources × 250+ citations × 100+ A 級）。

## 何時啟用

啟用條件（任一成立）：

1. 核心命題的推理鏈包含 **≥ 4 個 sub-argument**，且每個 sub-arg 屬於不同檢索領域（政治哲學 / 密碼學 / 法律 / 政治經濟 / 公衛 / 標準化等）
2. 原始命題包含「強反論」或「邊界條件」需要獨立嚴格檢驗
3. 預估 deep research output ≥ 100KB

multi-agent 模式與「無 accent / accent」是 *獨立軸*。預設無 accent（自 2026-05-03 起），詳見 [mashbean-accent-opt-in.md](mashbean-accent-opt-in.md)。multi-agent 通常與預設無 accent 搭配（學術文章），但 opt-in accent 也可以走 multi-agent（如「個人 blog 但題目大到要拆 5 sub-arg」）。

不啟用：

- 單一領域的 blog 文（用標準 single-agent flow）
- 命題明確、推理鏈 ≤ 3 sub-arg
- 引用需求 ≤ 30 條

## 流程概觀

```
Step 1 推理鏈驗證（main agent）
   ↓ 拆出 N 個 sub-arg（建議 5）
Step 2 平行派 N 個 Opus sub-arg agents
   ↓ 每個 agent 寫 raw/sub-args/sub-arg-N-<topic>.md
Step 3 整合（main agent 直接做，不派 subagent）
   ↓ 寫 raw/deep-research-output.md
Step 4 [可選] 外部 cross-validation
   ↓ python3 scripts/run_external_deep_research.py <job-id>
   ↓ 寫 raw/external-deep-research-claude.md
Step 5 pipeline integrate
   ↓ python3 scripts/run_deep_research.py <job-id> integrate
   ↓ 推到 evidence-mapped 狀態
Step 6 進入既有 pipeline（writer → critic → rewriter → editor）
```

## Step 1 — 推理鏈驗證

main agent 先讀 intake.yaml，產出 1 頁推理鏈草稿，**暫停等使用者確認**。內容必須含：

- 核心問題（一句話）
- N 個 sub-arg（每個含主張、推理類型 D/I/A/Ab/C、推理強度、最關鍵的反例）
- 跨層級推論的明確標示
- 最脆弱的 1-2 個假設

確認後才往下推。這一步完全在主對話進行，不派 subagent。

## Step 2 — 平行 sub-arg agents

每個 sub-arg 派一個獨立 Opus subagent。**重要：5 個 agent 必須在同一個 main message 用平行 Agent tool calls 啟動**，否則退化為序列。

每個 sub-arg agent 的 prompt 必須包含：

1. **任務範圍**：「專責處理 Sub-Arg N：<主張>」
2. **規模要求**：≥ 3000 中文字、≥ 30 來源、A 級 ≥ 10
3. **必收 A 級來源清單**：5–10 條最權威的（main agent 預先寫好）
4. **多語言要求**：依領域調整（政治哲學含德文 Habermas / 法文共和主義；密碼學以 IACR ePrint / W3C / IETF / ISO；法律以判例原文）
5. **反例與反論**：明確要求 agent 找出能反駁主張的文獻
6. **跨層級警示**：標出可能失效的推論跳躍
7. **反事實**：≥ 2 個 well-developed 反事實
8. **輸出位置**：`raw/sub-args/sub-arg-N-<topic>.md`
9. **輸出結構**：固定 8-13 章（主張重述 / 檢索路徑 / 引用清單 / 推理鏈 / 跨層級警示 / 反事實 / 待開發 / 對其他 sub-arg 的銜接）

每個 sub-arg 預估 30-60 分鐘，背景跑（`run_in_background=true`）。

### Sub-Arg 拆分範例

從 [2026-05-02-accountability-without-identification](../jobs/2026-05-02-accountability-without-identification/) 經驗：

| Sub-Arg | 領域 | 推理類型 | 角色 |
|---|---|---|---|
| 1 | 政治哲學 | D（演繹） | 規範性基礎 |
| 2 | 密碼學工程 | I（歸納） | 工程可行性 |
| 3 | 法律先例 | A（類比） | 制度模板 |
| 4 | 因果機制 / 實證案例 | C（因果） | 反向驗證 |
| 5 | 邊界條件 | Ab（溯因） | 自我批判 |

不一定要 5 個；最少 4，最多 6（更多會讓整合難以管理）。

## Step 3 — 整合

**整合不派 subagent，由 main agent 直接做**。歷史教訓：subagent 嘗試整合 5 × 40KB 的輸入容易在 600 秒 watchdog 內無法產出，連續 stall。

main agent 整合工作流程：

1. 用 Bash 提取每個 sub-arg 的「§1 主張重述」（≈ 30-50 行）
2. 用 Bash 提取每個 sub-arg 的「§ 待開發 / 訪談需求」
3. 直接 Write 一份 `raw/deep-research-output.md`，含 8 個 SECTION：
   - `<!-- SECTION: research_summary -->` — 3 段，含三個論證升級
   - `<!-- SECTION: reasoning_chain -->` — 採各 sub-arg 的修訂版主張
   - `<!-- SECTION: evidence_map -->` — 跨 sub-arg 共同支撐主論點的 ≥ 15 條對照表 + 指向 5 份原檔
   - `<!-- SECTION: source_registry -->` — ≥ 30 條 A 級主清單 + 指向原檔
   - `<!-- SECTION: case_comparison -->` — 跨 sub-arg 案例對照
   - `<!-- SECTION: high_risk_claims -->` — 整合所有 [TODO-VERIFY] / 待查核
   - `<!-- SECTION: open_questions -->` — 整合所有 § 待開發
   - `<!-- SECTION: rewrite_warnings -->` — 給下游 writer 的指引

整合檔目標 50-80KB，不超過 100KB（過大會壓縮 writer 的輸入空間）。完整 250+ 引用清單由 5 份原檔承擔；整合檔僅做 *跨 sub-arg 索引*，不重複羅列。

`rewrite_warnings` 必須包含三個 *論證升級* 的提醒，否則 writer 會回退到 intake.yaml 原版主張。歷史教訓：sub-arg agent 的修訂版（如 pseudonymous vs real-name 區分、AML/KYC 反向倒戈等）若沒在 rewrite_warnings 中明確標示，writer 容易忽略。

## Step 4 — [可選] 外部 cross-validation

獨立路徑驗證。執行：

```bash
python3 scripts/run_external_deep_research.py <job-id>
```

該腳本用 Anthropic API + Opus 4.7 + adaptive thinking + web_search_20260209 + Task Budgets 跑獨立深度研究（細節見 `scripts/run_external_deep_research.py` docstring）。產出 `raw/external-deep-research-claude.md`。

**已知限制**：`web_search_20260209` 內建 dynamic filtering 使用 server-side Python sandbox。如果 Claude 把長文輸出寫到 sandbox 內部檔案，那份內容無法 export 回 `raw/`，只剩 stream 的摘要。這時 cross-validation 視為「軟通過」(無新矛盾即可)，不強求完整 11k 字外部研究包。

## Step 5 — pipeline integrate

```bash
python3 scripts/run_deep_research.py <job-id> integrate
```

把 `raw/deep-research-output.md` 的 8 個 SECTION 拆到對應檔案：

- `notes/research-summary.md`
- `notes/reasoning-chain.md`
- `verification/evidence-map.md`（必要）
- `notes/source-registry.md`
- `notes/case-comparison.md`
- `verification/high-risk-claims.md`
- `notes/open-questions.md`
- `notes/rewrite-warnings.md`

成功後狀態自動推進到 `evidence-mapped`。

## Step 6 — 進入既有 pipeline

從這裡開始與標準 single-agent flow 相同：

1. Writer subagent → `drafts/research-draft.md`
2. Critic subagent → `verification/fact-check-report.md`
3. Writer rewrite subagent → `drafts/blog-rewrite.md`（若 critic 要求修訂）
4. Editor subagent → `final/article-final.md`
5. `run_editorial_pass.py --auto-advance`

預設無 accent，editorial-pass 自動推進到 ready-to-publish。若 intake.yaml 含 `apply_mashbean_accent: true`，會走 accent-pending → accent subagent。詳見 [mashbean-accent-opt-in.md](mashbean-accent-opt-in.md)。

## 失敗模式與救援

### Sub-arg agent 全部完成但整合 stall

**徵兆**：sub-arg agent 都成功，integrator agent 600 秒 watchdog 無進展被殺。

**原因**：整合任務輸出體積過大（200KB+），subagent 在生成期間 stream 中斷。

**救援**：main agent 直接做整合（用 Bash 提取 + Write）。歷史上這個救援能在 5-10 分鐘完成。

### Sub-arg agent 修訂主張後與 intake.yaml 不一致

**徵兆**：writer 寫稿時用了 intake.yaml 的原版命題，沒採用 sub-arg agent 的修訂版（如 Sub-Arg 1 的 pseudonymous vs real-name 區分）。

**原因**：rewrite_warnings 未明確列出論證升級，或 writer 忽略。

**救援**：critic 階段會抓出這類偏差。如果 critic 也漏掉，editor 階段做最後檢查。

### 引用錯誤（出版形式 / 作者順序 / 期刊 vs 專書）

**徵兆**：critic 抓到 cite 與 source-registry 不一致（例：Halliday-Levi-Reuter 寫成 Cambridge UP 專書但實為 *UC Irvine J* 期刊論文）。

**原因**：source-registry 是 main agent 整合時憑印象寫，sub-arg 原檔通常正確。

**救援**：rewrite 階段 writer 對照 sub-arg 原檔修正 cite 並同步更新 source-registry.md。

### 外部 cross-validation 內容遺失在 sandbox

**徵兆**：`run_external_deep_research.py` 報告 output_tokens 很高（如 46K）但寫入的 `.md` 只有幾 KB。

**原因**：Claude 用 web_search 內建 sandbox 的 Python 寫了長檔，但該檔無法 export 回 host filesystem。

**救援**：把 stream 摘要中提到的 framing-level 發現整理進整合檔的 research_summary 末段（標明「外部 cross-validation」），不強求完整外部研究包。

## 啟動範例

```python
# Step 0: 標準 article job 建立（與 single-agent 相同）
python3 scripts/start_article_job.py 2026-MM-DD-<slug> \
  --title "..." \
  --audience "..." \
  --core-question "..." \
  --thesis "..." \
  --notes "multi-agent mode (no-accent default)"

# intake.yaml 預設無 accent，無需加旗標
# （若刻意要 mashbean accent：加 apply_mashbean_accent: true）

# Step 1: main agent 產出推理鏈草稿，暫停確認

# Step 2: main agent 同一 message 用 5 個平行 Agent calls 啟動 sub-arg agents
# 每個 prompt 必須含上述 9 點要求

# Step 3: 5 個都完成後（背景通知），main agent 用 Bash 提取 + Write 整合 deep-research-output.md

# Step 4 (optional): 啟動外部 cross-validation
python3 scripts/run_external_deep_research.py 2026-MM-DD-<slug>

# Step 5: 推進 pipeline
python3 scripts/run_deep_research.py 2026-MM-DD-<slug> integrate

# Step 6: 標準 writer → critic → rewrite → editor
```

## 與既有 pipeline 的關係

multi-agent 是 *opt-in 增強*，不取代既有 single-agent flow。判定樹：

```
intake.yaml core_question 含 ≥ 4 個獨立 sub-arg？
  ├─ 是 → multi-agent flow（本 spec）
  └─ 否 → single-agent flow（CLAUDE.md Step 3-7）
```

accent 是另一個獨立軸（與 multi-agent 無關）：

```
intake.yaml apply_mashbean_accent: true？
  ├─ 是 → editorial-pass 後走 accent-pending → accent subagent
  └─ 否（預設）→ editorial-pass 後直接 ready-to-publish
```

兩個 flow 在 Step 5 (integrate) 之後合流，用同一個 writer / critic / editor 階段。

## 後續延伸方向

- **start_multi_agent_research.py orchestrator script**：自動產出 sub-arg agent prompt 樣板，main agent 只需填入領域特定內容
- **動態 N**：根據推理鏈複雜度自動決定 sub-arg 數（4-6）
- **跨 article 引用 dedup**：當同一作者寫多篇 article（如 19 篇博論研究系列）時，跨 article 共用 source-registry
- **訪談清單聚合**：把多篇 article 的訪談需求聚合為一份「dissertation interview roadmap」

## 變更紀錄

- 2026-05-02：初版。基於 article 01 的成功經驗。
