# 形式語言輸出比較表

來源：`external/blog-pro/src/content/argmaps/2026-05-05-passport-rooted-paradox.yaml`

## 1. Argdown

檔案：`argument.argdown`

效果：

- 最能保留文章的公開論證地圖形狀。
- 支撐、反對、回應關係可以直接讀，不需要先理解整個內部 YAML schema。
- 適合公開發表、外部研究者 review、後續匯出 SVG 或嵌入網頁。

代價：

- Argdown 本身不做推理。它顯示論證結構，但不會自動判斷反論之後哪個結論勝出。
- 公式比較像註記，不是 machine-checked proposition。

最適合角色：

公開交換格式與視覺化層。

## 2. DeLP-Style Rules

目前檔案：無。DeLP 先停在未來研究室工具選項。

效果：

- 最適合表示「通常成立，但可被反例擊敗」的命題。
- 它能捕捉 civic proof 的典型結構：
  - 護照根通常有用，因為覆蓋率高；
  - 但當 issuer 與 adversary 重疊時，護照根會變得不足；
  - zkPassport 解決 privacy 問題，但不解決 issuer-side revocation；
  - ICAO PKI 的 robust 可以防偽，但不能防止合法發證者武器化。

代價：

- 需要先選定 runner / 實際 dialect，才算可執行。
- predicate 命名會變成自己的 ontology 工作。
- 公開讀者需要額外解釋層，不如 Argdown 直覺。

最適合角色：

研究室內部的反論、例外、情境推理壓力測試。

## 3. Lean 4

目前檔案：無。Lean 先停在未來 lemma library 選項。

效果：

- 最適合抽出最小、可重複使用的 theorem skeleton。
- 這份樣本證明：接受 SRP axiom 之後，只要 issuer-adversary overlap 成立，single-passport-root validity 就失敗。
- 也示範 R2 / R3 / R4 在 trust 與 non-compromise 條件被提供時，可以作為 `MultiRootedAvailable` 的 witness。

代價：

- Lean 不能自行證明經驗前提。Turkey 2016、Belarus 2023、Russia 2022 是否屬於 issuer-adversary case，仍要靠文章證據與 fact-check。
- 把整篇文章 Lean 化會太慢，也可能製造假的精確感。

最適合角色：

少量、重複出現的 civic-proof 邏輯骨架 lemma library。

## 決策

`argmap.yaml` 繼續作為 canonical internal data。

目前只先採用 Argdown export，作為公開發表或外部協作的交換格式。

DeLP 先停在 prototype，不接進 pipeline。之後只有在「反論／例外推理」成為實際瓶頸時再重開。

Lean 先停在 prototype，不做整篇文章形式化。之後只考慮少量反覆出現的形式骨架，例如：

- `issuer_adversary + sovereign_root -> not trust_satisfied`
- `T valid iff T1 and T2 and T3`
- `multi_root_available iff exists noncompromised accepted root`
- `deployment_valid iff all boundary conditions hold`
