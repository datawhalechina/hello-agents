# FitnessPlannerAgent - 健身训练规划助手

> 基于HelloAgents框架的健身规划助手

## 📝 项目简介

FitnessPlannerAgent是一个健身训练规划助手,能够根据用户基本信息自动规划每周期的健身计划。

### 核心功能
- ✅ 智能建议：基于LLM和用户提供的基本信息进行分析和规划训练。


## 🛠️ 技术栈

- HelloAgents框架（SimpleAgent）
- QWEN API（智能分析）

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置LLM参数

**方式1: 使用.env文件(推荐)**

```bash
# 复制示例文件
cp .env.example .env

# 编辑.env文件,填入你的配置
# LLM_MODEL_ID=Qwen/Qwen2.5-72B-Instruct
# LLM_API_KEY=your_api_key_here
# LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
```

### 运行项目

在终端进入当项目所在的EugeneChanQAQ-smart_fitness_planner目录激活虚拟环境。

```bash
venv_fit/Scripts/activate
# 激活虚拟环境
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
# 启动项目
```

## 📖 使用示例

### 完整功能

1. 用户输入自己的基本信息（身高、体重、年龄）
2. 系统生成周期性的健身规划

## 🎯 项目亮点

- **智能化**：利用LLM根据个人身体基本数据,提供专业的健身训练建议
- **可扩展**：易于添加新的工具

## 📂 项目结构

```
EugeneChanQAQ-smart_fitness_planner/  
│  
├── app/                             # 🍱 FastAPI 服务主体   
│   ├── config.py                    # 配置文件（应用名、版本、路径等）  
│   ├── api/                         # FastAPI 相关  
│   │   ├── routers                  # 路由  
│   │   │    └──train.py             # 路由  
│   │   ├── main.py                  # FastAPI 主入口  
│   ├── agents/                      # 核心 Agent 逻辑模块  
│   │   ├── train_planner.py         #  
│   │   ├── state_manager.py         # 暂空  
│   │   ├── \_\_init__.py  
│   ├── models/                      # Pydantic 请求模型  
│   │   └── schemas.py               # 数据模型 
│   └── services/  
│       └── llm_service.py           #  
│  
├── tests/  
│   └── test_agent.py                # 暂空
│  
├── requirements.txt                 # Python依赖  
└── README.md                        # 项目说明  
```

## 🔧 技术实现


### 智能体设计

使用HelloAgents的SimpleAgent。

## 📊 示例输出

```markdown
============================================================
🚀 HelloAgents健身规划助手 v1.0.0
============================================================
应用名称: HelloAgents健身规划助手
版本: 1.0.0
服务器: 0.0.0.0:8000
LLM API Key: 已配置
LLM Base URL: https://dashscope.aliyuncs.com/compatible-mode/v1
LLM Model: qwen-max
日志级别: INFO

 ✔验证通过

============================================================
📚 API文档: http://localhost:8000/docs
📖 ReDoc文档: http://localhost:8000/redoc
============================================================

INFO:     Application startup complete.
INFO:     127.0.0.1:57008 - "GET / HTTP/1.1" 307 Temporary Redirect
INFO:     127.0.0.1:57008 - "GET /train/ HTTP/1.1" 200 OK
INFO:     127.0.0.1:57008 - "GET /favicon.ico HTTP/1.1" 404 Not Found

============================================================
📥 收到训练计划制定请求:
   身高: 183
   体重: 76
   年龄: 21
============================================================

获取Agent系统
开始初始化智能体健身规划系统
✅ LLM服务初始化成功
   提供商: qwen
   模型: qwen-max
创建健身规划Agent

============================================================
🚀 开始智能体规划训练...
身高：183
体重：76
年龄：21

============================================================
制定训练计划中...
训练规划结果: [
  {"day":1,"action":"深蹲","muscle":"腿部","group_num":3,"amount":12},
  {"day":1,"action":"卧推","muscle":"胸部","group_num":3,"amount":10},
  {"day":1,"action":"引体向上","muscle":"背部","group_num":3,"amount":8},
  {"day":2,"action":"休息"},
  {"day":3,"action":"硬拉","muscle":"背部","group_num":3,"amount":10},
  ...

============================================================
✅ 训练计划生成完成!
============================================================

✅ 训练计划生成成功,准备返回响应

INFO:     127.0.0.1:61389 - "POST /train/plan HTTP/1.1" 200 OK
```

## 🚧 未来改进

- [ ] 提供更多的基础信息以及特殊需求填写（性别、健身目的等）
- [ ] 添加食谱规划Agent（帮助提高健身效率）
- [ ] 调用API查找附近的健身餐食
- [ ] 提供周期性反馈，根据用户的最新数据更改健身策略和方案
- [ ] 生成用户身体数据报告

## 👤 作者

- GitHub: [@EugeneChanQAQ](https://github.com/EugeneChanQAQ)
- 项目链接：[FitnessPlannerAgent](https://github.com/datawhalechina/Hello-Agents/tree/main/Co-creation-projects/EugeneChanQAQ-smart_fitness_planner)

## 🙏 致谢

感谢Datawhale社区和Hello-Agents项目！

## 📄 许可证

所有共创项目遵循CC BY-NC-SA 4.0 License，欢迎学习和共创。


