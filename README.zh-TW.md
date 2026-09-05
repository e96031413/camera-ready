<p align="center">
  <a href="README.md">English</a> · <strong>繁體中文</strong> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="assets/images/hero_banner.jpg" alt="CameraReady Banner" width="100%" />
</p>

<h1 align="center">CameraReady</h1>

<p align="center">
  <strong>從選題構想到可直接投稿 — 每一關都有嚴格閘門把守。</strong><br>
  <em>專為 AI Agent 設計的跨學科自主學術論文研究與撰寫管線，以無可妥協的學術嚴謹度打造。</em>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-blue.svg">
  <img alt="Platforms" src="https://img.shields.io/badge/平台-Windows%20%7C%20macOS%20%7C%20Linux-brightgreen.svg">
  <img alt="Disciplines" src="https://img.shields.io/badge/學科-8%20大領域支援-purple.svg">
  <img alt="Citation Styles" src="https://img.shields.io/badge/引用格式-APA%20%7C%20MLA%20%7C%20Chicago%20%7C%20Vancouver%20%7C%20IEEE-orange.svg">
  <img alt="Zero Hallucination" src="https://img.shields.io/badge/引用驗證-零幻覺保證-success.svg">
  <img alt="Agent Skills" src="https://img.shields.io/badge/Agent%20Skills-標準規範相容-blueviolet.svg">
</p>

<p align="center">
  <a href="#五分鐘快速上手"><strong>⚡ 5 分鐘快速上手</strong></a> ·
  <a href="examples/minimal-review-paper/main.pdf"><strong>📄 範例編譯論文 (PDF)</strong></a> ·
  <a href="docs/DEMO.md"><strong>🎥 終端實錄 Demo</strong></a> ·
  <a href="docs/QUICKSTART.md"><strong>🚀 快速入門指南</strong></a> ·
  <a href="docs/GUARANTEES.md"><strong>🛡️ 嚴謹保證範圍</strong></a> ·
  <a href="SKILL.md"><strong>⚙️ 工作流規範</strong></a>
</p>

> [!IMPORTANT]
> **核心保證：** 每一條引用皆從權威資料庫（DBLP、CrossRef、arXiv API）即時抓取；每一個論斷皆能回溯至具體登記的證據；在研究計畫未獲得具名審核通過前，禁止撰寫任何內文正文。

---

## 問題在哪裡：傳統 AI 寫論文為何必然被拒稿（Desk Reject）

讓現有最強的前沿大語言模型（LLM）寫一篇論文，它能在幾秒鐘內產出通順優美的數千字文章。然而，在華麗的文字底下，它通常會伴隨以下致命硬傷：
- **偽造不存在的文獻**：憑記憶編造格式完美的 BibTeX，內含看似合理卻查無此文的論文標題與假 DOI。
- **過度誇大推論結論**：將文獻中有限的實驗觀察，過度泛化成決定性的普遍結論。
- **漠視會議格式與頁數硬規則**：要求 8 頁卻交出 11 頁的稿件，或在嚴格雙盲（Double-Blind）審查的 PDF 中洩漏作者姓名、信箱與程式庫連結。
- **漏失特定領域的規範聲明**：在臨床醫學論文中漏填臨床試驗登記號（CONSORT），在質性研究中宣稱「達到飽和」卻未交代理論飽和的判定依據（COREQ）。

這些從來就不是「文字潤飾」的問題，而是**「工程與研究流程」的架構性缺陷**。在頂級學術審查中，這類瑕疵會在第一時間導致初審退稿（Desk Reject）。

```text
傳統 AI 生成模式：
  [單純下 Prompt] ───────────► [憑空編造的初稿] ──► 初審退稿 (Desk Reject)

CameraReady 分閘門管線：
  [領域與會場配置] ──► [真實文獻即時抓取] ──► [具名核准的研究計畫]
                                                        │
  [直接投稿發布] ◄── [多層次對抗式審查] ◄── [可執行的 Issues 契約]
```

