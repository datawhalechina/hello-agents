# 故事生成器智能体项目结构

## 项目概述
这是一个基于AI的故事生成器智能体，可以根据用户输入生成小说、诗歌、剧本等多种文本内容。

## 项目结构

```
story-generator-agent/
├── README.md                 # 项目说明文档
├── requirements.txt          # Python依赖
├── .env                      # 环境变量配置
├── .gitignore                # Git忽略文件
├── config/                   # 配置文件目录
│   ├── __init__.py
│   ├── settings.py           # 主配置
│   └── prompts.py           # 提示词模板
├── src/                      # 源代码目录
│   ├── __init__.py
│   ├── agent.py             # 智能体主类
│   ├── generator/           # 生成器模块
│   │   ├── __init__.py
│   │   ├── base.py          # 基础生成器类
│   │   ├── novel.py         # 小说生成器
│   │   ├── poem.py          # 诗歌生成器
│   │   └── script.py        # 剧本生成器
│   ├── models/              # 模型管理
│   │   ├── __init__.py
│   │   ├── llm_client.py    # LLM客户端
│   │   └── model_config.py  # 模型配置
│   ├── utils/               # 工具函数
│   │   ├── __init__.py
│   │   ├── text_utils.py    # 文本处理工具
│   │   └── validation.py    # 输入验证
│   └── api/                 # API接口
│       ├── __init__.py
│       ├── routes.py        # 路由定义
│       └── schemas.py       # 数据模型
├── tests/                   # 测试目录
│   ├── __init__.py
│   ├── test_agent.py
│   ├── test_generator.py
│   └── test_models.py
├── data/                    # 数据目录
│   ├── prompts/             # 提示词模板
│   └── examples/            # 示例输出
└── docs/                    # 文档目录
    ├── api.md              # API文档
    └── usage.md            # 使用指南
```

## 核心模块说明

### 1. 配置模块 (config/)
- `settings.py`: 主配置文件，包含API密钥、模型参数等
- `prompts.py`: 不同生成类型的提示词模板

### 2. 智能体核心 (src/agent.py)
- 主智能体类，协调各个模块的工作
- 处理用户输入和输出

### 3. 生成器模块 (src/generator/)
- `base.py`: 基础生成器类，定义通用接口
- `novel.py`: 小说生成器实现
- `poem.py`: 诗歌生成器实现  
- `script.py`: 剧本生成器实现

### 4. 模型管理 (src/models/)
- `llm_client.py`: LLM客户端，处理与AI模型的通信
- `model_config.py`: 模型配置管理

### 5. API接口 (src/api/)
- `routes.py`: 定义API路由
- `schemas.py`: 数据验证模型

## 快速开始

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 配置环境变量：
```bash
cp .env.example .env
# 编辑 .env 文件，填入API密钥
```

3. 运行智能体：
```bash
python -m src.agent
```

## 扩展功能

- 添加新的生成类型：在 `src/generator/` 下创建新的生成器类
- 支持更多模型：在 `src/models/` 下扩展模型支持
- 增加缓存：在 `src/utils/` 下添加缓存逻辑
- 添加持久化：在 `data/` 目录下管理生成的内容

这个结构提供了良好的模块化设计，便于维护和扩展。