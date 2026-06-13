# Workflow

## 目標

把研究文章生產拆成可驗收的階段，避免 research、writing、fact-check、publish 混成一團。

## 狀態機

```
intake → scoped → researching → evidence-mapped → drafted →
fact-checking → rewritten → editorial-pass →
[argmap-pending] →                                  # 可選，僅 civic-proof / opt-in
ready-to-publish → published → verified → social-shared
```

例外狀態：

- `blocked`
- `needs-decision`
- `publish-failed`
- `verification-failed`

### 合法回退路徑

以下回退在生產中已驗證為必要：

- `fact-checking → researching` — 發現 evidence gap 時需要補研究
- `rewritten → fact-checking` — 改寫過程新增了未經查核的 claim
- `editorial-pass → rewritten` — 發現重大結構或語氣問題需要重寫

回退時必須在 `state.json` 的 `versions[]` 記錄原因。

## 每階段最小交付物

### intake
- 題目或題目方向
- 核心問題
- 目標文體
- 已知來源或線索
- 禁則與限制

### scoped
- 文章要回答什麼
- 不回答什麼
- working thesis
- 高風險 claim 清單

### researching
- `prompts/deep-research-prompt.md` — 自動產出
- 初步來源蒐集
- 來源可信度分級

### evidence-mapped
- `verification/evidence-map.md` — claim 與 source 對照表
- 主要論點有對應證據

### drafted
- `drafts/research-draft.md` — 完整 research draft
- 可容許報告腔，但不可發明引用

### fact-checking
- `verification/fact-check-report.md` — claim-by-claim 檢查
- citation sanitation
- 高風險主張標記

### rewritten
- `drafts/blog-rewrite.md` — 已轉成 blog 或指定文體
- 已清除自引與禁用句型

### editorial-pass
- `verification/editorial-pass-report.md` — 自動化檢查報告
- 文字順序、標題、首段、節奏完成
- 沒有 prompt 洩漏或 PDF 腔

### argmap-pending（可選，僅 civic-proof 系列或 `generate_argmap: true`）
- `final/argmap.yaml` — v2 schema 完整
- `final/argument.argdown` — 由 `final/argmap.yaml` deterministic 轉換而來
- `final/argdown-render/<slug>/index.html` + `map.svg` — Argdown CLI 靜態渲染
- python yaml.safe_load 可解析
- Argdown CLI JSON/HTML/SVG map export 可解析（`validate_argdown.py` / `render_argdown_assets.py`）
- slug 欄位與 article report id 完全一致

### ready-to-publish
- `final/*.md` — frontmatter 完整
- 若觸發 argmap 則 `final/argmap.yaml` 已通過 yaml 驗證，且 Argdown source/render 已產生
- publish checklist 通過

### published
- `publish/publish-record.json` — commit SHA + deploy run
- commit + push 完成
- deploy 已開始

### verified
- `publish/live-check.json` — HTTP 驗證紀錄
- deploy success
- live URL 200
- live title / lead / canonical 行為正確

### social-shared
- `social/facebook.md` — Facebook 長版分享文（300-500 字）
- `social/threads.md` — Threads 短版分享文（200 字以內）
- 兩份檔案皆含 YAML frontmatter（platform, article_title, canonical_url, generated_at）

## 工作分層

### Writing pipeline
- intake
- scope
- research（自動產生 Deep Research prompt）
- evidence map（自動整合 Deep Research 結果）
- draft
- fact-check
- rewrite
- editorial pass（自動化禁則檢查）

### Repo pipeline
- render blog markdown
- write file
- commit + push（自動回寫 state.json）
- watch deploy
- live verify（自動回寫 state.json）

規則：未完成 writing pipeline 前，不進 repo pipeline。

## 自動化腳本對照

| 狀態轉換 | 腳本 | 自動化程度 |
|----------|------|-----------|
| intake → scoped | `run_pipeline.py auto` | 自動（驗證 intake 欄位） |
| scoped → researching | `run_deep_research.py generate-prompt` | 自動產生 prompt |
| researching → evidence-mapped | `run_deep_research.py integrate` | 自動整合結果 |
| drafted → fact-checking | `run_pipeline.py next` | 半自動（需人工 review） |
| rewritten → editorial-pass | `run_editorial_pass.py --auto-advance` | 自動檢查 + 推進 |
| argmap.yaml → argument.argdown/render | `run_pipeline.py <job-id> argdown` | 自動格式轉換 + CLI parser 驗證 + HTML/SVG 渲染，不新增 claim |
| ready-to-publish → published | `publish_blog_entry.py` | 自動（git + state） |
| published → verified | `verify_publish.py` | 自動（HTTP + state） |
| verified → social-shared | subagent (agent-social.md) | 自動產生 FB + Threads 分享文 |

## 多代理建議

- `research`：來源蒐集、可信度分級、evidence map
- `writer`：research draft、blog rewrite
- `critic`：fact-check、找過度主張與 citation 斷點
- `editor`：標題、首段、順稿、壓縮、語氣
- `social`：根據已發佈文章產出 Facebook + Threads 分享文
- `main`：狀態推進、repo 操作、發稿驗證

## 自動續推原則

- 任何研究文章 job 一旦正式啟動，就必須自動切換成 `activeWork=true`
- active 任務 10 分鐘檢查一次，直到 job 狀態進入 `verified`、`publish-failed`、`verification-failed`、`blocked` 或明確結案
- 若無新進展，先做一個 safe self-push，再回報
- 若 30 分鐘仍無實質進展，升級為 stalled watchdog
- stalled 時必須指出 blocked reason 與 recovery action
- 驗收目標：豆泥只要下啟動指令，工作流就自動往下跑，結束前不需要再額外下「請繼續」

## 版本追蹤

每次重大改版（Deep Research 整合、fact-check 後改稿、editorial pass 修正）必須在 `state.json` 的 `versions[]` 記錄：

```json
{
  "versions": [
    {"note": "Deep Research 結果整合完成", "at": "2026-03-30T14:00:00+08:00"},
    {"note": "fact-check 後重寫 v2", "at": "2026-03-30T16:00:00+08:00"}
  ]
}
```
