# California Career Passport 四家最後廠商分析

日期 2026-06-19

GitHub 版本只追蹤分析報告。原始投標 PDF 與抽取文字保留在本機 jobs 目錄與 iCloud 副本，避免把投標文件推上 remote。

本報告依使用者提供的最後廠商名單分析 Auth9 / Certree、Infosys、SpruceID、Territorium。採購狀態上，本報告不把四者寫成已決標得標者。外部公開資料顯示 California Community Colleges 的 Career Passport 最終採購結果預期在 2026 年秋季出爐，RFP #1980 的定位是建立由使用者控制、可管理與分享可驗證學業紀錄與技能的 Career Passport 平台。

## 一頁結論

若把 Career Passport 的核心目標拆成四件事，判斷會更清楚。第一是可驗證憑證與開放標準，第二是一般加州居民真的能用，第三是雇主與學校真的願意驗，第四是長期不能被單一廠商鎖住。

我的排序如下。

1. SpruceID 最適合做政府級、標準優先、隱私與開放錢包的主方案。它的最大優勢是 California DMV mDL 實績、W3C VC / Open Badges / OID4VCI / OID4VP / ISO 18013-5 等標準能力，以及 no phone home 與選擇性揭露的設計語言。但它對教育履歷、技能語義、雇主端採用的資料鏈，需要在 pilot 中被硬測。

2. Auth9 / Certree 最適合做能最快接上真實驗證者與弱裝置族群的務實方案。它有雇用與收入驗證、學籍與 transcript 相關的真實場景，也明顯重視瀏覽器、PDF、API 與非專家驗證者。不過它的雲端 vault 與後端參與模型需要更嚴格的隱私、可攜、離場與 metadata leakage 檢查。

3. Territorium 最適合做教育到就業的技能語義與 learner record 平台。它強在 CLR、Open Badges、技能映射、雙語 learner experience、教育機構部署。但若要承擔加州公共錢包的信任層，它需要證明 wallet、DID、status、recovery、export、unlinkability 的硬標準，不只證明教育產品好用。

4. Infosys 最像大型系統整合商方案，優點是規模、交付能力、open-source Inji / MOSIP 路線，以及很明確的非託管與 no backend at presentation 主張。主要風險是投標文件自己承認列出的三個客戶參考並非 W3C VC、learner-controlled wallet 或 OID4VCI / OID4VP / VC-API 實作，且 pilot 範圍只含 Inji Mobile，不含 Inji Verify 與 Inji Web，iOS BLE 也被放到後續階段。

## RFP 判讀基準

RFP 對 Career Passport 的定義很明確。它要的是安全、由學習者控制的工具，能保存與展示可驗證的學業紀錄、執照、業界證照、badges、軍職經驗，讓雇主能理解一個人知道什麼、會做什麼。來源見 [Career Passport RFP Scope](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/Career_Passport_RFP_posted_4-15-26.txt:342)。

RFP 的信任模型也不是單純履歷網站。它要求 W3C Verifiable Credentials 可被即時驗證，理想上不需要再去找發行者或第三方確認，未來也要能嵌入 ATS、HR 與招募流程。來源見 [RFP Employer Trust](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/Career_Passport_RFP_posted_4-15-26.txt:387)。

RFP 同時要求隱私、holder control、有限設備族群、共享設備、間歇連線、無障礙與語言近用。特別關鍵的是，憑證屬於加州居民，分享行為不應在本人不知情或不能控制的情況下留下可被追蹤的揭露紀錄。來源見 [RFP Privacy And Access](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/Career_Passport_RFP_posted_4-15-26.txt:406)。

因此，本報告採用的評估軸線如下。

