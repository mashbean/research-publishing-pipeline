# Other-computer agent quickstart

這份 quickstart 給另一台電腦上的 agent 或人類操作者使用。

目標：在另一台電腦上，用最短步驟啟動一條研究文章 pipeline。

## 0. 先決條件

- 已能存取 `mashbean/ai-agent-workspace`
- 本機有 `python3`
- agent 或操作者有 shell / file access

## 1. 取得最新版本

若尚未 clone：

```bash
git clone https://github.com/mashbean/ai-agent-workspace.git
cd ai-agent-workspace
```

若已存在本機：

```bash
cd ai-agent-workspace
git pull origin main
```

## 2. 進入 pipeline 目錄

```bash
cd tools/research-publishing-pipeline
```

## 3. 用單指令建立 research job

```bash
python3 scripts/start_article_job.py <job-id> "<task-note>" "<next-deliverable>" "<intake-title-hint>"
```

### 範例

```bash
python3 scripts/start_article_job.py \
  2026-03-30-agent-extension \
  "啟動研究文章 pipeline" \
  "完成 intake 與 deep research packet" \
  "代理人（Agent）如何成為人的延伸"
```

## 4. 啟動後會發生什麼

這個腳本目前會自動完成：

1. 建立 `jobs/<job-id>/`
2. 複製 intake / packet / verification 模板
3. 生成 `deep-research-packet.yaml`
4. 更新 automation state，把這條 job 標成已啟動
5. 將 `intake.yaml` 的 `title_hint` 先填入

## 5. 接下來 agent 應做什麼

進入新 job 後，按狀態機往下推：

`intake -> scoped -> researching -> evidence-mapped -> drafted -> fact-checking -> rewritten -> editorial-pass -> ready-to-publish -> published -> verified`

對應最小任務：

- 補完 `intake.yaml`
- 確認 `deep-research-packet.yaml` 是否足夠
- 產生 evidence map
- 寫 research draft
- 跑 fact-check
- 改寫成發文稿
- 做 editorial pass
- 發稿並驗 live URL

## 6. 如果目標是發到 pro.mashbean.net

在 `intake.yaml` 內建議填：

```yaml
publish_target:
  repo: blog-pro
  collection: reports
  file_hint: 2026-03-30-your-topic
```

## 7. 如果目標是發到 mashbean.net 主站

只有 human / human-first 文章才應進主站。

若是 AI pipeline 研究文，請改發 `blog-pro`，不要進 `mashbean.net`。

## 8. 最常用口頭指令

如果是 agent 對話模式，推薦直接說：

- 「到 `ai-agent-workspace/tools/research-publishing-pipeline` 幫我開一條 research job，題目是 XXX，目標發到 pro.mashbean.net。」
- 「先 `git pull`，再開一個研究 job，主題是 XXX。」

## 9. 完工判定

只有下列條件都成立，才算結案：

- repo 已更新
- deploy success
- live URL 驗證成功
- 標題 / lead / canonical 行為正確
