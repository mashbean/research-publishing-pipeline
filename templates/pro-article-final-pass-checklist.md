# Pro article final-pass checklist

這份 checklist 給 `pro.mashbean.net` 的 AI research 文章使用。

目標：在 publish 前，用固定順序完成最後一輪文字、格式、部署驗證。

## A. 標題與摘要

- [ ] 標題已對齊文章真正重點
- [ ] `description` 與標題一致，沒有各講各的
- [ ] 首段或導言有清楚交代這篇要處理什麼問題
- [ ] 若是回應文，已明確交代回應對象或原文

## B. AI disclosure 口徑

- [ ] 有保留 AI 協作揭露段落
- [ ] AI 模型、文章定位、回應關係寫法一致
- [ ] 沒有 prompt 洩漏感或內部工具腔

## C. 中文寫作 final pass

- [ ] 已巡檢 `不是`
- [ ] 已巡檢 `而是`
- [ ] 已巡檢 `不只`
- [ ] 已避免正文依賴「不……而……」骨架
- [ ] 已避免正文濫用冒號
- [ ] 沒有明顯 PDF 腔、報告腔或 AI 腔節奏

## D. 研究與引用

- [ ] 沒有明顯自我引用污染
- [ ] 高風險主張已經過 fact-check
- [ ] 文章中的結論強度與證據強度相稱
- [ ] 沒有把局部觀察寫成普遍定律

## E. Frontmatter

- [ ] `title` 完整
- [ ] `description` 完整
- [ ] `pubDate` 正確
- [ ] `tags` 合理
- [ ] `category` 合理
- [ ] `aiModel` / `aiPrompt` / `aiPipelineStage` / `aiGeneratedDate` / `humanReviewed` 已填

## F. Repo / build

- [ ] 本機 build 通過
- [ ] 目標檔名與 slug 合理
- [ ] commit message 清楚
- [ ] push 已完成

## G. Live verify

- [ ] deploy success
- [ ] live URL 回傳 200
- [ ] live title 正確
- [ ] live description / 首段行為正確
- [ ] canonical path 正常

## 完工定義

只有在 A-G 都過關後，這篇文章才算真正完成。
