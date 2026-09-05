<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-TW.md">繁體中文</a> · <strong>简体中文</strong>
</p>

<p align="center">
  <img src="assets/images/hero_banner.jpg" alt="CameraReady Banner" width="100%" />
</p>

<h1 align="center">CameraReady</h1>

<p align="center">
  <strong>从选题构想到可直接投稿 — 每一关都有严格闸门把守。</strong><br>
  <em>专为 AI Agent 设计的跨学科自主学术论文研究与写作流水线，以绝不妥协的学术严谨度构建。</em>
</p>

<p align="center">
  <a href="https://opensource.org/licenses/MIT"><img alt="License: MIT" src="https://img.shields.io/badge/License-MIT-yellow.svg"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/Python-3.10%2B-blue.svg">
  <img alt="Platforms" src="https://img.shields.io/badge/平台-Windows%20%7C%20macOS%20%7C%20Linux-brightgreen.svg">
  <img alt="Disciplines" src="https://img.shields.io/badge/学科-8%20大领域支持-purple.svg">
  <img alt="Citation Styles" src="https://img.shields.io/badge/引用格式-APA%20%7C%20MLA%20%7C%20Chicago%20%7C%20Vancouver%20%7C%20IEEE-orange.svg">
  <img alt="Zero Hallucination" src="https://img.shields.io/badge/引用验证-零幻觉保证-success.svg">
  <img alt="Agent Skills" src="https://img.shields.io/badge/Agent%20Skills-标准规范兼容-blueviolet.svg">
</p>

<p align="center">
  <a href="#五分钟快速上手"><strong>⚡ 5 分钟快速上手</strong></a> ·
  <a href="examples/minimal-review-paper/main.pdf"><strong>📄 示例编译论文 (PDF)</strong></a> ·
  <a href="docs/DEMO.md"><strong>🎥 终端实录 Demo</strong></a> ·
  <a href="docs/QUICKSTART.md"><strong>🚀 快速入门指南</strong></a> ·
  <a href="docs/GUARANTEES.md"><strong>🛡️ 严谨保证范围</strong></a> ·
  <a href="SKILL.md"><strong>⚙️ 工作流规范</strong></a>
</p>

> [!IMPORTANT]
> **核心保证：** 每一条引用均从权威数据库（DBLP、CrossRef、arXiv API）实时检索获取；每一项主张均能回溯至具体登记的证据；在研究计划未获得实名审核通过前，严禁撰写任何正文内容。

---

## 问题出在哪里：传统 AI 写论文为何必然被拒稿（Desk Reject）

让现有最强的前沿大语言模型（LLM）写一篇论文，它能在数秒钟内生成行文流畅、辞藻华丽的长篇论述。然而，在光鲜的文字表象下，往往潜藏着以下致命硬伤：
- **凭空捏造虚假文献**：依靠模型记忆编造格式逼真的 BibTeX，其中论文标题看似合理却根本不存在，DOI 也是虚构的。
- **过度夸大研究结论**：将文献中局部的、有条件的实验现象，随意推演为具有普适性的绝对结论。
- **无视会议格式与页数硬约束**：要求 8 页面却输出 11 页，或在严格双盲（Double-Blind）评审的 PDF 稿件中泄露作者姓名、机构邮箱与 GitHub 仓库链接。
- **遗漏专业学科的合规声明**：在临床医学论文中忘记登记临床试验注册号（CONSORT），在质性研究中宣称“达到理论饱和”却未交代判据（COREQ）。

这些从不是单纯的“语言润色”问题，而是**“研究工程流程”的系统性缺失**。在顶尖学术会议与期刊中，这类缺陷会在初审阶段直接招致拒稿（Desk Reject）。

```text
常规 AI 生成模式：
  [简单输入 Prompt] ───────────► [凭空编造的初稿] ──► 初审拒稿 (Desk Reject)

CameraReady 分闸门流水线：
  [学科与会场配置] ──► [真实文献实时检索] ──► [实名批准的研究计划]
                                                        │
  [直接投稿发布] ◄── [多维度对抗式评审] ◄── [可执行的 Issues 契约]
```

**CameraReady** 将学术论文写作转化为一套**确定性、可审计且具备防呆机制的工程流水线**。每个阶段均设定严格的准入条件、可由脚本自动化检验的退出条件，以及只客观核查报错、绝不擅自脑补修改的防御闸门。

---

<a name="五分钟快速上手"></a>

## 五分钟快速上手：从零到可构建骨架