**CameraReady** 將學術論文撰寫轉變為一套**確定性、可追蹤且具備防呆機制的工程管線**。每個階段都有明確的進入條件、可由腳本機械化檢驗的離開條件，以及只嚴格檢驗回報、絕不擅自猜測修飾的檢查閘門。

---

<a name="五分鐘快速上手"></a>

## 五分鐘快速上手：從零到可編譯骨架

CameraReady 核心流程**僅需 Python 3.10+**（全流程採用 Python 標準函式庫，免去繁瑣的 `pip install` 環境衝突）。

```bash
# 1. 複製本倉庫
git clone https://github.com/e96031413/camera-ready.git
cd camera-ready

# 2. 列出支援的學科並快速建立初始專案
python scripts/quick_start.py --list
python scripts/quick_start.py --title "Sleep duration and next-day recall" --discipline psychology
```

這會立即建立一個架構完整、具備驗證防護的論文工作區：

```text
papers/sleep-duration-and-next-day-recall/
├── main.md                         # 包含 APA 規範 Front Matter 的章節骨架（零憑空捏造內文）
├── ref.bib                         # 乾淨的參考文獻檔（註解標明真實檢索指令）
├── plan/...-sleep-duration....md   # 結構化研究計畫書（等待研究者具名核准）
├── issues/...-sleep-duration....csv # 具備明確驗收準則與相依性的 12 欄任務契約
└── notes/autopilot-state.json      # 確定性狀態機記錄檔（停駐於第 1 階段）
```

接著，檢視領域規範並進行建置：

```bash
# 檢視心理學領域的審查焦點與報告規範清單
python scripts/discipline_profile.py requirements psychology

# 依官方 APA 7th CSL 樣式將文件轉換為 Word (.docx) 檔
python scripts/export_document.py --input papers/sleep-duration-and-next-day-recall/main.md --style apa7

# 查看目前階段狀態與通過第 1 關的確切條件
python scripts/autopilot.py status --project-dir papers/sleep-duration-and-next-day-recall
```

專案骨架能順利編譯通過，但裡面沒有任何一句由模型憑空編造的論點。核心學術論證始終掌控在您的手中。

- **檢視完整範例論文**：[`examples/minimal-review-paper/`](examples/minimal-review-paper/README.md)（附帶已編譯並進版控的 [`main.pdf`](examples/minimal-review-paper/main.pdf)）。
- **終端操作完整實錄**：[`docs/DEMO.md`](docs/DEMO.md)（可藉由 `bash docs/demo-script.sh` 完整重現）。

---

## 分閘門論文流水線（The Gated Pipeline）

<p align="center">
  <img src="assets/images/workflow_gates.jpg" alt="CameraReady Gated Workflow Pipeline" width="100%" />
</p>

CameraReady 由 `scripts/autopilot.py` 驅動，將研究生命週期劃分為 10 個具備硬性防護的連續階段。每一個階段都嚴格比對真實磁碟檔案的離開條件，未滿足前絕不推進：

