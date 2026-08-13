# ResumeAgent - 中日英三语智能简历生成器

> 基于 HelloAgents 框架的对话式多智能体简历助手：Agent 提问收集 → 结构化事实库 → 三语独立生成 → 导出 PDF

## 📝 项目简介

写一份简历已不易，写三种语言的简历更是灾难——中、日、英三种简历根本不是"互译"，而是三套规范体系：

- **中文**：单页模块化简历，按行业分流个人信息
- **日文**：履歴書 ＋ 職務経歴書 双文档，JIS 固定格式、和暦纪年、照片位
- **英文**：ATS 安全版式 Resume，动词开头、量化成果

ResumeAgent 用**面试式提问**收集求职者信息（用户也可自由补充），沉淀为唯一的结构化事实库，再由确定性渲染器 + LLM 润色器按各语言规范独立生成简历，支持模拟 HR/ATS 评审与 PDF 导出。

### 核心思路

```
Agent 访谈（提问→回答→解析入库）
        ↓
结构化事实库（唯一数据源，改一处三语同步）
        ↓
三语独立生成：中文单页 / 日文双文档 / 英文 ATS 版式（各自规范，而非直译）
        ↓
润色 → 评审 → Markdown / HTML / PDF 导出
```

## ✨ 核心功能

- [x] Agent 访谈式信息收集（缺口驱动提问 + 量化追问 + 回答解析入库）
- [x] 结构化事实库（本地落盘、草稿恢复、防编造约束）
- [x] 和暦换算工具（令和/平成/昭和/大正/明治，正确处理元号切换边界）
- [x] 三语独立生成：履歴書＋職務経歴書（日）/ 单页简历（中）/ ATS Resume（英）
- [x] 三语润色与摘要（数字一致性自动校验，防篡改）
- [x] 模拟 HR / ATS 评审（四项评分 + 问题 + 建议）
- [x] Markdown / HTML / PDF 导出（A4 版式，系统 CJK 字体）

## 🛠️ 技术栈

- HelloAgents 框架（SimpleAgent + Tool + ToolRegistry）
- LLM：DeepSeek（OpenAI 兼容接口，可换 Qwen / Kimi / Ollama）
- PDF：Playwright Chromium（备选：本机 Chrome headless / 浏览器打印）
- 其他：python-dotenv、Jupyter Notebook

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 可选：Playwright Chromium（PDF 导出，`playwright install chromium`）

### 安装依赖

```bash
pip install -r requirements.txt
```

> 说明：`hello-agents` 自 1.0.0 起不再提供 `[all]` extra，直接安装基础包即可。

### 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY（默认 DeepSeek，也可换其他 OpenAI 兼容服务）
```

### 运行项目

```bash
jupyter lab
# 打开 main.ipynb，按顺序运行全部单元格
```

## 📖 使用示例

1. **快速演示**：直接运行全部单元格，会自动完成「访谈 → 解析 → 三语生成 → 润色 → 评审 → PDF 导出」全流程，产物在 `outputs/` 目录
2. **真实使用**：把「交互模式」单元格中的 `RUN_INTERACTIVE` 改为 `True`，即可与 Agent 实时对话完善简历
3. **自定义数据**：修改 `data/sample_answers.json` 中的示例求职者信息

演示产物（`outputs/`）：

| 语言 | 文件 |
|------|------|
| 中文 | `resume_zh.md / .html / .pdf` |
| 日文 | `rirekisho_ja.*`（履歴書）、`shokumu_keirekisho_ja.*`（職務経歴書） |
| 英文 | `resume_en.md / .html / .pdf` |

## 🎯 项目亮点

- **三语独立生成而非互译**：日文走和暦+双文档+照片位，英文走 ATS 安全版式，从渲染层杜绝"翻译腔"
- **每语独立视觉版式**：中文藏青蓝现代单页（色块标题＋技能标签）、日文 JIS 藏青表单（标题带＋照片位）、英文 ATS 安全单栏青灰强调色——三语排版与配色各自设计，而非同一模板换文案
- **确定性工具层**：和暦换算、事实库、渲染器全部可离线复现，LLM 只负责语言任务
- **防幻觉约束**：解析与润色均要求"只基于事实、禁止编造"，并有数字一致性自动校验
- **元号边界正确**：1989/2019 等跨年月份按规范切换（昭和64年→平成元年、平成31年→令和元年）

## 📊 性能评估

- 和暦换算：9 组边界用例全部通过（含 1912/1926/1989/2019 切换点）
- 润色数字一致性：中/日/英三语输出与原文数字集合比对，无篡改遗漏
- 本地渲染四份文档：< 0.5s（不含 LLM 调用）

## 🔮 未来计划

- [ ] 粘贴目标 JD，自动标注简历缺失关键词
- [ ] 多版本管理（同一事实库派生多个投递版本）
- [ ] 多模板切换与日文 B5 纸张支持
- [ ] 上传已有简历（PDF/DOCX）解析导入

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@shiyuanyeming-hub](https://github.com/shiyuanyeming-hub)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