CameraReady 核心流程**仅需 Python 3.10+**（全流程完全基于 Python 标准库，彻底告别繁重的 `pip install` 依赖冲突）。

```bash
# 1. 克隆本仓库
git clone https://github.com/e96031413/camera-ready.git
cd camera-ready

# 2. 列出支持的学科并快速初始化项目
python scripts/quick_start.py --list
python scripts/quick_start.py --title "Sleep duration and next-day recall" --discipline psychology
```

该命令将瞬间生成一个结构完备、具备验证防护的论文工作目录：

```text
papers/sleep-duration-and-next-day-recall/
├── main.md                         # 包含 APA 规范 Front Matter 的骨架文件（零虚构正文）
├── ref.bib                         # 干净的参考文献文件（注释标注真实检索命令）
├── plan/...-sleep-duration....md   # 结构化研究计划书（等待研究人员实名签署核准）
├── issues/...-sleep-duration....csv # 具备明确验收标准与依赖关系的 12 列任务契约
└── notes/autopilot-state.json      # 确定性状态机记录文件（停留在第 1 阶段）
```

随后，查看学科规范并导出预览：

```bash
# 查看心理学领域的评审要求与强制报告规范清单
python scripts/discipline_profile.py requirements psychology

# 遵循官方 APA 7th CSL 样式将文档转换为 Word (.docx) 文件
python scripts/export_document.py --input papers/sleep-duration-and-next-day-recall/main.md --style apa7

# 查看当前阶段状态与顺利通过第 1 关的明确条件
python scripts/autopilot.py status --project-dir papers/sleep-duration-and-next-day-recall
```

论文骨架能够顺利编译导出，但其中绝不包含任何模型凭空编造的主张。核心学术论证完全由您掌控。

- **查看完整已编译论文示例**：[`examples/minimal-review-paper/`](examples/minimal-review-paper/README.md)（包含已提交入库的 [`main.pdf`](examples/minimal-review-paper/main.pdf)）。
- **终端操作全过程实录**：[`docs/DEMO.md`](docs/DEMO.md)（可通过 `bash docs/demo-script.sh` 完整复现）。

---

## 分闸门论文流水线（The Gated Pipeline）

<p align="center">
  <img src="assets/images/workflow_gates.jpg" alt="CameraReady Gated Workflow Pipeline" width="100%" />
</p>

CameraReady 由 `scripts/autopilot.py` 驱动，将学术论文研究生命周期拆解为 10 个设置有硬性校验防线的有序阶段。每个阶段均严格比对真实磁盘文件，条件未达成前绝不前移：

| # | 阶段代号 | 阶段名称 | 核心退出条件与硬性闸门 |
|:---:|:---|:---|:---|
| **1** | `ideate` | 选题构想 | 遵循 SMART 与 FINER 原则确立研究问题（RQ）；完成研究边界与文献空白分析。 |
| **2** | `literature` | 文献检索 | 从 DBLP / CrossRef / arXiv API 引入真实文献；**绝对禁止残留 `PLACEHOLDER_` 条目**。 |
| **3** | `plan` | 计划审定 | **实名签署闸门**：必须由真实研究人员实名核准研究计划书（`--approved-by`）。 |
| **4** | `issues` | 执行契约 | 生成 12 列 Issues CSV，定义 DAG 依赖、责任人与验收准则；杜绝任何循环依赖。 |
| **5** | `experiments` | 实验证据 | 归档 Evidence Pack 与实验日志（诠释学与规范法学领域自动跳过本阶段）。 |
| **6** | `draft` | 双阶段撰写 | 严格执行“提纲先行”于“正文行文”；每个章节 Issue 验收条件均需满足并标记 `DONE`。 |
| **7** | `verify` | 自动化质检 | 格式页数检查、双盲匿名审计、敏感信息扫描与领域报告规范全数通过。 |
| **8** | `review` | 多维度评审 | 运行内置三层自审（逻辑、论据、语气）与跨模型对抗式评审，输出编号意见清单。 |
| **9** | `revise` | 系统性答辩 | 每条评审意见均需提供非 TODO 的具体修改记录与支撑论据。 |
| **10** | `camera-ready` | 完稿归档 | 构建符合 arXiv 官方标准的干净投稿包（`submission.tar.gz`）及配套材料。**由人工提交。** |

> [!NOTE]
> AI Agent 负责大量的文献比对、内容草拟与迭代修订；状态机则负责坚守学术纪律。若需强制跳过某一闸门，必须显式附加 `--force --reason "<说明理由>"`，该记录将永久记录在运行日志中以便后续核查。

---

