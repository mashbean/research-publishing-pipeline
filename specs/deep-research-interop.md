# Deep Research 協作規範

## 目標

無論 Deep Research 由 ChatGPT、Claude chat、Claude Code subagent、還是 Codex 執行，都能產出結構化輸出，讓 pipeline 自動整合。

## 問題：目前為什麼不通

1. Deep Research 輸出是自由格式 markdown，章節名稱不固定
2. `run_deep_research.py integrate` 靠 header 名稱模糊匹配，容易漏
3. 不同工具（ChatGPT vs Claude）的輸出結構差異大
4. 沒有明確告訴 Deep Research 要輸出什麼結構
5. 研究結果回來後，需要人工判斷放到哪個檔案

## 解法：結構化輸出協定

### 輸出格式

Deep Research 必須輸出以下固定結構，使用 `<!-- SECTION: name -->` 標記分隔：

```markdown
<!-- SECTION: research_summary -->
# 研究摘要
[2-3 段，概述研究發現]

<!-- SECTION: reasoning_chain -->
# 推理鏈

## 核心問題
[一句話]

## 推理路徑

### Sub-Arg 1: [名稱]
- **主張**: ...
- **推理類型**: I/D/A/Ab/C
- **支撐證據**:
  1. [來源等級] 來源描述 → 關鍵發現
  2. ...
- **推理強度**: 強/中/弱
- **反例/限制**: ...

### Sub-Arg 2: ...

## 合成結論
- **結論**: ...
- **推理路徑**: Sub-Arg 1 (I) + Sub-Arg 2 (C) → Synthesis
- **結論強度**: 強/中/弱
- **已知盲點**: ...

<!-- SECTION: evidence_map -->
# 證據對照表

| # | 主張 | 來源 | 來源等級 | 信心度 | 查閱日期 | 備註 |
|---|------|------|---------|--------|---------|------|
| 1 | ... | ... | A/B/C | 高/中/低 | 2026-03-30 | ... |

<!-- SECTION: source_registry -->
# 來源清冊

## 學術文獻
- Author (Year). *Title*. Journal/Publisher. DOI/URL

## 官方文件
- Organization. "Title." URL (查閱日期)

## 案例與報導
- Source. "Title." URL (查閱日期)

<!-- SECTION: case_comparison -->
# 案例正反對照

| 類別 | 成功案例 | 失敗案例 | 對照意義 |
|------|---------|---------|---------|
| ... | ... | ... | ... |

## 案例結構化資料

### [案例名稱]
- 類型: ...
- 成立年份: ...
- 狀態: active / struggling / failed / acquired
- 法律結構: ...
- 收入模式: ...
- 年收入: ... (來源, 年份)
- 使用者規模: ... (來源, 查閱日期)
- 治理模式: ...
- 關鍵風險: ...
- 失敗原因: ... (如適用)

<!-- SECTION: high_risk_claims -->
# 高風險主張

| # | 主張 | 風險類型 | 說明 | 建議處理 |
|---|------|---------|------|---------|
| 1 | ... | 因果混淆 / 倖存者偏差 / 範疇滑移 / 數據過時 | ... | 改寫為... |

<!-- SECTION: open_questions -->
# 未解問題
- [ ] ...
- [ ] ...

<!-- SECTION: rewrite_warnings -->
# 改寫注意事項
- ...
```

### 為什麼用 HTML comment 標記

1. **ChatGPT / Claude chat 都能產出**：HTML comment 是 markdown 標準語法
2. **機器可解析**：`re.split(r'<!-- SECTION: (\w+) -->')` 一行搞定
3. **人類可讀**：comment 不影響 markdown 渲染
4. **容錯**：即使少了某個 section，其他 section 仍可獨立解析

## 在不同工具中的使用方式

### ChatGPT Deep Research

在 prompt 末尾加上：

```
## 輸出格式要求

請使用以下結構輸出，每個章節用 <!-- SECTION: name --> 標記開頭：

必要章節（按順序）：
1. <!-- SECTION: research_summary --> 研究摘要
2. <!-- SECTION: reasoning_chain --> 推理鏈（含核心問題、子論點、合成）
3. <!-- SECTION: evidence_map --> 證據對照表（markdown 表格）
4. <!-- SECTION: source_registry --> 來源清冊（按學術/官方/案例分類）
5. <!-- SECTION: case_comparison --> 案例正反對照表 + 結構化資料
6. <!-- SECTION: high_risk_claims --> 高風險主張
7. <!-- SECTION: open_questions --> 未解問題
8. <!-- SECTION: rewrite_warnings --> 改寫注意事項

這些標記讓下游工具可以自動拆分你的研究成果。
```

### Claude Chat

同樣在 prompt 末尾附上格式要求。Claude 對指定結構的遵從度高。

### Claude Code Subagent

subagent prompt 中直接引用本規範：

```python
Agent(
  prompt=f"讀取 {job_dir}/prompts/agent-research.md 和 specs/deep-research-interop.md，"
        f"按照結構化輸出協定產出研究成果，存到 {job_dir}/raw/deep-research-output.md"
)
```

### Codex (OpenAI)

Codex 環境中執行 research task 時，在 task description 中包含格式要求。
Codex 的輸出存到 `raw/deep-research-output.md`，然後由 pipeline 整合：

```bash
python3 scripts/run_deep_research.py <job-id> integrate
```

## 自動整合流程

`run_deep_research.py integrate` 的解析邏輯：

```
1. 讀取 raw/deep-research-output.md
2. 用 <!-- SECTION: (\w+) --> 切割
3. 每個 section 寫入對應檔案：
   - research_summary → notes/research-summary.md
   - reasoning_chain → notes/reasoning-chain.md
   - evidence_map → verification/evidence-map.md
   - source_registry → notes/source-registry.md
   - case_comparison → notes/case-comparison.md
   - high_risk_claims → verification/high-risk-claims.md
   - open_questions → notes/open-questions.md
   - rewrite_warnings → notes/rewrite-warnings.md
4. 更新 state.json: status → evidence-mapped
5. 如果 reasoning_chain 存在，status 直接到 evidence-mapped
   如果只有 evidence_map，同樣到 evidence-mapped
   如果什麼都沒解析到，fallback 整份存到 drafts/research-draft.md
```

## 品質閘門

integrate 完成後，自動檢查：

1. `evidence_map` 是否存在且非空
2. `reasoning_chain` 是否包含至少 2 個 Sub-Arg
3. `case_comparison` 是否包含至少 1 個失敗案例
4. `source_registry` 是否包含至少 1 個 A 級來源

任一項不通過 → status 設為 `needs-decision`，標明缺少什麼。
