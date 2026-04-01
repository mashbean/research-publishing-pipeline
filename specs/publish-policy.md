# Publish Policy

## 原則

push 不算完成，deploy success 也不算最終完成。以 live URL 驗證為準。

## 發稿流程

1. 寫入 final article 檔
2. 檢查 frontmatter
3. commit
4. push
5. watch deploy
6. 驗 live URL

## 最低驗證要求

### Deploy
- workflow 已完成
- status = success

### Live URL
- HTTP 200
- 標題正確
- 首段或 lead 正確
- canonical 短網址可用

### 路徑一致性
- canonical path 正常
- legacy path 若存在，應可正確導向 canonical 或顯示正確文章
- verbose long URL 行為明確且一致

## 失敗狀態

### publish-failed
- git push 失敗
- workflow 失敗
- build 卡住

### verification-failed
- live URL 404
- live title 錯誤
- old path 指到錯文
- canonical / legacy 行為不一致

## 完工定義

只有在下列條件全部成立時，文章才算真正完成：

- repo 已更新
- deploy success
- canonical live URL 內容正確
- 若有 long / legacy URL，也已驗證行為符合預期