## 核心优势：CameraReady 与普通 AI 工具的四大本质差异

### 1. 零幻觉引用体系（Zero-Hallucination Citations）
在 CameraReady 中，大语言模型仅凭内部记忆生成参考文献被严格禁止。
- 书目元数据一律直接自 **DBLP、CrossRef 或官方 arXiv API** 检索拉取。
- 凡无法在官方公共文献库中核实的数据，统一打上 `PLACEHOLDER_` 前缀标记。
- `verify_citations.py` 会直接阻断构建流程，任何未经核实的占位符进入参考文献均判定失败。
- `citation_style.py validate` 根据目标格式要求逐字段校验（如 APA 必附 DOI、Vancouver 采用数字序号、IEEE 保持标准 BibTeX 键名）。

### 2. 具备执行约束力的 Issues CSV 契约
CameraReady 放弃随意凌乱的 TODO 清单，采用工程化 12 列 CSV 作为交付契约：
- **包含字段**：`Issue_ID`、`Section`、`Task_Description`、`Acceptance_Criteria`、`Dependencies`、`Owner`、`Status`、`Verified_Citations`、`Word_Count_Target`、`Notes`。
- `validate_paper_issues.py` 自动校验数据模式，并在有向无环图（DAG）中排查死锁依赖环。
- 只有在验收准则完全达标且真实引用条数核实无误时，对应的章节任务才能标记为 `DONE`。

### 3. 双阶段撰写与三层自我审查（Two-Stage Writing & Multi-Pass Self-Review）
所有章节正文均强制拆分为两个步骤：
1. **第 1 阶段（要点提纲）**：规划段落核心逻辑、论述主旨与文献引用落点。
2. **第 2 阶段（正文成文）**：根据提纲拓展为兼具学术严谨度与可读性的段落。

正文完成后，依次通过四套针对特定维度的诊断工具：
- **`logic_selfloop.py`**：核查论述推导链条，清除无前提支撑的跳跃性结论。
- **`argument_selfloop.py`**：核对每个事实论断是否有充分的引用或实验数据背书。
- **`voice_selfloop.py`**：规范学术行文语调与节奏，剔除口语化或浮夸表述。
- **`anti_ai_scan.py`**：扫描并消除典型的 AI 生成味词汇（如 delve into、testament、pivotal）及刻板句式。

### 4. 贯穿成果出版的全生命周期（Full Lifecycle Support）
绝大多数 AI 工具止步于“输出初稿”。CameraReady 覆盖从立项到录用后的完整科研衍生品：
- **学术会议论文**：IEEEtran 双栏排版，NeurIPS、ICML、ICLR、ACL、AAAI、CVPR 专用模板。
- **Beamer 幻灯片**：配备精美代码高亮与 TikZ 矢量架构图的 XeLaTeX 演示文稿。
- **PowerPoint 演示**：基于 Node.js + PptxGenJS 生成的原生 `.pptx`，数学公式支持矢量级排版。
- **学术海报**：支持响应式 HTML/CSS 大图排版，利用 Playwright 进行高分辨率无损渲染。
- **视频论文与语音解说**：借助 Remotion 渲染引擎与神经语音合成技术生成带字幕的论文讲解视频。

---

## 跨学科与多引用格式矩阵

CameraReady 为 8 大主流科研门类量身定制配置画像，自动匹配对应的引用格式、输出编译流与报告规范：

| 学科领域 | 默认引用格式 | 输出格式通道 | 必遵报告规范与合规检查表 |
|:---|:---|:---|:---|
| **计算机科学与机器学习 (CS/ML)** | IEEE | LaTeX PDF | 会议官方 Checklist (NeurIPS/ICML/ICLR/ACL/AAAI/CVPR) |
| **心理学与认知科学** | APA 7th | Word / PDF | JARS-Quant、CONSORT、PRISMA |
| **临床医学与健康科学** | Vancouver | Word / PDF | CONSORT、STROBE、PRISMA、CARE |
| **教育学研究** | APA 7th | Word / PDF | JARS-Qual、COREQ、CHERRIES、PRISMA |
| **商科与经济学** | APA 7th | Word / PDF | PRISMA、CHERRIES |
| **社会科学** | Chicago (作者-年份) | Word / PDF | COREQ、SRQR、CHERRIES、STROBE、PRISMA |
| **人文与文学研究** | MLA 9th | Word / PDF | 原文引证规范与一手文献标引 |
| **法学与规范法学研究** | Chicago (注释与书目) | Word / PDF | 司法判例与权威法源追踪列表 |

