# VulnAuditAgent - 智能代码漏洞审计助手

> 基于 HelloAgents 框架的三通道协同代码安全审计智能体：规则引擎 + 污点追踪 + LLM 研判

## 📝 项目简介

传统 SAST 工具误报率高，纯 LLM 审计又容易遗漏和幻觉。VulnAuditAgent 把两者结合起来，模拟真实安全工程师"工具初筛 → 数据流分析 → 人工复核"的审计流程：

- **规则引擎**做确定性覆盖：危险函数、硬编码密钥、弱加密等已知模式一个不漏
- **污点追踪**补规则盲区：跟踪"外部输入 → 危险函数"的数据流，能抓到字符串拼接 SQL 注入这类规则难以描述的问题
- **LLM 研判**过滤误报：对每条候选漏洞做二次验证，给出真阳性/误报判断和修复建议

适用于：代码安全自查、CTF 代码审计题、学习 SAST 原理、小型项目的上线前安全检查。

## ✨ 核心功能

- [x] 规则引擎扫描：12+ 条内置规则（eval/exec、命令注入、不安全反序列化、硬编码密钥、弱哈希、弱随机数、TLS 关闭等）
- [x] 污点追踪分析：source（request/input/argv/环境变量）→ sink（eval/system/SQL 执行等）完整链路
- [x] LLM 智能研判：逐条验证真伪、评估等级、给出修复建议
- [x] Markdown 审计报告自动生成（含行号、代码片段、优先级排序）
- [x] Web 图形界面：深色安全大屏风格，实时显示扫描进度（规则→污点→研判），结果页含风险等级统计卡片

## 🛠️ 技术栈

- HelloAgents 框架（SimpleAgent + ToolRegistry + 自定义 Tool）
- Python AST 模块（语法树分析）
- 大模型 API（任意 OpenAI 兼容服务，开发使用 Kimi K2）

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 一个 OpenAI 兼容的 LLM API Key

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env，填入你的 LLM_API_KEY（支持 ModelScope/DeepSeek/智谱/Kimi 等）
```

### 运行项目

```bash
# 方式一：直接运行脚本（推荐）
python main.py

# 方式二：Jupyter Notebook
jupyter lab  # 打开 main.ipynb 逐格运行

# 方式三：Web 图形界面（美观大屏风格）
python web_ui.py   # 然后浏览器打开 http://127.0.0.1:8501
```

审计报告输出到 `outputs/audit_report.md`。

## 📖 使用示例

把待审计的 Python 文件放入 `data/` 目录（默认审计 `data/vulnerable_sample.py`），运行后得到如下报告片段：

```
### [3] SQL 注入（vulnerable_sample.py:20 → 23）
- 风险等级: 严重
- 研判结论: 真阳性（规则未命中，但污点链路证实）
- 代码片段: cur.execute("SELECT * FROM users WHERE id = " + uid)
- 修复建议: 改用参数化查询 ...
```

对内置示例文件（含 10 处故意埋入的漏洞）的实测结果：

| 通道 | 产出 |
|------|------|
| 规则引擎 | 10 条候选（含行号、片段） |
| 污点追踪 | 6 条完整 source→sink 链路（含规则漏掉的 SQL 注入） |
| LLM 研判 | 逐条给出真阳性/存疑判断 + 修复建议 |

## 🎯 项目亮点

- **三通道交叉验证**：规则确定性强但盲区大，LLM 灵活但易幻觉，污点追踪补数据流——三者互相补位，比任何单一手段都更接近真实审计
- **误报研判机制**：LLM 不是直接出报告，而是对工具产出做"复核"，责任清晰
- **易扩展**：新增规则只需在 `SINK_RULES` 字典加一行；source/sink 集合同理

## 🔮 未来计划

- [ ] 支持多文件/整个项目的批量审计（跨文件污点传播）
- [ ] 支持更多语言（JavaScript/Java 的规则库）
- [ ] 接入 CVE/CWE 知识库，自动关联漏洞编号
- [ ] 增加修复代码自动生成功能

## 👤 作者

- GitHub: [@smdcdz](https://github.com/smdcdz)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