| # | 階段代號 | 階段名稱 | 核心離開條件與硬性閘門 |
|:---:|:---|:---|:---|
| **1** | `ideate` | 選題構想 | 透過 SMART 與 FINER 原則確立研究問題（RQ）；完成研究邊界與文獻缺口分析。 |
| **2** | `literature` | 文獻探勘 | 從 DBLP / CrossRef / arXiv API 匯入真實書目；**嚴禁殘留任何 `PLACEHOLDER_` 條目**。 |
| **3** | `plan` | 計畫審定 | **具名核准人閘門**：必須由真人研究者具名核准研究計畫書（`--approved-by`）。 |
| **4** | `issues` | 執行契約 | 建立 12 欄 Issues CSV，註明 DAG 相依性、負責人與驗收標準；通過相依環迴圈檢測。 |
| **5** | `experiments` | 實驗證據 | 彙整 Evidence Pack 與實驗紀錄（詮釋型與法釋義型學科自動略過此關）。 |
| **6** | `draft` | 兩階段成文 | 嚴格執行「條列大綱」先於「內文散文」；每一項 Issue 的驗收條件均需標註為 `DONE`。 |
| **7** | `verify` | 自動化品管 | 格式頁數檢查、雙盲匿名檢測、隱私防護掃描與領域準則檢查全數通過。 |
| **8** | `review` | 多面向評審 | 執行內在三層評審（邏輯、論證、語調）與跨模型對抗式審查，產出具體改善編號。 |
| **9** | `revise` | 系統性答辯 | 每一條審查意見皆需提供具體的非 TODO 處置記錄與更新佐證。 |
| **10** | `camera-ready` | 完稿發布 | 產生符合 arXiv 規定的乾淨投稿壓縮包（`submission.tar.gz`）與後續材料。**由真人送出投稿。** |

> [!NOTE]
> AI Agent 負責繁重的文獻爬梳、初稿撰寫與迭代修訂；狀態機則負責捍衛流程紀律。若需跳過特定閘門，必須明確提供 `--force --reason "<理由>"`，該紀錄將永久保留於日誌中供後續稽核。

---

## 核心優勢：CameraReady 與一般 AI 工具的四大本質差異

### 1. 零幻覺引用架構（Zero-Hallucination Citations）
在 CameraReady 中，嚴格禁止大模型依憑自身權重記憶生成參考文獻。
- 書目中繼資料一律直接自 **DBLP、CrossRef 或官方 arXiv API** 檢索擷取。
- 凡無法自公開權威資料庫取得驗證的文獻，一律標註 `PLACEHOLDER_` 前綴。
- `verify_citations.py` 會阻斷建置流程，只要有一筆未驗證的佔位符流向參考文獻檔即判定失敗。
- `citation_style.py validate` 依各格式所需欄位嚴格查核（例如 APA 必須有 DOI、Vancouver 必須維持數字編號、IEEE 必須使用標準 BibTeX 鍵值）。

### 2. 具備法律效力般的 Issues CSV 執行契約
CameraReady 捨棄無結構的待辦清單，採用嚴謹的 12 欄 CSV 作為交付契約：
- **包含欄位**：`Issue_ID`、`Section`、`Task_Description`、`Acceptance_Criteria`、`Dependencies`、`Owner`、`Status`、`Verified_Citations`、`Word_Count_Target`、`Notes`。
- `validate_paper_issues.py` 自動驗證資料綱要，並在有向無環圖（DAG）中偵測是否有死結相依環。
- 只有當具體的驗收標準全數滿足，且真實引用數量檢核無誤時，該章節任務方能標記為 `DONE`。

### 3. 兩階段寫作與三層自我審查（Two-Stage Writing & Multi-Pass Self-Review）
任何章節的撰寫都必須依循雙階段原則：
1. **第 1 階段（條列大綱）**：明確規畫段落論述核心、邏輯層次與欲引用的文獻定位。
2. **第 2 階段（散文成文）**：根據結構化大綱展開為具學術語感的段落。

稿件完成後，將經過四道獨立的診斷檢查工具：
- **`logic_selfloop.py`**：檢查論證推導的連貫性，剔除毫無根據的邏輯跳躍。
- **`argument_selfloop.py`**：核對每個事實主張是否具備充足的文獻或數據佐證。
- **`voice_selfloop.py`**：調整學術文氣與語調，確保行文自然且符合該學科嚴謹度。
- **`anti_ai_scan.py`**：掃描並消除典型的 AI 模板化詞彙（如 delve into、testament、pivotal）與機械式重複句型。