- 標準與互通性，包含 W3C VC Data Model 2.0、Open Badges v3.0、DIDs、OID4VCI、OID4VP、status / revocation、export 與 vendor exit
- 持有人控制與隱私，包含私鑰控制、選擇性揭露、unlinkability、metadata leakage、presentation 時是否呼叫 issuer 或廠商後端
- 真實採用與整合，包含 eTranscript California、社區大學、DMV mDL、雇主、licensing board、ATS / HR、既有 verifier 工作流程
- 公平與近用，包含手機與非手機、瀏覽器、共享設備、低頻寬、語言、無障礙、recovery 與失去裝置後的處理
- Pilot 可驗證性，包含 30 天 pre-pilot integration check、三種 credential type、兩個 issuer、真實 cohort、Tier 1 interoperability hard pass / fail、usability threshold

## 比較表

| 廠商 | 最強證據 | 主要缺口 | 適合角色 | Pilot 應優先測什麼 |
|---|---|---|---|---|
| SpruceID | California DMV mDL、政府級 wallet、開放標準與隱私設計 | 教育技能語義、雇主端採用、recovery 與 eTranscript / ATS 整合需在本案證明 | 公共錢包與信任層主方案 | no phone home、OID4VP、選擇性揭露、mDL / 學籍 / badge 共存、低資源使用者 |
| Auth9 / Certree | 真實雇用與收入驗證、學籍與 transcript 場景、瀏覽器與 verifier 友善 | 雲端 vault 與後端參與需檢查 metadata leakage、vendor exit、unlinkability | 快速啟動 verifier network 與非專家驗證工作流 | 無手機使用、PDF / link / API 驗證、device loss、完整匯出到第三方 wallet |
| Territorium | CLR / Open Badges 認證、教育到就業技能語義、雙語 learner experience | 更像 LER / skills platform，需要證明政府級 wallet 信任邊界 | 技能語義層、learner record 與 pathway 體驗 | 技能映射透明度、非專有 taxonomy、issuer / verifier 跨平台驗證、AI 建議的可解釋性 |
| Infosys | 大型交付能力、open-source Inji / MOSIP、明確非託管與 presentation 不呼叫後端 | 客戶參考不是 W3C wallet 實作，pilot 只含 Inji Mobile，不含 verifier / web wallet 完整堆疊 | 若州方要自有程式碼與大型 SI 治理，可作工程交付方案 | Phase 2 範圍落差、iOS BLE、Inji Verify / Web 排除影響、真實 issuer / verifier 串接 |

## SpruceID

SpruceID 的投標定位最貼近「政府級、標準優先、隱私優先」的公共錢包。投標文件表示其核心專長包含 W3C Verifiable Credentials、Open Badges v3、DIDs、ISO 18013-5 mDL、SD-JWT、OID4VCI、OID4VP 與 practical interoperability。來源見 [SpruceID Standards](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/17._SpruceID.txt:95)。