> **自定义扩展**：若您的学科尚未被内置收录，只需添加一个 YAML 或 Markdown 文件即可完成定义。详见 [`docs/EXTENDING.md`](docs/EXTENDING.md)。

---

## 全自动化检查闸门（The Quality Gates）

流水线内置多道拥有一票否决权的独立校验脚本：

| 闸门脚本 | 拦截排查项目 | 处置策略 |
|:---|:---|:---|
| `format_gate.py` | 正文页数超标、遗漏会议规定章节、样式包（.sty）未正确引入。 | **阻断构建** |
| `anonymity_check.py` | 双盲评审模式下残留作者姓名、`\thanks`、邮箱、仓库链接与 PDF 元数据。 | **阻断构建** |
| `verify_citations.py` | 未定位的引用键名、虚构 BibTeX、残留的 `PLACEHOLDER_` 条目。 | **阻断构建** |
| `citation_style.py` | 参考文献条目缺少目标样式渲染所需的必要元数据字段。 | **阻断构建** |
| `integrity_gate.py` | 论文断言超出被引文献的真实研究范围或存在过度吹捧。 | **输出警告清单** |
| `anti_ai_scan.py` | 充斥大模型陈词滥调、机械句式与高频 AI 标记词汇。 | **目标：LOW** |
| `paper_privacy_scan.py` | 泄露个人密钥、API Tokens、内网服务器主机名、本地绝对路径。 | **阻断构建** |
| `paper_checklist.py` | 会议官方 Checklist 工作表漏填或格式异常（如 NeurIPS）。 | **阻断构建** |
| `reporting_guideline.py` | PRISMA、CONSORT、STROBE 等医学/实证规范表存在未作答项。 | **阻断构建** |
| `arxiv_package.py` | 遗漏插图、非合规图片格式、未内嵌 `.bbl`、引用绝对路径、超大文件。 | **打包干净 Tarball** |
| `portability_check.py` | 操作系统编码差异（Windows vs Linux）、硬编码 POSIX 路径、非便携调用。 | **CI 强制检查** |
| `skill_spec_check.py` | `SKILL.md` frontmatter 未遵循 Agent Skills 开放标准规范。 | **CI 强制检查** |

> [!TIP]
> **排查哲学：** 闸门工具绝不会擅自静默修改您的论文，更严禁替作者代填任何清单问答。`paper_checklist.py` 会自动生成填入 `[TODO]` 的核查表，必须由研究者实名确认后方可通过。详见 [`docs/GUARANTEES.md`](docs/GUARANTEES.md)。

---

## 顶级学术会议支持矩阵

官方配置同步各大顶尖国际会议最新规范，自动检测篇幅与排版并按需下载官方样式文件：

| 会议简称 | 正文篇幅上限 | 版面排版标准 | Checklist 规范要求 | 配置文件路径 |
|:---|:---|:---|:---|:---|
| **NeurIPS** | 9 页 | 单栏，10pt | 强制必填 | [`neurips.yaml`](assets/venues/neurips.yaml) |
| **ICML** | 8 页 | 双栏，10pt | 强制必填 | [`icml.yaml`](assets/venues/icml.yaml) |
| **ICLR** | 9 页 | 单栏，10pt | 必须填答 | [`iclr.yaml`](assets/venues/iclr.yaml) |
| **ACL** | 8 页（Long Paper） | 双栏，11pt，A4 | 必须填答 | [`acl.yaml`](assets/venues/acl.yaml) |
| **AAAI** | 7 + 1 + 1 页 | 双栏，10pt | 必须填答 | [`aaai.yaml`](assets/venues/aaai.yaml) |
| **CVPR** | 8 页 | 双栏，10pt | 无硬性要求 | [`cvpr.yaml`](assets/venues/cvpr.yaml) |
| **arXiv** | 无页数限制 | IEEEtran 默认双栏 | 可选 | 内置模板 |

*会议专用样式包（.sty/.cls）在运行期由 `scripts/venue_setup.py` 从大会官方网址按需拉取，严格遵守各学术组织的版权政策。*

---

## 环境与前置依赖

### 核心极简环境
- **Python 3.10 及以上**：核心骨架与闸门校验无需安装任何外部第三方 pip 库。