### 4. 涵蓋完整出版生命週期（Full Lifecycle Support）
多數 AI 工具止步於「輸出初稿」。CameraReady 支援自發想到論文獲刊後的完整周邊產出：
- **學術會議論文**：IEEEtran 雙欄、NeurIPS、ICML、ICLR、ACL、AAAI、CVPR 專用排版。
- **Beamer 簡報**：包含高質感程式碼高亮與 TikZ 向量架構圖的 XeLaTeX 簡報。
- **PowerPoint 簡報**：由 Node.js + PptxGenJS 產出的原生 `.pptx`，方程式支援向量級排版。
- **學術海報**：支援響應式 HTML/CSS 大圖排版，透過 Playwright 高解析度渲染輸出。
- **影片論文與語音導讀**：結合 Remotion 影片引擎與神經網絡 TTS 產生含字幕的論文宣傳影片。

---

## 跨學科與多引用格式矩陣

CameraReady 為 8 大主流學術領域量身打造設定檔，自動配置對應的引用風格、排版管道與法定報告準則：

| 學術領域 | 預設引用格式 | 輸出格式管道 | 必備報告準則與檢查清單 |
|:---|:---|:---|:---|
| **資訊工程與機器學習 (CS/ML)** | IEEE | LaTeX PDF | 會議官方 Checklist (NeurIPS/ICML/ICLR/ACL/AAAI/CVPR) |
| **心理學與認知科學** | APA 7th | Word / PDF | JARS-Quant、CONSORT、PRISMA |
| **臨床醫學與健康科學** | Vancouver | Word / PDF | CONSORT、STROBE、PRISMA、CARE |
| **教育學研究** | APA 7th | Word / PDF | JARS-Qual、COREQ、CHERRIES、PRISMA |
| **商管與經濟學** | APA 7th | Word / PDF | PRISMA、CHERRIES |
| **社會科學** | Chicago (Author-Date) | Word / PDF | COREQ、SRQR、CHERRIES、STROBE、PRISMA |
| **人文學科與文學研究** | MLA 9th | Word / PDF | 原始文本引註規範與第一手文獻標註 |
| **法學與法釋義研究** | Chicago (Notes & Bib) | Word / PDF | 司法判例與權威法源追蹤清單 |

> **客製化擴充**：若您的學術領域不在預設清單中，僅需新增一個 YAML 或 Markdown 檔案即可完成定義。詳見 [`docs/EXTENDING.md`](docs/EXTENDING.md)。

---

## 全自動化檢查閘門（The Quality Gates）

管線內建多個具備一票否決權的獨立檢查工具：

| 閘門腳本 | 攔截檢查項目 | 處置行為 |
|:---|:---|:---|
| `format_gate.py` | 正文頁數超標、遺漏會議必要章節、樣式檔（.sty）未正確載入。 | **阻斷建置** |
| `anonymity_check.py` | 雙盲模式下殘留作者姓名、`\thanks`、信箱、專案 Repo 連結、PDF 中繼資料。 | **阻斷建置** |
| `verify_citations.py` | 未解析的引用鍵值、虛構的 BibTeX、殘存的 `PLACEHOLDER_` 項目。 | **阻斷建置** |
| `citation_style.py` | 參考文獻條目缺少該引用格式渲染所需的必要中繼欄位。 | **阻斷建置** |
| `integrity_gate.py` | 論文主張與被引來源實際研究成果不符或誇大其實。 | **列出警示清單** |
| `anti_ai_scan.py` | 充斥機器生成慣用語、過度修飾的陳腐詞彙與重複句法特徵。 | **目標：LOW** |
| `paper_privacy_scan.py` | 洩漏私密金鑰、API Tokens、內部伺服器主機名稱、開發者本機絕對路徑。 | **阻斷建置** |
| `paper_checklist.py` | 會議官方 Checklist 工作表未填寫或格式不符（如 NeurIPS）。 | **阻斷建置** |
| `reporting_guideline.py` | PRISMA、CONSORT、STROBE 等領域醫學/實證標準工作表未完成填答。 | **阻斷建置** |
| `arxiv_package.py` | 缺少插圖、格式不合規、未內嵌 `.bbl`、絕對路徑參照、檔案容量過大。 | **產出乾淨壓縮包** |
| `portability_check.py` | 作業系統編碼陷阱（Windows vs Linux）、硬編碼 POSIX 路徑、非跨平台呼叫。 | **CI 強制驗證** |
| `skill_spec_check.py` | `SKILL.md` frontmatter 未遵守 Agent Skills 開放規格標準。 | **CI 強制驗證** |