最大外部佐證是 California DMV mDL。SpruceID 投標文件主張自己是 CA DMV mDL 的 lead implementation partner，且處理超過 380 萬 credentials。來源見 [SpruceID CA DMV Claim](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/17._SpruceID.txt:102)。外部資料中，SpruceID 也公開說明與 CA DMV 合作 mDL，並強調 open source、standards、selective disclosure 與避免 issuer phone home 的設計。來源見 [SpruceID CA DMV mDL](https://blog.spruceid.com/spruceid-partners-with-ca-dmv-on-mdl/)。

對 Career Passport 而言，SpruceID 的好處是可信任基礎建設已接近加州政府語境。CA DMV 官方頁面說明 mDL 仍在 pilot，使用者仍需要實體駕照或 ID，但也宣稱使用資料不會在未同意下離開設備，且 California Community Colleges 是可使用場景之一。來源見 [CA DMV Wallet](https://www.dmv.ca.gov/portal/ca-dmv-wallet/)。

SpruceID 的架構承諾也強。投標文件說 holder control、keys on device、SpruceID 不接觸 holder private keys、沒有 centralized credential store，並討論 unlinkability、recovery、reissuance、encrypted backup 或 user-managed material。來源見 [SpruceID Holder Control](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/17._SpruceID.txt:420)。它也明確描述 OID4VCI / OID4VP 的 issuance / presentation 與 QR / web redirect flows。來源見 [SpruceID OID4VCI OID4VP](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/17._SpruceID.txt:470)。

主要風險在於 Career Passport 不只是一個身分錢包。它需要把 academic record、Open Badges、skills metadata、credit for prior learning、employer verification 與 ATS / HR workflow 串起來。SpruceID 文件把 eTranscript、CA mDL、ATS integrations、localization、backup / recovery、skills navigation 列為後續項目或非 Phase 2 依賴項，這代表 pilot 必須逼近真實整合，而不能只展示 wallet mechanics。來源見 [SpruceID Future Items](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/17._SpruceID.txt:1193)。

外部風險則是 mDL 類公共錢包本身帶來的治理爭議。EFF 對 California DMV mDL 的分析提醒，數位 ID 需要 holder control、privacy、transparency、optionality、紙本或塑膠 ID 替代選項與 selective disclosure。來源見 [EFF California mDL Analysis](https://www.eff.org/deeplinks/2024/03/decoding-california-dmvs-mobile-drivers-license)。這些不是 SpruceID 的單點缺陷，但會變成 Career Passport 的治理要求。

判斷上，SpruceID 是最有資格做「公共信任層」的候選者。若州方最重視開放標準、政府級 wallet、隱私、與長期跨機關 credential infrastructure，SpruceID 是最強方案。但合約與 pilot 要把教育語義、雇主端採用、recovery、低資源使用者、以及 vendor exit 寫成硬門檻。

## Auth9 / Certree

Auth9 / Certree 的投標不像純 wallet 廠商，而是從「真實世界如何驗文件」出發。投標文件說 Certree 自 2019 年 production，服務 employment、income、academic records，並且早期部署就針對 gig、hourly、nontraditional workers 與 voluntary ecosystems。來源見 [Auth9 Background](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/4._Auth9_Certree.txt:83)。

它的關鍵優勢是 verifier adoption。投標文件說 Certree 的 verifier ecosystem 已包含 employers、background screeners、licensing boards 與 institutions。來源見 [Certree Verifier Ecosystem](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/4._Auth9_Certree.txt:50)。外部資料也能看到 TriNet 把 employment / income verification 導向 Certree，員工設帳號後，verifier 直接透過 Certree request documents，員工再分享。來源見 [TriNet Certree Support](https://www.trinet.com/support)。Impellam 的 Certree FAQ 也描述員工能控制分享 proof of employment / income，文件連結可驗證且文件不能被任意修改。來源見 [Impellam Certree FAQ](https://ess.impellam.com/customizations/Certree%20FAQ%2010-2020.pdf)。

對 Career Passport 的公平近用來說，Auth9 / Certree 的 web vault 是加分。投標文件主張它是 browser / any device 可用的 web wallet / vault，credential 可在 issuer 之外保存，並支援 secure links、PDF with embedded verification、API、SIS 與 native W3C exchange。來源見 [Certree Web Vault](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/4._Auth9_Certree.txt:266)。

它也有與加州社區大學、eTranscript California 和 CACCRAO 周邊相近的資料。投標文件說 2025 年有由 CCCCO、CCC Foundation 與 CACCRAO board 合作的 pilot，並被選為 eTranscript CA modernization pilot vendor 之一，也提到多個 California community college districts live 或 pending go-live。來源見 [Certree CA Pilot](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/4._Auth9_Certree.txt:443)。

最大風險是它的隱私與架構邊界不像 SpruceID 那麼乾淨。投標文件描述 dual-key cloud vault，說 Certree 不能在沒有 holder active participation 的情況下存取 holder credentials。來源見 [Certree Dual Key Vault](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/4._Auth9_Certree.txt:306)。但同一份文件也說在 display / presentation 時可能會接觸 Certree backend、issuer DID resolution endpoints 與 status list endpoints。來源見 [Certree Network Contacts](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/4._Auth9_Certree.txt:1668)。

這不代表 Certree 不合格，但它把 pilot 重點推向可觀測隱私與可攜性。州方應要求完整網路流量測試、metadata retention policy、log minimization、verifier correlation 風險分析、第三方 wallet 匯出測試、issuer 退場測試、與 account recovery 安全審查。

判斷上，Auth9 / Certree 是最務實的 adoption play。若 Career Passport 的第一年目標是讓雇主、學校、licensing board 真的能收文件、驗文件、且不需要先懂 W3C，Certree 很有競爭力。但如果把它放在州級公共 wallet 的核心位置，合約必須把資料可攜、後端依賴、去識別與 unlinkability 寫得比投標文字更硬。

## Territorium

Territorium 的核心優勢不是加密錢包本身，而是教育到就業的 learner record 與技能語義層。投標文件說它服務 1,200 萬 learners、300 多間美國機構，SaberesMx 超過 100 萬 learners，並強調 bilingual、standards-aligned、learner-controlled wallet。來源見 [Territorium Scale](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/18._Territorium.txt:83)。

它的產品 LifeJourney 被描述為 learner-controlled wallet and skills infrastructure，支援 full credential lifecycle、W3C VC、Open Badges 3.0 與 CLR 2.0-style records。來源見 [Territorium LifeJourney](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/18._Territorium.txt:171)。外部 1EdTech certification page 也列出 Territorium 的 active certifications，包含 CLR 2.0 與 Open Badges v3.0 issuer。來源見 [1EdTech Territorium Certification](https://site.imsglobal.org/certifications/territorium/territorium)。

Career Passport 的特殊難題是「技能」不能只是 badge 名稱。Territorium 在這點上最有針對性。投標文件說 LifeJourney 是 education-to-workforce data infrastructure，skills intelligence layer 能把 metadata 映射到 O*NET、CTDL、Open Skills 與 California taxonomies，並主張 technical interoperability 以外還需要 semantic interoperability。來源見 [Territorium Skills Intelligence](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/18._Territorium.txt:408)。

外部產品頁也支撐這個定位。Territorium 的 CLR 頁面把產品描述為 verified record of skills and competencies，並說 AI 可將校內外學習映射到 granular competencies，功能包含 prior learning assessment、achievements、wallet 與 employability pathways。來源見 [Territorium CLR](https://territorium.com/product/comprehensive-learner-record/)。Territorium 的 wallet support 頁也說明 Open Badges v3 與 CLR formats、import、sharing 與 employer sharing。來源見 [Territorium Wallet Support](https://success.territorium.com/how-to)。

主要風險是 vendor lock-in 與 AI / skills mapping 的治理。若 Career Passport 的價值被 Territorium 的技能圖譜、AI coaching 或 employability pathway 綁住，州方需要確認 taxonomy mapping 可審計、可匯出、可重跑、可被第三方替換。RFP 的目標是可攜憑證，不應變成只能在同一平台裡理解的 profile。

另一個風險是 wallet 信任邊界。投標文件說它支援 did:web、did:key、did:jwk，offline display after caching，可能接觸 issuer DID / status / context endpoints，recovery 透過 encrypted cloud-backed credentials 與 wrapped keys，Territorium 不看 plaintext key、password 或 secret。來源見 [Territorium DID Recovery](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/18._Territorium.txt:2767)。這些說法合理，但 pilot 需要像審查公共錢包一樣實測，而不能只接受教育平台型產品 demo。

判斷上，Territorium 是最好的 skills / CLR / learner pathway 方案。若 Career Passport 的決策重心是「讓學習紀錄變成可被勞動市場理解的技能語言」，Territorium 很強。但若決策重心是公共錢包、隱私與跨機關 trust fabric，它應被要求補強硬標準、匯出與去平台化證明。

## Infosys

Infosys 的提案走大型系統整合與 open-source public infrastructure 路線。投標文件說其能力包含 digital identity、trust、Verifiable Credentials、Hyperledger Indy / ACA-Py、open platforms、education / workforce、accessibility、cybersecurity、privacy 與 resilience。來源見 [Infosys Background](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/02-6.2-Company-Background.txt:41)。

外部資料確實能支撐 Infosys 有 VC 相關經驗。Infosys 官方 case study 說它使用 Hyperledger Indy 與 ACA-Py 建立 credential verification，並在 30 萬多名員工中推廣。來源見 [Infosys Hyperledger Case Study](https://www.infosys.com/services/blockchain/case-studies/verification-platform.html)。Linux Foundation Decentralized Trust 的文章也描述 Infosys Lex badges 需要 VCs、public verification portal、wallet 與 SSI framework。來源見 [LF Decentralized Trust Infosys](https://www.lfdecentralizedtrust.org/blog/infosys-boosts-efficiency-security-and-privacy-of-credential-verification-with-hyperledger-indy-and-aca-py)。

Infosys 投標的技術核心是 MOSIP / Inji。Inji 文件把 Inji Mobile 描述為 open-source mobile wallet，支援 W3C VC、OID4VCI、OID4VP、ISO 18013-5、SD-JWT，並支援 online / offline。來源見 [Inji Mobile Docs](https://docs.inji.io/inji-wallet/inji-mobile/overview)。MOSIP 官方也把 Inji 定位為 issuance、storage、verification 的 verifiable credential stack。來源見 [MOSIP Inji](https://www.mosip.io/inji)。

Infosys 的優點是投標文件把隱私承諾寫得很明確。pilot readiness package 說 credential content 與 signing keys 不進 Infosys 後端，presentation 只接觸 selected verifier，不接觸 issuer、Infosys 或第三方。來源見 [Infosys Pilot Privacy](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/06-Section_Two_-_Pilot_Readiness_Package.txt:57)。addendum 也說 presentation 時沒有外部 endpoint，status list 與 metadata refresh 與 presentation 解耦。來源見 [Infosys No Endpoint At Presentation](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/07-Addendum_1_Clarification_Responses.txt:18)。

但最大紅旗也在投標文件本身。Infosys 的 Form 4 客戶參考明確說，列出的 engagements 都不是 W3C Verifiable Credentials、learner-controlled digital wallets、OID4VCI、OID4VP 或 VC-API 實作。它們只能證明 large-scale higher-education / K-12 platform delivery、cloud / identity modernization、SIS operations。來源見 [Infosys Reference Limitation](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/04-Form_4_Client_References.txt:50)。

第二個紅旗是 pilot scope。Infosys 明確說本次 engagement 的範圍是 Inji Mobile wallet only，Inji Verify 與 Inji Web 不在範圍內。來源見 [Infosys Pilot Scope](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/06-Section_Two_-_Pilot_Readiness_Package.txt:17)。同一份文件也說 Android BLE 在 pilot 內，iOS BLE 放在 Phase 3 roadmap，native ISO 18013-5 device retrieval 不在 pilot 承諾。來源見 [Infosys BLE Scope](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/extracted/06-Section_Two_-_Pilot_Readiness_Package.txt:27)。

Infosys 還有一個值得注意的外部強項。Infosys Springboard Livelihood Program 公開資料說目標到 2030 年創造 50 萬個工作機會，FY25 已安置 8 萬人，並與 20 個夥伴合作。來源見 [Infosys Springboard Livelihood Program](https://www.infosys.com/newsroom/press-releases/2025/launches-springboard-livelihood-program.html)。這對 Career Passport 的 workforce adoption 有敘事價值，但它不是 Career Passport 所需 credential wallet production reference 的直接替代。

判斷上，Infosys 是工程交付與州方自有 public infrastructure 的候選，而不是最成熟的 Career Passport domain vendor。若 California 想買的是「由州方持有、open-source、可被大型 SI 交付的基礎建設」，Infosys 有吸引力。但若採購要立即降低 Phase 2 的 credential wallet、verifier、education LER 風險，Infosys 需要補上大量直接實作證明。

## 建議的 finalist 問題清單

### 給 SpruceID

1. 請展示同一個 wallet 中同時持有 CA DMV mDL、academic credential、Open Badges v3、employment credential 的 issuance、presentation、recovery 與 export。
2. 請證明 presentation 時不會讓 issuer、SpruceID 或第三方得到 verifier correlation signal。
3. 請說明 eTranscript California、MAP CPL、OpenCCC / CCCApply / CCCID、ATS / HR 系統如何進入 Phase 2 可測範圍。
4. 請提出非智慧型手機、共享設備與低頻寬使用者的等價流程。
5. 請交付第三方 wallet 匯出與 vendor exit 的可驗證測試。

### 給 Auth9 / Certree

1. 請以封包與 log 層級展示 display / presentation 時 Certree backend、issuer DID endpoints、status list endpoints 各自接收到什麼 metadata。
2. 請證明 holder 可把 credential 完整匯出到第三方 W3C wallet，且 verifier 不需繼續依賴 Certree。
3. 請測試 issuer 退場、college SIS 斷線、holder 失去裝置、帳號被鎖時的 recovery 與資料可攜。
4. 請提供 verifier correlation、link sharing、PDF embedded verification 的隱私風險模型。
5. 請展示不熟悉 W3C 的 employer 或 licensing board 如何在 3 分鐘內完成可信驗證。

### 給 Territorium

1. 請公開 skills intelligence layer 如何把 metadata 映射到 O*NET、CTDL、Open Skills 與 California taxonomies。
2. 請證明 skills mapping 與 AI coaching 的結果可匯出、可審計、可用第三方工具重跑。
3. 請展示非 Territorium issuer 與非 Territorium verifier 的跨平台 Open Badges v3 / CLR / W3C VC 驗證。
4. 請說明 offline display、status checks、DID resolution 與 context endpoints 的 metadata leakage 控制。
5. 請測試雙語、無障礙、shared device、失去裝置後復原，以及低數位素養使用者的完整 journey。

### 給 Infosys

1. 請說明 Form 4 客戶參考不是 W3C VC / wallet / OID4VCI / OID4VP 實作時，Phase 2 如何降低直接實作風險。
2. 請把 Inji Verify 與 Inji Web 排除在 pilot 範圍外的影響寫成明確風險，並提出替代驗證流程。
3. 請展示 iOS BLE 未進 Phase 2 時，iPhone 使用者如何完成 offline 或 local-channel presentation。
4. 請提供 MOSIP / Inji upstream roadmap 與 California 客製碼之間的維護、資安修補、授權與 ownership 邊界。
5. 請用真實 issuer、真實 verifier、真實 cohort 證明，不只展示 mobile wallet 本身。

## 建議的 pilot 壓力測試

1. Three credential types, two issuers, one third-party verifier。至少包含 transcript / academic record、Open Badges v3 或 CLR、employment 或 license credential。
2. Presentation privacy test。用封包紀錄與服務端 log 證明 issuer、vendor、status endpoint、DID endpoint、analytics endpoint 不會取得 holder-verifier correlation。
3. No-smartphone route。使用 shared device、public computer、low-end Android、斷續網路與英西雙語流程，測量成功率與時間。
4. Device loss and recovery。發證後刪除 app、換手機、遺失 email access、issuer 暫時不可用，測試 recovery 與 reissue。
5. Verifier non-expert test。讓不懂 W3C 的 employer / licensing board / admissions office 在無工程協助下完成驗證。
6. Vendor exit。把同一批 credentials 匯出到第三方 wallet，並讓第三方 verifier 成功驗證。
7. Sparse metadata test。用欄位不完整、技能語義稀疏、issuer metadata 老舊的 credential，測試平台是否仍能透明處理未知與不確定。

## 採購建議

若只選一個主承包商，SpruceID 是風險結構最乾淨的選擇，前提是合約把教育與雇主整合列成硬交付。它最符合公共錢包、開放標準、隱私與 California DMV 生態延伸。

若採雙層或多廠商架構，較合理的組合是 SpruceID 做 wallet / trust layer，Territorium 做 skills / CLR / learner pathway layer，Auth9 / Certree 做 verifier adoption 與 transcript / employment verification bridge。這種組合的治理成本較高，但能避免單一廠商同時掌控錢包、技能語義、verifier network 與 pathway intelligence。

若採單一 SI 交付並要求州方持有源碼，Infosys 值得列入，但它應被要求先通過更嚴格的 Phase 2 scope test。尤其是 client references 不直接對應 W3C wallet production、pilot 只含 Inji Mobile、iOS BLE 與 verifier / web wallet 不在即期範圍內，這些都應變成明確的合約 gate。

Auth9 / Certree 不應只被視為傳統 verification vendor。它的實務採用與 verifier-friendly 設計很可能是 Career Passport 能否被雇主與機構接受的關鍵。不過它若成為核心 wallet，需要比其他廠商更嚴格接受隱私、metadata、出口與 cloud-vault dependency 審查。

Territorium 不應只被看成普通教育平台。它掌握 Career Passport 最難的另一半，也就是把學習記錄轉成勞動市場可理解的 skills language。但它的 AI / taxonomy / platform intelligence 應維持可審計、可替換、可匯出。

## 資料來源

### 本地投標與 RFP 文件

- [Career Passport RFP posted 4-15-26](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/source-materials/baseline/Career%20Passport%20RFP%20posted%204-15-26.pdf)
- [Auth9 Certree proposal](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/source-materials/vendors/4.%20Auth9%20Certree.pdf)
- [SpruceID proposal](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/source-materials/vendors/17.%20SpruceID.pdf)
- [Territorium proposal](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/source-materials/vendors/18.%20Territorium.pdf)
- [Infosys submission folder](/Users/mashbean/Developer/repos/research-publishing-pipeline/jobs/2026-06-19-career-passport-finalists-analysis/source-materials/vendors/9.%20Infosys%20Submission)

### 外部資料

- [CCCCO California Career Passport Timeline Report](https://www.cccco.edu/-/media/CCCCO-Website/docs/report/california-career-passport-timeline-report-a11y.pdf)
- [HigherGov RFP #1980 listing](https://www.highergov.com/sl/contract-opportunity/ca-develop-a-new-california-career-passport-66008289/)
- [TriNet Certree support](https://www.trinet.com/support)
- [Impellam Certree FAQ](https://ess.impellam.com/customizations/Certree%20FAQ%2010-2020.pdf)
- [SpruceID CA DMV mDL partnership](https://blog.spruceid.com/spruceid-partners-with-ca-dmv-on-mdl/)
- [CA DMV Wallet](https://www.dmv.ca.gov/portal/ca-dmv-wallet/)
- [EFF California DMV mDL analysis](https://www.eff.org/deeplinks/2024/03/decoding-california-dmvs-mobile-drivers-license)
- [Territorium CLR](https://territorium.com/product/comprehensive-learner-record/)
- [1EdTech Territorium certification](https://site.imsglobal.org/certifications/territorium/territorium)
- [Territorium wallet support](https://success.territorium.com/how-to)
- [Infosys Hyperledger credential verification case study](https://www.infosys.com/services/blockchain/case-studies/verification-platform.html)
- [LF Decentralized Trust on Infosys Hyperledger Indy and ACA-Py](https://www.lfdecentralizedtrust.org/blog/infosys-boosts-efficiency-security-and-privacy-of-credential-verification-with-hyperledger-indy-and-aca-py)
- [Inji Mobile documentation](https://docs.inji.io/inji-wallet/inji-mobile/overview)
- [MOSIP Inji](https://www.mosip.io/inji)
- [Infosys Springboard Livelihood Program](https://www.infosys.com/newsroom/press-releases/2025/launches-springboard-livelihood-program.html)
