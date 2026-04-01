# 引用整合規範

## 目標

引用不只是「附上來源」，而是用來源的力量推動論證。每一個引用必須回答讀者的一個隱含問題。

## 引用的三種功能

### 1. 事實錨定（Factual Anchor）

用於建立不可爭辯的基礎事實。

```
✓ Wikimedia Foundation FY2024-25 審計報告顯示年收入 2.086 億美元，
  其中 85% 以上來自個人捐助。
```

**規則**：
- 必須用 A 級來源
- 數字必須標明年份和來源
- 貨幣單位明確（USD/EUR/TWD）

### 2. 論證支撐（Argument Support）

用於為推論提供可信度。

```
✓ Elinor Ostrom 在 1990 年的研究指出，公共資源的永續管理需要
  明確的邊界規則、集體決策機制和衝突解決程序。這些條件同樣
  適用於數位公共財的治理。
```

**規則**：
- 先陳述論點，再引入來源（不要「根據 Ostrom……所以……」）
- 標明推理類型（這裡是類比 A：從自然公共財推到數位公共財）
- 如果是跨領域類比，必須說明類比的限制

### 3. 張力呈現（Tension Display）

用於展示觀點衝突，增加文章深度。

```
✓ Doctorow 認為平台墮落（enshittification）是商業模式的必然結果，
  但 Benkler 的 commons-based peer production 理論認為非市場協作
  可以繞過這個陷阱。兩者的分歧在於：非營利結構是否能真正隔絕
  市場壓力。
```

**規則**：
- 至少呈現兩方觀點
- 明確指出分歧所在
- 不需要在引用處就下結論

## 引用格式

### 正文中的引用

使用「來源描述 + 關鍵數據」模式，不使用學術腳註編號：

```
✓ 根據 ProPublica 公開的 990 表格，Signal Foundation 在 2024 財年
  的淨資產減少 470 萬美元，年度支出約 860 萬美元。

✗ Signal Foundation 的淨資產減少 470 萬美元[1]。
✗ 根據研究（Signal Foundation, 2024），淨資產減少。
```

### 來源附註區

文章末尾的來源清單，使用以下格式：

```markdown
## 參考來源

### 學術文獻
- Ostrom, Elinor (1990). *Governing the Commons*. Cambridge University Press.
- Scholz, Trebor (2016). "Platform Cooperativism." *Rosa Luxemburg Stiftung*.
  https://scholarworks.umb.edu/...

### 官方文件與財務資料
- Wikimedia Foundation. "FY2024-25 Audit Report." wikimediafoundation.org
- Signal Foundation. "Form 990 (FY2024)." via ProPublica Nonprofit Explorer.

### 案例與報導
- Mastodon gGmbH. "2024 Annual Report." blog.joinmastodon.org (查閱日期：2026-03-30)
- Doctorow, Cory (2023). "Enshittification." pluralistic.net
```

### URL 處理

- A/B 級來源：提供完整 URL 或 DOI
- 990 filing：標明 via ProPublica Nonprofit Explorer
- Blog/媒體：標明查閱日期（網頁可能消失）
- 學術論文：DOI 優先，arXiv ID 次之

## 引用密度

### 按段落類型

| 段落類型 | 引用密度 | 說明 |
|---------|---------|------|
| 事實陳述段 | 高（每 1-2 句一個來源） | 數字、年份、金額都需要來源 |
| 分析論證段 | 中（每段 1-2 個來源） | 來源支撐推論，不是每句都引 |
| 綜合評論段 | 低（段首或段尾一個來源） | 作者自己的論證，不需要句句引用 |
| 開頭/結尾 | 極低 | 可以不引用，這是作者的聲音 |

### 反模式

```
✗ 每句都引用（像論文，讀起來累）
✗ 整段沒有任何引用但充滿事實宣稱（讀起來不可信）
✗ 引用堆砌（「根據 A、B、C、D 的研究……」→ 讀者不知道誰說了什麼）
```

## 引用衝突處理

當兩個來源對同一事實有不同說法：

1. **數字差異**：優先採用 A 級來源；如果都是 A 級，取最新的
2. **觀點差異**：兩方都呈現，說明分歧
3. **方法論差異**：說明各自的測量方式，讓讀者判斷

```
✓ FediDB 統計 Mastodon 月活躍使用者約 100 萬人（2024 年中），
  但 Mastodon 官方 blog 引用的數字約 150 萬。差異可能來自
  對「活躍」的不同定義——FediDB 統計的是 30 天內有互動的帳號。
```

## 在 pipeline 中的位置

引用整合在三個階段被執行：

1. **evidence-mapped**：每個 claim 配對來源（evidence-map.md）
2. **drafted**：research draft 中嵌入引用（寫作代理負責）
3. **fact-checking**：critic 檢查引用是否正確使用、是否過度延伸（fact-check-report.md）

**交付物**：
- `final/*.md` 末尾的「參考來源」區
- Evidence map 中每個 claim 的來源欄位必須包含查閱日期
