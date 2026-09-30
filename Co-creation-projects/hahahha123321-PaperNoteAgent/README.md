# PaperNoteAgent - 可核验的论文精读笔记助手

> 输入一篇论文，生成一份每条要点都附原文证据、并由程序逐句核对的中文精读笔记。

## 📝 项目简介

用 AI 总结论文很方便，但有一个老问题：**你不知道哪句话是论文说的，哪句话是 AI 编的。**

PaperNoteAgent 让每条要点都带上一句从原文逐字复制的英文证据，再由程序到原文里逐句查找。找不到的会被标上 ⚠️，最后给出一个“证据命中率”。这样读笔记时，每句话都能回原文查证。

- **解决什么问题**：AI 论文总结中的编造和曲解
- **特色功能**：原文证据 + 程序核对 + 审核 Agent 复查
- **适用场景**：读英文论文、写文献综述前的精读、课程论文阅读

## ✨ 核心功能

- [x] 支持 arXiv 编号（自动下载）和本地 PDF 两种输入
- [x] 结构化精读笔记：研究问题 / 核心方法 / 实验结论 / 局限性
- [x] 每条要点附原文证据，程序逐句核对，输出证据命中率
- [x] ReaderAgent 写笔记，CheckerAgent 审核，不通过则修正一次
- [x] 调用预算（最多 4 次），预算用完时转人工复核，不会报错中断
- [x] 无需 API Key 的自检单元，覆盖编排流程的各个分支

## 🛠️ 技术栈

- HelloAgents 0.2.9（两个 `SimpleAgent` 协作）
- Pydantic：约束模型输出的 JSON 结构
- pypdf：提取 PDF 文字
- arXiv 公开下载地址（免费，无需 Key）

## 🧭 工作流程

```text
arXiv 编号 / 本地 PDF
  → [Python] 下载、提取文字、去掉参考文献、清洗、限长
  → [ReaderAgent] 生成精读笔记：每条要点 = 中文概括 + 英文原句证据
  → [Python] 逐条核对证据是否出现在原文中
  → [CheckerAgent] 审核要点与证据是否相符、有无遗漏
  → 不通过则修正一次（全程最多 4 次模型调用）
  → [Python] 生成 JSON + Markdown 笔记
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 一个 OpenAI 兼容的 LLM API（如 DeepSeek）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL
```

### 运行项目

```bash
jupyter lab
# 打开 main.ipynb，从上到下运行
```

- 第 11 节“自检”不需要 API Key，可以先运行它，确认环境没有问题
- 第 12 节修改 `PAPER_SOURCE` 就能换论文：
  - arXiv 编号：`"2210.03629"`
  - 本地 PDF：把文件放进 `data/`，写 `"data/你的论文.pdf"`

## 📖 使用示例

```python
report = analyze_paper("2210.03629")   # ReAct 论文
save_report(report)                    # → outputs/2210.03629_note.md
print(report.evidence_hit_rate)        # 证据命中率，如 1.0
```

## 🎯 项目亮点

- **程序核对证据**：“这句话在不在原文里”是可以直接查的问题，交给程序而不是模型判断，结果确定、可复现
- **容错的文本比对**：PDF 提取的文字常有断词、连字、多余空格，比对前统一“压扁”，减少误判
- **处理跨页句子**：用 ReAct 论文实测时发现，跨页的句子会被脚注、页码、页眉打断而误判为“找不到”；现在会先去掉页眉页码，并允许证据被打断一次
- **可测试的编排**：Agent 通过参数传入，自检时换成假 Agent，不花费用就能测试所有分支
- **节省上下文**：每次调用前清空 Agent 历史，避免长论文被重复发送

## ⚠️ 已知限制

- 扫描版（图片）PDF 无法提取文字
- 超过 60000 字符的论文只分析前半部分，笔记中会注明
- 只核对证据“是否存在”，证据与要点“意思是否一致”由 CheckerAgent 判断，仍可能出错

## 🔮 未来计划

- [ ] 按章节切分长论文，分段精读后汇总
- [ ] 找不到证据时，给出原文中最接近的句子
- [ ] 多篇论文对比阅读
- [ ] 扫描版 PDF 的 OCR 支持

## 🙏 致谢

- 感谢 Datawhale 社区和 Hello-Agents 项目
- 编排思路（结构化输出、调用预算、格式修复）参考了共创项目 [Henry2513-MeetingActionAgent](../Henry2513-MeetingActionAgent)

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@hahahha123321](https://github.com/hahahha123321)
