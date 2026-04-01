# 啟動指南：Chat / Cowork / Code

三種環境各有不同的啟動方式和適用場景。

---

## 短期方案（現在就能用）

### Chat（claude.ai 對話模式）

**適用場景**：探索題目、初步研究、跟 Deep Research 互動

**啟動方式**：

1. 在 Chat 中貼上你的題目和問題
2. 要求 Claude 產出結構化研究筆記，格式參照 `deep-research-packet.yaml`
3. 將 Chat 的研究成果複製出來，存成 `.md` 檔

**範例 prompt**：
```
我要寫一篇繁體中文 blog，主題是「非營利平台的永續經營」。
核心問題：非營利的社群平台能活下去嗎？
請幫我做以下研究：
1. 找出 5 個相關案例（至少 2 個失敗的）
2. 每個案例的收入結構和治理模式
3. 標記哪些主張需要更強的來源
輸出格式：evidence_map + source_notes + high_risk_claims
```

**接回 pipeline**：
```bash
# 將 Chat 的研究結果存檔
pbpaste > raw/deep-research-output.md  # macOS
python3 scripts/run_deep_research.py <job-id> save-raw raw/deep-research-output.md
python3 scripts/run_deep_research.py <job-id> integrate
```

---

### Cowork（claude.ai 協作模式 / Artifacts）

**適用場景**：文章共寫、即時編輯、討論修改方向

**啟動方式**：

1. 在 Cowork 中開啟一個 Artifact
2. 貼上 `drafts/research-draft.md` 或 `drafts/blog-rewrite.md`
3. 與 Claude 協作改寫

**範例 prompt**：
```
這是我的研究草稿（見 Artifact）。
請幫我轉成 blog 文體，注意以下禁則：
- 禁止「不是……而是……」句型
- 禁止報告腔
- 禁止正文濫用冒號
- 開頭要讓讀者知道這篇在回答什麼
```

**接回 pipeline**：
```bash
# 從 Cowork 複製修改後的文章
pbpaste > drafts/blog-rewrite.md
python3 scripts/update_job_state.py <job-id> --status rewritten \
  --last-deliverable drafts/blog-rewrite.md \
  --add-version-note "Cowork 協作改寫完成"
```

---

### Code（Claude Code CLI）

**適用場景**：全流程自動化、subagent 調度、發稿驗證

**啟動方式**：

```bash
cd tools/research-publishing-pipeline

# 一鍵建立 + 自動推進
python3 scripts/start_article_job.py 2026-04-01-my-topic \
  --title "文章標題" \
  --audience "讀者" \
  --core-question "核心問題" \
  --thesis "假說"

python3 scripts/run_pipeline.py 2026-04-01-my-topic auto
```

然後 Claude Code 會自動用 subagent 跑完 research → draft → fact-check → rewrite → editorial pass。

需要人工介入時 pipeline 會停下。完成 fact-check review 後：
```bash
python3 scripts/run_pipeline.py 2026-04-01-my-topic auto
```

---

## 中期方案（subagent 調度）

### Code 環境的 subagent 全自動流程

在 Claude Code 中直接說：

```
幫我寫一篇 blog，主題是「非營利平台能不能活下去」，
核心問題是「非營利社群平台有沒有永續經營的可能」，
讀者是關注數位治理的人。
用 research-publishing-pipeline 跑完整流程。
```

Claude Code 會：
1. 讀取 `CLAUDE.md` 了解流程
2. 建立 job
3. 自動 spawn research subagent → writer subagent → critic subagent → editor subagent
4. 在 fact-check 完成後暫停，等你確認
5. 確認後自動 publish + verify

### 跨環境協作流程（推薦）

```
Chat           Cowork          Code
 │               │               │
 ├─ 探索題目      │               │
 ├─ Deep Research │               │
 │               │               │
 │    save-raw ──────────────────→├─ integrate
 │               │               ├─ auto (draft → fact-check)
 │               │               │
 │               ├─ 協作改寫 ←────┤  (export blog-rewrite.md)
 │               ├─ 來回修改      │
 │               │               │
 │    pbpaste ───────────────────→├─ editorial pass
 │               │               ├─ publish
 │               │               ├─ verify
 │               │               └─ done ✓
```

**關鍵原則**：
- **Chat** 負責發散思考和 Deep Research
- **Cowork** 負責文章共寫和即時編輯
- **Code** 負責狀態管理、品質檢查和發稿

---

## 三環境快速對照

| 動作 | Chat | Cowork | Code |
|------|------|--------|------|
| 探索題目 | ✓ 最佳 | ○ 可用 | △ 太重 |
| Deep Research | ✓ 最佳 | △ 不適合 | ○ 用 subagent |
| 文章共寫 | ○ 可用 | ✓ 最佳 | ○ 用 subagent |
| 禁則檢查 | △ 手動 | △ 手動 | ✓ 全自動 |
| Fact-check | ○ 可用 | ○ 可用 | ✓ 用 subagent |
| 發稿 | ✗ 無法 | ✗ 無法 | ✓ 唯一管道 |
| 驗證 | ✗ 無法 | ✗ 無法 | ✓ 全自動 |
| 狀態管理 | ✗ 無法 | ✗ 無法 | ✓ 全自動 |
