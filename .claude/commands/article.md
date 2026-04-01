---
description: Start or continue an article job using the research publishing pipeline
allowed-tools: Agent, Bash, Read, Write, Edit, Glob, Grep, TodoWrite
---

# Article Pipeline Command

使用者要求啟動或繼續一篇研究文章。

## 指令

找到 pipeline 根目錄（含 `CLAUDE.md` 的 `research-publishing-pipeline/` 資料夾），讀取其中的 `CLAUDE.md` 了解完整流程。

提示：pipeline 可能在以下位置之一：
- `tools/research-publishing-pipeline/`
- 專案根目錄（如果此 repo 本身就是 pipeline）

## 如果使用者提供了題目（新文章）

1. 從使用者訊息中提取：title, audience, core_question, thesis
2. 產生 job-id（格式：`YYYY-MM-DD-topic-slug`）
3. 進入 pipeline 目錄，執行：
```bash
python3 scripts/start_article_job.py <job-id> \
  --title "<title>" \
  --audience "<audience>" \
  --core-question "<question>" \
  --thesis "<thesis>"
python3 scripts/run_pipeline.py <job-id> auto
```
4. 根據 CLAUDE.md 的指示，用 subagent 分派 research → writer → critic → editor
5. 在需要人工確認的步驟暫停

## 如果使用者要繼續現有文章

1. 找到最新的 job：
```bash
ls -t <pipeline-dir>/jobs/ | head -5
```
2. 查看狀態：
```bash
python3 scripts/run_pipeline.py <job-id> status
```
3. 根據當前狀態繼續下一步

## 使用者的輸入

$ARGUMENTS