### 根据输出目标的扩展工具链
| 目标成果类型 | 建议安装工具链 |
|:---|:---|
| **LaTeX PDF（IEEE / 会议论文）** | TeX Live、MacTeX 或 MiKTeX |
| **LaTeX PDF（APA / MLA / Chicago / Vancouver）** | TeX Live / MiKTeX 且搭载 `biber` 及对应宏包 |
| **Word / Markdown / Typst / HTML** | `pandoc`（可运行 `python scripts/export_document.py --check` 检测） |
| **Beamer 演示幻灯片** | XeLaTeX |
| **PowerPoint (.pptx) 幻灯片** | Node.js + PptxGenJS（数学公式转换需要 `pandoc`） |
| **学术展示海报** | Playwright + Chromium、Pillow |
| **论文解说视频** | Node.js + Remotion、神经语音合成引擎、`ffprobe` |

---

## 作为 Agent Skill 使用

CameraReady 完整遵循 [Agent Skills](https://agentskills.io) 开放协议规范：

```bash
# 安装至 Claude Code 技能库
cp -r . ~/.claude/skills/camera-ready

# 在 Claude Code 对话中直接唤起：
/camera-ready
```

- 完美兼容 **Claude Code**、**claude.ai**、**Gemini CLI**、**Codex** 等 AI Agent 系统。
- **100% 独立 CLI 可用**：`scripts/` 目录下的所有工具均支持人类研究人员在终端独立调用。

---

## 常见问题 FAQ

<details>
<summary><strong>CameraReady 会直接替我全自动写完一整篇论文吗？</strong></summary>

CameraReady 负责搭建严密骨架、校验文献真实性、执行自审并阻断违规操作。虽然 `autopilot.py` 可以自动化贯穿流程，但核心科学假设、关键论述观点以及审查清单上的回应依然源自人类研究人员。关键节点（例如研究计划书审批）严格要求实名人工放行。
</details>

<details>
<summary><strong>CameraReady 如何确保论文引用百分之百真实存在？</strong></summary>

所有文献条目均通过权威官方 API（DBLP、CrossRef、arXiv）实时联网检索。检索失败的条目会被标注 `PLACEHOLDER_` 前缀并终止导入。引用校验闸门（`verify_citations.py`）会将任何遗留的占位符视为严重错误并中断编译。
</details>

<details>
<summary><strong>若我的投稿期刊要求提供 Microsoft Word 格式，可以使用吗？</strong></summary>

完全可以！CameraReady 将 Word（`.docx`）视为一等公民输出格式（在心理学、医学与社科领域极为常见）。您只需使用语义清晰的 Markdown 撰写并标注文献键，`export_document.py` 便会调用官方 CSL 规范精确格式化并导出为标准 Word 稿件。
</details>

<details>
<summary><strong>该工具会自动将论文上传到 arXiv 或大会投稿系统吗？</strong></summary>

**绝不。** `arxiv_package.py` 仅在本地打包符合规范的投稿归档包（`submission.tar.gz`）。根据我们的 Follow-Through 政策与 [`SECURITY.md`](SECURITY.md)，上传至任何公共平台或评审系统始终必须由研究人员本人手动执行。
</details>

---

## 项目目录结构

```text
camera-ready/
├── SKILL.md                  # 面向 AI Agent 的分闸门完整工作流规范文档
├── assets/
│   ├── disciplines/          # 8 大支持学科设定集
│   ├── styles/               # 6 大引用格式规范定义
│   ├── venues/               # 顶级会议配置文件（NeurIPS、ICML、ICLR、ACL 等）
│   ├── checklists/           # 会议自查表与医学/实证报告规范（PRISMA、CONSORT 等）
│   ├── images/               # 项目视觉横幅与流水线架构图
│   └── template/             # LaTeX、Beamer、海报与视频模板
├── docs/
│   ├── QUICKSTART.md         # 循序渐进的实操入门指导
│   ├── DEMO.md               # 完全可复现的终端操作实录
│   ├── GUARANTEES.md         # 严谨边界：机器校验 vs 辅助检测 vs 人工责任
│   ├── EXTENDING.md          # 扩展新会议、学科与报告规范的操作指引
│   └── TROUBLESHOOTING.md    # 常见故障特征、原因诊断与排解方案
├── examples/
│   └── minimal-review-paper/ # 完整编译示例论文（包含计划、CSV 契约与各项报告）
├── references/               # 深入探讨引用、文风与答辩策略的参考指南
├── scripts/                  # 独立 CLI 命令行工具集（包含脚手架、质检闸门与编译导出）
└── tests/                    # 跨 Windows、macOS 与 Linux 运行的 420+ 项自动化测试
```

---

## 开源协议

本项目采用 [MIT 许可证](LICENSE) 授权开源。第三方组件（如 `IEEEtran.cls`、会议官方样式文件及 CSL 格式）保留原作者版权与专有许可，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
