# mashbean-accent: Opt-in Spec（自 2026-05-03 起）

從 2026-05-03 開始，**research-publishing-pipeline 的預設語氣是學術／無 accent**。mashbean-accent skill 改為 opt-in，僅在 intake.yaml 顯式啟用時才套用。

歷史脈絡：article 01（[2026-05-02-accountability-without-identification](../jobs/2026-05-02-accountability-without-identification/)）以 `formal_academic: true` opt-in 跳過 accent。實踐後發現所有 pipeline 產出（學術文章、政策研究報告、博論章節）幾乎都應該是學術風格，accent 才是少數派。於是把預設翻轉。

## 預設模式（無 accent）

不需要任何旗標。pipeline 預設行為：

- **Writer**：產出論文式結構（脈絡 → 核心問題 → 章節 roadmap → 主體 → 條件性結論）
- **Editor**：跳過 mashbean-accent 校準整段
- **不引入** mashbean lexicon（啊哈、嘻嘻、XD、（遠目、颯爽、家己、歹勢 等）
- **不寫**自嘲、括號 meta 吐槽、跨領域錯位比喻
- 結尾**不寫**「回望式感性收束」
- 開頭**不情境定錨**個人故事
- `run_editorial_pass.py` 通過後直接推進到 `ready-to-publish`，跳過 `accent-pending`

適用情境：

- 博士論文章節初稿
- pro.mashbean.net 研究報告
- 學術引用密度高（≥ 30 條）的長文
- 政策分析、產業觀察、技術評估

## Opt-in 模式（apply_mashbean_accent）

`intake.yaml` 顯式設定 *任一* 旗標即啟用：

```yaml
apply_mashbean_accent: true
# 或
content_goal: personal_blog
```

啟用後行為：

- **Writer**：套用 mashbean-accent skill（自 `~/.claude/skills/mashbean-accent/`）的「九項自檢清單」，accent 命中 ≥ 1 即可，剩下交給 accent-pass
- **Editor**：執行第 3 節「mashbean-accent 語氣校準」整段
- 開頭情境定錨、結尾感性收束、lexicon 3-6 個自然分佈
- `run_editorial_pass.py` 通過後推進到 `accent-pending`，等 accent subagent 完成第二輪潤色

適用情境：

- mashbean.net 個人 blog 文章（情境敘事、生活反思、經驗分享）
- 對特定讀者群有「mashbean 本人聲音」期待的場合
- 技術內容仍需保留個人語氣痕跡的混合型文章

## 旗標優先序

| intake.yaml 設定 | 實際行為 | 備註 |
|---|---|---|
| 無設定 / 預設 | 無 accent | 自 2026-05-03 起的新預設 |
| `apply_mashbean_accent: true` | Accent | 顯式 opt-in |
| `content_goal: personal_blog` | Accent | 別名 |
| `formal_academic: true` | 無 accent | Legacy 別名（與預設一致，向後相容） |
| `content_goal: academic_paper` | 無 accent | Legacy 別名（與預設一致） |
| `apply_mashbean_accent: true` + `formal_academic: true` | Accent | 顯式 opt-in 優先於 legacy 別名 |

## 實作位置

| 文件 | 相關行 / 章節 |
|---|---|
| `scripts/run_editorial_pass.py` | line ~390-420：`apply_mashbean_accent` 判定 + state 推進 |
| `prompts/agent-editor.md` | 開頭「模式判定」章節 |
| `prompts/agent-writer.md` | 開頭「模式判定」章節 + 兩種模式的「必須做」分支 |
| `prompts/agent-accent.md` | accent subagent 自身規範（僅在 opt-in 才被觸發，內容不變） |
| `scripts/lib.py` | state machine 仍保留 accent-pending 狀態，僅在 opt-in 時用到 |
| `scripts/run_pipeline.py` | step_accent_pass 仍存在，僅在 opt-in 時觸發 |
| `prompts/agent-readability.md` | **無 accent 分支的對應關卡**（2026-07-30 新增）。opt-in accent 時**不跑**——accent 的口語化已涵蓋拆鷹架 |
| `scripts/lib.py` / `run_pipeline.py` | `readability-pending` 狀態與 `step_readability_pass`，僅在無 accent（預設）時觸發 |

> **2026-07-30 補記**：把 accent 改為 opt-in 時，沒有注意到 accent-pass 其實身兼兩職——它讓文章像 mashbean 寫的，也讓文章好讀。關掉 accent 等於同時關掉了可讀性的唯一守門員，而 critic → rewrite → editor 每一關都在往「更多限定語、更多顯式論證」推。這個缺口在〈中國基層參與的三十年〉發稿後由使用者回饋暴露，補法是新增 readability-pass 作為無 accent 分支的對應關卡。

## 測試

驗證預設行為（不應走 accent）：

```bash
# 建立一個測試 job，intake.yaml 不含 apply_mashbean_accent
python3 scripts/start_article_job.py 2026-05-03-test-default --title "..." --core-question "..." --thesis "..."
# ... 跑到 editorial-pass ...
python3 scripts/run_editorial_pass.py jobs/2026-05-03-test-default --auto-advance
# 預期：state advanced to ready-to-publish (no-accent default)
```

驗證 opt-in（應走 accent-pending）：

```yaml
# intake.yaml 加入
apply_mashbean_accent: true
```

```bash
python3 scripts/run_editorial_pass.py jobs/2026-05-03-test-accent --auto-advance
# 預期：state advanced to accent-pending (apply_mashbean_accent=true)
```

## blog-pro vs blog 對應

預設模式（無 accent）→ **blog-pro**（pro.mashbean.net）：

- frontmatter schema 見 `external/blog-pro/src/content.config.ts`
- collection: `reports`
- 必填：`title`、`description`、`pubDate`
- 建議：`aiModel`、`aiPipelineId`、`humanReviewed`

Opt-in accent 模式 → **blog**（mashbean.net）：

- frontmatter schema 見 blog 的 content config
- collection: `blog`
- 風格上是個人 blog 而非研究報告

## 給後續使用者的建議

絕大多數 pipeline 任務不需要動 `apply_mashbean_accent`——預設無 accent 就是你要的。

只在以下情形顯式 opt-in：

- 文章是純粹個人 blog（生活反思、活動心得、隨筆）
- 你刻意要 mashbean 個人語氣，而非客觀分析
- 文章預定發到 mashbean.net 而非 pro.mashbean.net

mashbean-accent skill 本身仍位於 `~/.claude/skills/mashbean-accent/`，可在 pipeline 外的場合（例如直接在主對話寫一篇 blog，不走 pipeline）獨立使用。

## 變更紀錄

- **2026-05-03**：翻轉預設。原本 `formal_academic: true` 是 opt-in 跳過 accent，現改為 `apply_mashbean_accent: true` 是 opt-in 加上 accent。原本的 `formal_academic` / `content_goal: academic_paper` 仍可用作 legacy 別名（與新預設一致）。
- **2026-05-02**：初版。當時 `formal_academic: true` 是 opt-in 跳過 accent，預設仍然走 mashbean-accent。