> [!TIP]
> **檢驗哲學：** 閘門工具絕不背著研究者暗中修改論文內容，更絕不代填任何檢查清單答覆。`paper_checklist.py` 會自動建立標註 `[TODO]` 的檢查表，必須由研究者審核確認後方可通過。詳見 [`docs/GUARANTEES.md`](docs/GUARANTEES.md)。

---

## 頂級會議支援矩陣

內建各大頂級國際學術會議最新規範配置，自動檢驗頁數、版面並動態下載官方最新 style 檔案：

| 會議簡稱 | 正文頁數上限 | 版面規範 | Checklist 要求 | 設定檔路徑 |
|:---|:---|:---|:---|:---|
| **NeurIPS** | 9 頁 | 單欄，10pt | 強制必填 | [`neurips.yaml`](assets/venues/neurips.yaml) |
| **ICML** | 8 頁 | 雙欄，10pt | 強制必填 | [`icml.yaml`](assets/venues/icml.yaml) |
| **ICLR** | 9 頁 | 單欄，10pt | 必須填答 | [`iclr.yaml`](assets/venues/iclr.yaml) |
| **ACL** | 8 頁（Long Paper） | 雙欄，11pt，A4 | 必須填答 | [`acl.yaml`](assets/venues/acl.yaml) |
| **AAAI** | 7 + 1 + 1 頁 | 雙欄，10pt | 必須填答 | [`aaai.yaml`](assets/venues/aaai.yaml) |
| **CVPR** | 8 頁 | 雙欄，10pt | 無強制要求 | [`cvpr.yaml`](assets/venues/cvpr.yaml) |
| **arXiv** | 無頁數上限 | IEEEtran 雙欄預設 | 選填 | 內建樣板 |

*會議專用樣式檔（.sty/.cls）於執行時期由 `scripts/venue_setup.py` 從官方入口即時下載，嚴格遵守各會議智慧財產與轉散布條款。*

---

## 環境與前置需求

### 基礎核心環境
- **Python 3.10 以上**：標準核心管線完全無須安裝外部第三方 pip 套件。

### 依輸出材料之選配工具鏈
| 欲產出之成果文件 | 建議安裝工具鏈 |
|:---|:---|
| **LaTeX PDF（IEEE / 會議論文）** | TeX Live、MacTeX 或 MiKTeX |
| **LaTeX PDF（APA / MLA / Chicago / Vancouver）** | TeX Live / MiKTeX 並搭載 `biber` 與相關樣式包 |
| **Word / Markdown / Typst / HTML** | `pandoc`（可執行 `python scripts/export_document.py --check` 檢測） |
| **Beamer 簡報投影片** | XeLaTeX |
| **PowerPoint (.pptx) 簡報** | Node.js + PptxGenJS（數學式排版需 `pandoc`） |
| **學術論文海報** | Playwright + Chromium、Pillow |
| **配音簡報論文影片** | Node.js + Remotion、神經網絡語音合成引擎、`ffprobe` |

---

## 作為 Agent Skill 使用

