# 來源蒐集策略

## 目標

系統性蒐集學術文獻與真實世界案例，避免倖存者偏差、來源同質化、和 C 級來源獨撐核心論點。

## 來源分類

### 學術來源（A 級）

| 類型 | 搜尋管道 | 信號 |
|------|---------|------|
| 期刊論文 | Google Scholar, SSRN, arXiv, JSTOR | peer-reviewed, DOI |
| 學位論文 | ProQuest, 國家圖書館 | 指導教授、口試委員 |
| 學術專書 | Google Books, WorldCat | 大學出版社、學術出版社 |
| 會議論文 | ACM DL, IEEE Xplore, SSRN | 錄取率、同儕審查 |

**搜尋策略**：
1. 從核心問題抽出 2-3 個學術關鍵詞
2. Google Scholar 搜尋，按引用數排序
3. 找到 1-2 篇高引用 survey/review paper
4. 從 survey 的參考文獻往下挖（snowballing）
5. 檢查最近 2 年是否有更新的研究

### 政策與官方文件（A 級）

| 類型 | 搜尋管道 | 信號 |
|------|---------|------|
| 法規原文 | 國家法規資料庫, EUR-Lex | 正式公報 |
| 政府報告 | OECD iLibrary, 審計報告 | 政府機關署名 |
| 國際組織 | UN, World Bank, ITU | 機構發佈 |
| 審計/監察 | GAO, NAO, ANAO, 監察院 | 獨立審計 |

### 真實世界案例（B/C 級，但不可或缺）

| 類型 | 搜尋管道 | 注意事項 |
|------|---------|---------|
| 公司財報/990 | SEC EDGAR, ProPublica Nonprofit Explorer | A 級數據，直接引用 |
| 年度報告 | 組織官網 | B 級，有自我宣傳風險 |
| 創辦人/團隊 blog | Medium, 個人網站 | C 級，一手資料但有偏差 |
| 媒體報導 | 各大媒體 | C 級，事實可引用但分析不可獨撐 |
| 社群討論 | HN, Reddit, Fediverse | C 級，作為氣氛佐證，不作為事實來源 |

## 四象限蒐集法

每篇文章的來源必須涵蓋四個象限：

```
              學術理論          真實案例
            ┌─────────────┬─────────────┐
  成功/     │ 學術框架     │ 成功案例     │
  正面      │ (Ostrom,    │ (Wikipedia, │
            │  Benkler)   │  Stocksy)   │
            ├─────────────┼─────────────┤
  失敗/     │ 批判理論     │ 失敗案例     │
  負面      │ (Doctorow,  │ (Cohost,    │
            │  Zuboff)    │  Ello)      │
            └─────────────┴─────────────┘
```

**規則**：
- 每個象限至少 2 個來源
- 成功案例數 ≤ 失敗案例數 + 1（避免倖存者偏差）
- 每個成功案例必須至少一個相同領域的失敗對照

## 案例蒐集 SOP

### Step 1: 識別案例範疇

從核心問題推出需要哪些類型的案例：
```
核心問題: 非營利社群平台能永續嗎？
→ 需要: 非營利平台（成功 + 失敗）
→ 需要: 合作社平台（成功 + 失敗）
→ 需要: 混合模式（營利子公司 + 非營利母體）
→ 需要: 不同規模（全球 vs 區域 vs 社群）
→ 需要: 不同地理區域（歐美 + 亞洲）
```

### Step 2: 每類至少一正一反

| 類別 | 成功 | 失敗 | 對照意義 |
|------|------|------|---------|
| 非營利平台 | Wikipedia | Diaspora* | 品牌 + 規模 vs 無 |
| 聯邦式 | Mastodon (存活) | App.net | 開放協議 vs 封閉 |
| 合作社 | Stocksy | Ello | 交易型 vs 社群型 |
| 混合模式 | Mozilla | — | 營利依賴風險 |

### Step 3: 為每個案例蒐集結構化數據

```yaml
case:
  name: "Mastodon"
  type: "非營利聯邦式社群平台"
  founded: 2016
  status: "active"  # active / struggling / failed / acquired
  legal_structure: "gGmbH (德國非營利有限公司)"
  revenue_model: ["Patreon 捐助", "企業贊助"]
  annual_revenue: "~€700K (2023)"
  users: "~1M MAU (FediDB, 2024)"
  governance: "BDFL → 有限制度化"
  key_risk: "創辦人依賴、Threads 競爭"
  source_grade: "B (官方 blog, 非獨立審計)"
  failure_mode: null  # 或 "資金耗盡" / "治理崩潰" / "使用者流失"
```

### Step 4: 交叉驗證

- 同一個案例的不同面向，至少用兩個獨立來源
- 財務數據必須來自 A 級來源（990、審計報告、年報）
- 使用者數據標註來源和查詢日期

## 搜尋 prompt 模板

### 學術文獻搜尋

```
Search: Google Scholar
Query: "platform cooperativism" OR "nonprofit platform" sustainability governance
Filter: Since 2020, sort by relevance
Goal: Find 2-3 survey papers, then snowball references
```

### 真實案例搜尋

```
Search: Web
Query: "nonprofit social media platform" failed OR shutdown OR closed
Goal: Find failure cases to balance success narrative
```

```
Search: ProPublica Nonprofit Explorer
Query: [organization name]
Goal: 990 filing for financial data
```

### 區域案例搜尋

```
Search: Web (限定語言)
Query: 非營利 社群平台 台灣 OR 日本 OR 韓國
Goal: 找到歐美以外的案例
```

## 在 pipeline 中的位置

來源蒐集發生在兩個時間點：

1. **intake → scoped**：使用者提供已知來源 + pipeline 自動識別需要的案例象限
2. **scoped → researching**：Deep Research prompt 包含四象限蒐集指令

**交付物**：
- `notes/source-registry.yaml` — 結構化來源清冊
- `notes/case-comparison.md` — 案例正反對照表
