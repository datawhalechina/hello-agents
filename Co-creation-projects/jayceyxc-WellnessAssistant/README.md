# Wellness Assistant Agent
> 基于 Hello-Agents 框架实现的个人健康管理智能体，支持自然语言记录健康数据、生成并动态调整运动方案、健康复盘

## 📝 项目简介
本项目是一款面向个人健康管理的AI Agent应用，区别于传统固定表单类健康软件和普通大模型问答程序。
- 解决问题：传统健康工具缺少自主规划能力，通用大模型缺少长期健康记忆、无法稳定调用业务工具，给出的运动方案不能跟随用户身体状态动态调整。
- 特色功能：智能体自带工具调用、长期记忆、反思复盘能力，用户以自然语言交互，完成健康记录、个性化运动规划、健康状态复盘。
- 适用场景：个人日常健康指标追踪、减脂/康复运动管理、居家健康自我监测。

> 免责声明：本项目仅作为健康辅助工具，**不具备医疗诊断能力，输出内容仅供参考，不能替代专业医师诊疗**。

## ✨ 核心功能
- [ ] 自然语言对话交互：通过对话录入健康指标、查询健康相关建议
- [ ] 健康台账管理：持久化存储健康记录，支持指标趋势可视化查看
- [ ] 个性化运动方案生成：根据用户基础信息、健康目标生成适配的运动计划
- [ ] 运动计划动态调整：接收用户身体反馈，自动修改训练强度与内容
- [ ] 简易健康评估与定期复盘：结合历史数据给出健康提示、周期性健康总结
- [ ] Agent 调用链路追踪：可视化查看智能体思考、工具调用全过程

## 🛠 技术栈
- HelloAgents 框架
- 智能体范式：ReAct（思考-行动）范式
- 后端：Python + FastAPI + SQLAlchemy + SQLite
- 前端：Vue3 + Element Plus + ECharts
- LLM 支持：Ollama（本地离线）、主流大模型API
- 其他依赖：python-dotenv、pydantic

## 🚀 快速开始
### 环境要求
- Python 3.10+
- Node.js 18+（前端编译）
- Ollama（可选，本地部署大模型）

### 后端安装依赖
```bash
pip install -r requirements.txt
```

### 配置API密钥
```bash
# 创建.env文件
cp .env.example .env
# 编辑.env文件，填入大模型API密钥或者Ollama服务地址
```

### 启动后端服务
```bash
python main.py
```

### 启动前端
```bash
cd frontend
npm install
npm run dev
```
前端默认运行在 `http://localhost:5173`，Vite 会将 `/api` 请求代理到后端 `http://127.0.0.1:8000`。

### 运行后端测试
```bash
python -m pytest -q tests
```

### 当前实现进度
- 已完成：FastAPI 骨架、SQLAlchemy/SQLite 数据模型、HelloAgents ReAct 智能体、健康台账、运动计划生成与版本化调整、长期记忆、健康复盘、Trace 持久化及 REST API（架构文档阶段一~四）。
- 已生成待验证：Vue3 + Element Plus + ECharts 四个页面（对话、指标趋势、运动计划、Agent 链路），需先安装前端依赖并启动 Ollama / 在线 LLM 服务后联调。
- 后端接口：`POST /api/chat`、`GET /api/chat/history`（恢复会话记录）、`GET /api/health`、`GET /api/health/records`、`GET /api/health/trends`、`GET /api/plans/current`、`GET /api/plans/{plan_id}/versions`、`GET /api/traces/{trace_id}`。
- 交互式 API 文档：启动后端后访问 `http://127.0.0.1:8000/docs`。

## 📖 使用示例
1. 用户通过对话发送指令：`帮我记录今天体重、睡眠情况，并生成一份减脂运动计划`
2. Agent 自主判断，调用健康记录工具保存数据，调用运动规划工具生成方案
3. 用户反馈：`训练后身体不适，请降低计划强度`
4. Agent 读取历史健康记录，调用计划更新工具，动态调整运动方案
5. 在Trace面板查看智能体的思考链路与工具调用日志

## 🎯 项目亮点
- 基于标准ReAct智能体范式，不是简单的大模型Prompt套壳，具备自主工具决策能力
- 支持长期健康记忆，智能体可以记住用户历史健康基线，方案更贴合个人情况
- 运动方案支持动态迭代，根据用户身体反馈持续调整，而非一次性静态方案
- 部署灵活：支持Ollama本地离线大模型，也可对接在线LLM API，演示友好
- 前后端分离架构，Vue前端提供可视化页面，包含数据图表、Agent追踪面板

## 📊 性能评估
> 本项目为学习演示型Agent项目，暂无大规模定量评估
- 工具调用成功率：在测试场景下稳定
- 平均响应时间：取决于选用的大模型服务

## 🔮 未来计划
- [ ] 接入第三方健康设备接口，自动同步心率、睡眠数据
- [ ] 增加饮食记录与膳食推荐工具
- [ ] 优化向量长期记忆检索能力
- [ ] 增加多用户隔离与权限管理

## 🤝 贡献指南
欢迎提出 Issue 和 Pull Request！

## 📄 许可证
MIT License

## 👤 作者
- GitHub: [@jayceyxc](https://github.com/jayceyxc)
- Email: jayce123@163.com

## 🙏 致谢
感谢Datawhale社区和Hello-Agents项目！
