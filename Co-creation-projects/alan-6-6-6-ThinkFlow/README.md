# ThinkFlow - AI 思维教练

> 基于 HelloAgents 框架的智能思维拆解工具，帮助你从混沌走向清晰

## 📝 项目简介

ThinkFlow 是一款 AI 思维教练，通过"黄金三角"方法论引导用户完成"从混沌到清晰"的思考旅程。

**解决的问题：**
- 思绪混乱、不知从何下手
- 目标模糊、难以拆解
- 选择困难、决策焦虑

**核心价值：**
- 将咨询公司的专业工具（麦肯锡 MECE、WBS、决策矩阵）融入 AI
- 通过提问引导用户主动思考，而非直接给答案
- 支持递归式决策跳转，符合真实项目管理逻辑

## ✨ 核心功能

- [x] **澄清期（ClarifyAgent）**：黄金圈法则挖掘真实动机，5W1H 界定问题边界
- [x] **拆解期（DecomposeAgent）**：WBS 工作分解结构，将大目标拆解为可执行任务
- [x] **决策期（DecideAgent）**：决策矩阵，多维度评估选项
- [x] **MECE 校验**：确保拆解相互独立、完全穷尽
- [x] **递归跳转**：Decompose 阶段遇二选一场景可返回 Decide 阶段

## 🛠️ 技术栈

- **框架**：HelloAgents（SimpleAgent + 多智能体架构）
- **LLM**：DeepSeek（deepseek-v4-flash）
- **方法论**：黄金圈法则、5W1H、WBS、决策矩阵、MECE 原则
- **状态管理**：上下文快照 + 决策回传协议

## 🚀 快速开始

### 环境要求

- Python 3.10+
- hello-agents >= 0.2.7

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 LLM

```bash
# 创建 .env 文件
cp .env.example .env

# 编辑 .env 文件，配置 DeepSeek API
```

### 运行项目

```bash
jupyter lab
# 打开 main.ipynb 并运行所有单元格
```

## 📖 核心设计

### 黄金三角模型

```
用户需求
    ↓
澄清期（Clarify）──→ 决策期（Decide）──→ 拆解期（Decompose）
    (黄金圈+5W1H)        (决策矩阵)          (WBS分解)
          ↓                   ↓                   ↓
        定义目标           选择路径           执行任务
```

### 三智能体架构

| 智能体 | 角色 | 核心任务 | 输入 | 输出 |
|--------|------|----------|------|------|
| **ClarifyAgent** | 认知脚手架工程师 | 挖掘动机，界定边界 | 用户模糊需求 | 明确定义的目标+约束条件 |
| **DecideAgent** | 理性决策教练 | 多维度评估选项 | 选项列表 | 唯一优选方案 |
| **DecomposeAgent** | 结构化架构师 | WBS 任务分解 | 目标或方案 | 可执行任务列表 |

### 递归调用机制

当 Decompose 阶段检测到互斥选项时：
1. 自动冻结当前 WBS 状态
2. 生成标准化决策请求传递给 DecideAgent
3. DecideAgent 返回携带路径标识的方案
4. DecomposeAgent 精准续接分解

## 🎯 项目亮点

- **方法论驱动**：将麦肯锡、BCG 等顶级咨询公司的工具固化为 AI 能力
- **状态机设计**：支持动态跳转，符合真实项目管理逻辑
- **MECE 校验**：确保拆解的完整性和独立性
- **教练语气**：通过提问引导，而非直接给出答案

## 📊 测试用例

### 测试环节 A：ClarifyAgent（问题澄清）
**输入**："老板让我提升用户留存，我不知道从哪下手。"
**预期输出**：通过黄金圈和 5W1H 追问，收敛到具体目标

### 测试环节 B：DecomposeAgent（结构拆解）
**输入**："策划一场公司年会"
**预期输出**：WBS 层级分解，识别潜在决策点

### 测试环节 C：DecideAgent（决策收敛）
**输入**："自研风控系统 vs 接入第三方SDK"
**预期输出**：决策矩阵对比，输出优选方案

## 🔮 未来计划

- [ ] 可视化思维导图输出
- [ ] 支持多人协作模式
- [ ] 增加更多思维工具（SWOT、SCAMPER）
- [ ] Web 界面开发

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@alan-6-6-6](https://github.com/alan-6-6-6)
- 项目链接: [ThinkFlow](https://github.com/datawhalechina/hello-agents/tree/main/Co-creation-projects/alan-6-6-6-ThinkFlow)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