CameraReady 完全符合 [Agent Skills](https://agentskills.io) 開放標準規範：

```bash
# 安裝至 Claude Code
cp -r . ~/.claude/skills/camera-ready

# 在 Claude Code 對話中直接呼叫：
/camera-ready
```

- 完美整合 **Claude Code**、**claude.ai**、**Gemini CLI**、**Codex** 等 AI Agent 開發環境。
- **100% 支援獨立運作**：所有 `scripts/` 工具均可作為單機 CLI 命令行工具，由人類直接調用執行。

---

## 常見問題 FAQ

<details>
<summary><strong>CameraReady 會直接幫我全自動寫出一篇完整論文嗎？</strong></summary>

CameraReady 負責搭設嚴密的骨架、自動化查核引用真實性、執行自審並標註瑕疵。雖然 `autopilot.py` 具備自動驅動管線的能力，但學術假說的推演、核心論點與 Checklist 上的審查問答仍屬於研究者本人的智慧成果。關鍵節點（如計畫書核准）必須由真人明確放行。
</details>

<details>
<summary><strong>CameraReady 如何保證論文中的參考文獻絕無虛構？</strong></summary>

所有參考文獻一律透過公開權威 API（DBLP、CrossRef、arXiv 官方資料庫）即時檢索。若查無此文，系統會產生 `PLACEHOLDER_` 標籤並停止匯入。引用驗證閘門（`verify_citations.py`）會將任何殘留的佔位符視為嚴重錯誤並中斷建置。
</details>

<details>
<summary><strong>如果我的投稿期刊只收 Microsoft Word 格式，可以使用嗎？</strong></summary>

完全可以！CameraReady 將 Word（`.docx`）視為一等公民輸出格式（在心理學、醫學與社科領域廣泛應用）。您只需在語意明確的 Markdown 中撰寫並嵌入文獻鍵值，`export_document.py` 便會透過官方 CSL 引擎精確排版並輸出為符合格式的 Word 稿件。
</details>

<details>
<summary><strong>本工具會自動將我的論文上傳到 arXiv 或各大學術會議系統嗎？</strong></summary>

**絕不。** `arxiv_package.py` 僅在本地端建構符合規範的乾淨壓縮包（`submission.tar.gz`）。依據我們的 Follow-Through 原則與 [`SECURITY.md`](SECURITY.md)，將成果上傳到任何公開伺服器或評審平台，永遠由研究者本人手動操作。
</details>

---

## 專案結構一覽

```text
camera-ready/
├── SKILL.md                  # 給 AI Agent 的分閘門完整工作流規範文件
├── assets/
│   ├── disciplines/          # 8 大學術領域設定檔
│   ├── styles/               # 6 大引用格式定義檔
│   ├── venues/               # 頂級會議配置（NeurIPS、ICML、ICLR、ACL 等）
│   ├── checklists/           # 會議檢核表與醫學/實證報告規範（PRISMA、CONSORT 等）
│   ├── images/               # 專案視覺橫幅與管線流程架構圖
│   └── template/             # LaTeX、Beamer、海報與影片專用範本
├── docs/
│   ├── QUICKSTART.md         # 循序漸進的實務入門指引
│   ├── DEMO.md               # 可完全重現的終端操作實錄
│   ├── GUARANTEES.md         # 嚴格界定：機器驗證 vs 輔助偵測 vs 真人責任
│   ├── EXTENDING.md          # 擴充會議、學科與報告規範的操作手冊
│   └── TROUBLESHOOTING.md    # 常見錯誤現象、原因診斷與排解方案
├── examples/
│   └── minimal-review-paper/ # 完整編譯範例論文（包含計畫、CSV 與各項閘門報告）
├── references/               # 關於引用格式、學術語感、反擊審查的深度參考指南
├── scripts/                  # 獨立運行的 CLI 命令行工具（包含鷹架、品管閘門與編譯輸出）
└── tests/                    # 橫跨 Windows、macOS 與 Linux 平台的 420+ 項自動化測試套件
```

---

## 授權條款

本專案採用 [MIT 授權條款](LICENSE) 釋出。第三方組件（如 `IEEEtran.cls`、會議官方樣式檔與 CSL 格式檔）保留原作者之智慧財產權與專屬授權，詳見 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
