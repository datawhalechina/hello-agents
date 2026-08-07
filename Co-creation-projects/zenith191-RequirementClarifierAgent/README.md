# RequirementClarifierAgent - 多智能体需求澄清与技术方案助手

> 基于 HelloAgents 框架，把一段模糊需求转化为事实清晰、风险可见、可进入开发的需求与技术方案报告。

## 📝 项目简介

RequirementClarifierAgent 面向产品立项、软件外包和团队内部需求评审场景。用户只需提供一段原始需求，系统便会组织多个职责独立的智能体依次完成需求分析、MVP 方案设计、风险审查和报告整合。

项目重点解决以下问题：

- 将用户明确表达的事实与建议、假设、待确认项分开，避免凭空补全业务规则。
- 系统化检查目标用户、核心范围、约束、数据、非功能需求和验收标准。
- 在进入开发前暴露范围蔓延、隐私安全、可靠性、成本和进度风险。
- 生成结构固定的 Markdown 报告，便于继续评审或纳入项目文档。

### 工作流程

```mermaid
flowchart LR
    A["原始需求"] --> B["需求完整度检查工具"]
    B --> C["需求分析师"]
    C --> D["方案架构师"]
    D --> E["风险审查员"]
    E --> F["报告整合员"]
    F --> G["报告结构质检工具"]
    G --> H["Markdown 报告"]
```

## ✨ 核心功能

- [x] **需求完整度初检**：确定性扫描七类关键信息并生成澄清问题。
- [x] **多智能体协作**：四个 HelloAgents `SimpleAgent` 按职责传递中间结论。
- [x] **MVP 技术方案**：输出范围、模块、数据流、接口草案和实施节奏。
- [x] **独立风险审查**：按概率、严重度和缓解措施评估关键风险。
- [x] **报告结构质检**：检查最终 Markdown 是否包含八个规定章节。
- [x] **离线审计模式**：没有 LLM 密钥时仍可运行需求完整度检查。

## 🛠️ 技术栈

- HelloAgents 0.2.9
  - `SimpleAgent`：构建四个角色智能体
  - `HelloAgentsLLM`：连接 OpenAI 兼容的模型服务
  - `Tool`、`ToolParameter`、`ToolRegistry`：实现和注册自定义工具
- Python 3.10+
- python-dotenv
- pytest
- JupyterLab

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 一个 OpenAI 兼容的 LLM API 服务及密钥

### 安装依赖

```bash
pip install "hello-agents[all]==0.2.9"
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
# 创建 .env 文件
cp .env.example .env

# 编辑 .env，填入真实配置
```

`.env` 使用 HelloAgents 的统一配置项：

```env
LLM_MODEL_ID=Qwen/Qwen2.5-72B-Instruct
LLM_API_KEY=your_modelscope_api_key_here
LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
LLM_TEMPERATURE=0.2
LLM_TIMEOUT=120
```

请勿提交包含真实密钥的 `.env` 文件。

### 运行项目

```bash
# 运行完整多智能体流程
python main.py \
  --input data/sample_requirement.txt \
  --output outputs/requirement_report.md

# 显示各专家的中间结果
python main.py --show-intermediate

# 无需 API 密钥，只执行需求完整度检查
python main.py --audit-only
```

### 运行 Jupyter Notebook

```bash
jupyter lab
# 打开 main.ipynb 并运行全部单元格
```

Notebook 在未配置密钥时会展示仓库自带的示例报告；配置密钥后会执行真实多智能体流程。

## 📖 使用示例

示例输入位于 `data/sample_requirement.txt`：

```text
我们想做一个社区活动报名小程序。居民能浏览和报名活动，社区工作人员能发布活动并查看报名名单。希望一个月内上线，预算尽量低，预计同时在线人数不超过 100 人，主要在手机上使用。
```

运行完整流程后，将生成包含以下章节的报告：

1. 需求摘要
2. 已确认信息
3. 待确认问题
4. 范围与优先级
5. 技术方案
6. 风险与对策
7. 验收标准
8. 下一步行动

仓库内的 `outputs/requirement_report.md` 提供了完整输出示例。

## 🎯 项目亮点

- **角色隔离**：分析、设计、审查、整合分别由独立智能体负责，风险审查不会被方案设计角色弱化。
- **事实边界**：所有提示词都要求区分已确认事实、建议和待确认项。
- **确定性护栏**：在 LLM 前后分别运行完整度检查和报告结构质检。
- **可测试设计**：编排层支持注入离线替身，普通测试不依赖网络或 API 密钥。
- **单一实现来源**：CLI 和 Notebook 复用 `src/`，避免演示代码与生产逻辑漂移。

## 📊 性能评估

项目提供 30 项离线自动化测试，覆盖以下内容：

- LLM 配置缺失、占位符和边界值校验。
- 两个 HelloAgents 自定义工具的成功和错误路径。
- 四智能体调用顺序、上下文传递、异常包装和报告保存。
- CLI 无密钥审计模式。
- 官方 `SimpleAgent` 团队构建集成。
- 显式启用后才连接模型服务的真实 LLM 冒烟测试。

运行测试：

```bash
python -m pytest -q
```

配置好 `.env` 后，可显式运行真实 LLM 冒烟测试：

```bash
RUN_LIVE_TESTS=1 python -m pytest -m live -q
```

示例需求的确定性初检覆盖 5/7 个维度（71%）；仓库示例报告的结构质检得分为 100/100。LLM 生成内容受所选模型和服务状态影响，因此不虚构内容准确率。

## 🔮 未来计划

- [ ] 支持用户回答澄清问题后进行第二轮增量分析。
- [ ] 增加 JSON Schema 结构化输出与自动修复机制。
- [ ] 引入小规模标注集，评估事实/假设分类准确率。
- [ ] 支持将报告导出为 issue 或项目管理工具任务。

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request。提交改动前请运行离线测试，并确保示例数据不包含敏感信息。

## 📄 许可证

本项目遵循 Hello-Agents 仓库的 CC BY-NC-SA 4.0 License。

## 👤 作者

- GitHub：[@zenith191](https://github.com/zenith191)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目提供的教程、框架与共创平台。
