# research-publishing-pipeline

研究文章自動生產線 — 從題目到上線發稿的半自動 pipeline，搭配 Claude Code 使用。

## 它做什麼？

給定一個研究題目，pipeline 自動走完：

```
intake → 研究 → 查核 → 寫作 → 編輯 → 發稿 → 線上驗證
```

每個階段由專門的 AI subagent 負責，狀態機自動管理流程推進與回退。

## 安裝

### 方法一：自動安裝（推薦）

```bash
git clone <this-repo-url> /tmp/research-pipeline
cd /tmp/research-pipeline
./setup.sh ~/your-project
```

### 方法二：手動安裝

```bash
# 1. 複製 pipeline 到你的專案
cp -R research-publishing-pipeline/ ~/your-project/tools/research-publishing-pipeline/

# 2. 安裝 /article 指令
mkdir -p ~/your-project/.claude/commands
cp .claude/commands/article.md ~/your-project/.claude/commands/article.md

# 3. 安裝 Python 依賴
pip3 install pyyaml
```

## 使用

安裝完成後，在 Claude Code 裡輸入：

```
/article 數位身份的零知識證明應用
```

或指定更多參數：

```
/article
題目：公共數位基礎設施的治理挑戰
讀者：科技政策研究者
核心問題：DPI 如何在效率與隱私之間取得平衡？
```

### 繼續未完成的文章

```
/article 繼續
```

### 查看所有 job 狀態

```bash
cd tools/research-publishing-pipeline
python3 scripts/run_pipeline.py <job-id> status
```

## Pipeline 架構

```
├── scripts/        # 自動化腳本（狀態機、研究、編輯、發稿）
├── prompts/        # Subagent 指令模板（research, writer, critic, editor, publish）
├── specs/          # 流程規範（workflow, citation, style, publish policy）
├── templates/      # Job 模板（intake.yaml, state.json, ...）
├── references/     # 案例研究
├── jobs/           # 文章 job 目錄（每篇文章一個資料夾）
├── docs/           # 使用指南
├── CLAUDE.md       # Claude Code 操作指南（pipeline 的大腦）
└── .claude/commands/article.md  # /article 指令定義
```

## 自訂

### 改寫風格規則

編輯 `specs/style-policy-zh.md` 和 `scripts/run_editorial_pass.py` 中的 pattern。

### 調整 agent 行為

編輯 `prompts/agent-*.md`：
- `agent-research.md` — 研究策略、來源收集方式
- `agent-writer.md` — 寫作風格、語氣、禁則
- `agent-critic.md` — 查核標準、evidence 要求
- `agent-editor.md` — 編輯標準、結構審查

### 自我引用偵測

在 `scripts/run_editorial_pass.py` 的 `SELF_CITATION_PATTERNS` 加入你的名字：

```python
(r"yourname,?\s*20\d{2}", "自我引用 placeholder"),
```

### 發稿目標

建立 job 時指定發稿 repo：

```bash
python3 scripts/start_article_job.py my-article \
  --publish-repo path/to/blog-repo
```

## 依賴

- Python 3.10+
- PyYAML (`pip install pyyaml`)
- Claude Code（CLI 或 IDE extension）
- gh CLI（optional，用於 deploy 偵測）

## 狀態機

```
intake → scoped → researching → evidence-mapped → drafted →
fact-checking → rewritten → editorial-pass → ready-to-publish →
published → verified
```

合法回退：
- `fact-checking → researching`（需補研究）
- `rewritten → fact-checking`（改寫新增未查核 claim）
- `editorial-pass → rewritten`（重大結構問題）

## License

MIT
