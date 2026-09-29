# StudentConfideAgent · 心语倾诉助理

> 面向学业压力较大的学生，提供合法合规的倾诉型 AI Bot；每位使用者逐步拥有自己的专属 Agent。

## 📝 项目简介

学生阶段学业与人际压力往往不小，和父母沟通又容易卡住——不是不想说，而是不知道怎么开口、怕被误解、或一时找不到合适的倾诉对象。

本项目希望做一个**轻量、可控、合规**的倾诉入口：

- **现阶段不做复杂平台扩展**（不做社交广场、不做大规模社区运营）
- **仅提供一个 Bot 助理**，在合法合规边界内陪伴倾听、疏导表达、协助整理情绪与学业困扰
- **每位使用者逐步拥有自己的专属 AI Agent**：通过会话记忆与个人偏好沉淀，让回复越来越贴近「这个人」，而不是千人一面的通用客服话术

> 重要声明：本助理**不是心理医生或医疗机构**，不提供诊断、开药或危机干预替代服务。若涉及自伤、伤人等紧急情况，应引导用户寻求现实中的专业帮助与紧急热线。

## ✨ 核心功能

- [x] **倾诉对话 Bot**：自然语言倾听与共情回应（学业压力、亲子沟通卡顿、情绪倾诉等）
- [x] **合规安全护栏**：敏感话题识别、拒答越界请求、危机场景转介提示
- [x] **专属 Agent 成长**：按用户 ID 隔离记忆，逐步形成个人风格与上下文连续性
- [ ] **情绪/主题小结**（规划中）：一句话总结本次倾诉主题，便于用户复盘
- [ ] **可选本地笔记**（规划中）：用户主动保存的「想对父母说的话」草稿（仅本人可见）

## 🛠️ 技术栈

- **HelloAgents 框架**（`SimpleAgent` / `ToolAwareSimpleAgent`、记忆与笔记能力）
- **智能体范式**：以对话式 Agent 为主；需要结构化整理时可组合 Reflection / 简单 Plan
- **记忆**：按 `user_id` 写入本地 `data/memory/`（跨会话长期记忆，演示无需 Qdrant / Neo4j）；配置好 LLM 后，同一用户再接入 HelloAgents `MemoryTool(memory_types=["working"])` 作为当次会话的工作记忆
- **安全**：对话进入模型前先走确定性护栏（危机转介、拒绝诊断开药、拒绝违法与色情请求）
- **运行形态**：Jupyter Notebook（`main.ipynb`）优先；后续可扩展为轻量 Web（可选）

## 📁 推荐项目结构

```
neil43lk-StudentConfideAgent/
├── README.md                 # 本说明文档
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── .gitignore
├── main.ipynb                # 主演示 Notebook
├── data/                     # 示例对话 / 安全策略（真实记忆不入库）
│   ├── sample_dialogues.json
│   ├── safety_policy.md
│   └── memory/               # 运行后按 user_id 生成，已 gitignore
├── outputs/                  # 运行输出
│   ├── session_summary.md
│   └── screenshots/
└── src/
    ├── agents/
    │   └── confide_agent.py  # 倾诉助理 Agent
    ├── memory/
    │   └── user_agent_store.py  # 用户专属记忆隔离
    ├── safety/
    │   └── guardrails.py     # 合规与危机转介
    └── utils/
```

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 可用的 LLM API（推荐 DeepSeek / 通义等 OpenAI 兼容接口）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_MODEL_ID / LLM_API_KEY / LLM_BASE_URL
```

示例：

```env
LLM_PROVIDER=auto
LLM_MODEL_ID=deepseek-chat
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.deepseek.com
LLM_TIMEOUT=60

# 专属 Agent：用于隔离不同使用者的记忆命名空间
DEFAULT_USER_ID=demo_student_001
```

### 运行项目

```bash
# 启动 Jupyter
jupyter lab
# 或：jupyter notebook

# 打开并运行 main.ipynb
```

未配置密钥时，Notebook 仍可演示安全护栏、两位用户的记忆隔离，以及本地会话小结。`chat()` 不会编造倾听回复；配好 `.env` 后再走大模型。

## 📖 使用示例

```python
from src.agents.confide_agent import create_confide_agent

# 每位使用者对应独立 user_id → 逐步形成专属 Agent
agent = create_confide_agent(user_id="student_xiaoming")

reply = agent.chat("最近考试压力好大，又不知道怎么跟爸妈说……")
print(reply)
```

预期体验：

1. Bot 先倾听与共情，不急于说教  
2. 帮助梳理「想表达的感受 / 担心被误解的点 / 可以尝试的沟通方式」  
3. 记住该用户过往倾诉主题（在合规与隐私约束下），后续对话更「懂你」  
4. 若触及危机相关表述，给出明确转介提示，而不是继续闲聊式回应  

## 🎯 项目亮点

- **问题真实**：对准「学业压力 + 亲子沟通不畅」的学生场景，而不是空泛聊天 Bot  
- **范围克制**：明确「暂不扩展平台」，先把单 Bot、合规、专属记忆做扎实  
- **专属 Agent**：不是一次会话结束就清空，而是按使用者沉淀可延续的个人助理  
- **合规优先**：安全护栏与免责声明写进产品边界，避免「伪心理咨询」风险  

## ⚖️ 合规与使用边界

本项目在设计与演示中需遵守以下原则：

1. **不做医疗/心理诊断**，不替代专业咨询或治疗  
2. **危机场景**：识别到自伤、伤人等风险时，停止普通闲聊模式，提示寻求线下专业帮助与紧急渠道  
3. **隐私最小化**：演示数据本地化；不默认上传敏感个人信息；文档中禁止提交真实 `.env` / 真实个案  
4. **内容合法**：拒绝违法、暴力教唆、色情等违规请求  
5. **年龄与场景**：定位为学生倾诉助理 Demo，正式对外服务前需补充更完整的合规评估  

## 📊 性能评估（规划）

可通过小样本对话集做人工评测（后续补齐）：

- 共情与倾听质量（1–5 分人工打分）  
- 是否越界提供「诊断/处方」类不当建议（越界率）  
- 危机转介触发是否及时、准确  
- 专属记忆是否提升跨会话连贯性（有记忆 vs 无记忆对照）  

## 🔮 未来计划

- [ ] 完善安全护栏与评测集  
- [x] Notebook 演示「新用户 → 多轮倾诉 → 专属记忆生效」（无密钥时可离线验证隔离；有密钥时生成倾听回复）  
- [ ] 可选：极简 Web 聊天页（仍保持单 Bot，不做社区）  
- [ ] 可选：用户主导的「想对父母说的话」草稿生成（可编辑、可删除）  
- [ ] **不做**：社交匹配、公开动态、未授权的家长侧监控  

## 🤝 贡献指南

欢迎提出 Issue 与 Pull Request。涉及安全策略与危机话术的改动，请优先说明测试用例与边界说明。

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@neil43lk](https://github.com/neil43lk)
- 项目路径（共创仓库）：`Co-creation-projects/neil43lk-StudentConfideAgent`

## 🙏 致谢

感谢 Datawhale 社区与 Hello-Agents 项目！  
本 README 结构参考第十六章毕业设计文档及共创项目实践经验。
