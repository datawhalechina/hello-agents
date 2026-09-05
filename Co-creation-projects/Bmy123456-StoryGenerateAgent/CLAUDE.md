# CLAUDE.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。

## 项目概述

故事生成器智能体 - 一个支持多种大语言模型的内容生成系统，可以生成小说、诗歌和剧本。支持智谱AI（GLM-4.5）、OpenAI、Anthropic Claude 和 Google Gemini，通过统一接口调用。

## 常用命令

### 运行演示
```bash
# 快速演示脚本（测试所有生成类型）
python run_demo.py

# Jupyter Notebook 交互式演示
jupyter notebook main.ipynb
```

### 运行测试
```bash
# 运行所有测试
python run_tests.py

# 使用 pytest 运行
python -m pytest tests/ -v
```

### 启动 API 服务
```bash
python start_server.py
```

### 环境检查
```bash
python test_import.py
```

## 架构说明

### 核心模块

**`src/agent.py`** - 主入口点。`StoryGeneratorAgent` 类协调所有内容生成：
- `generate_novel(theme, style, **kwargs)` - 小说生成
- `generate_poem(theme, style, **kwargs)` - 诗歌生成
- `generate_script(theme, style, **kwargs)` - 剧本生成
- `summarize(content)` - 内容总结
- `translate(content, language)` - 文本翻译

**`src/models/llm_client.py`** - 多模型客户端，自动检测API类型：
- 根据 `BASE_URL` 自动识别API类型（zhipu/openai/anthropic/google）
- 自动处理不同API的请求/响应格式
- 支持流式输出：`stream_generate()`
- 非OpenAI API使用 `requests`，OpenAI使用 `openai` SDK

**`src/generator/`** - 内容生成器：
- `base.py` - 抽象基类 `BaseGenerator`
- `novel.py` - `NovelGenerator`（max_tokens=2000）
- `poem.py` - `PoemGenerator`（max_tokens=500）
- `script.py` - `ScriptGenerator`（max_tokens=1500）

**`config/settings.py`** - Pydantic配置，兼容v1和v2：
- 兼容 pydantic v1（`BaseSettings`）和 v2（`pydantic_settings`）
- 从 `.env` 文件加载配置

**`config/prompts.py`** - 各类型生成的提示词模板

### 导入模式

代码库中广泛使用回退导入（fallback imports）。当从 `config` 导入失败时，会回退到环境变量和默认提示词。这是为了Jupyter Notebook的兼容性。

## 配置说明

### `.env` 文件
```env
OPENAI_API_KEY=你的API密钥
BASE_URL=https://open.bigmodel.cn/api/paas/v4  # 或OpenAI默认地址
MODEL_NAME=glm-4.5-air
TEMPERATURE=0.7
MAX_TOKENS=1000
```

### 支持的模型
- 智谱AI: `glm-4.5-air`（默认配置）
- OpenAI: `gpt-4`、`gpt-3.5-turbo`
- Anthropic: Claude系列
- Google: Gemini系列

## 重要注意事项

- **Pydantic v2 兼容性**: `config/settings.py` 同时兼容 pydantic v1 和 v2。如果使用 pydantic v2，请确保安装 `pydantic-settings`。
- **调试输出**: `llm_client.py` 中的 `_make_request()` 方法当前包含调试打印语句，排查问题后可移除。
- **编码问题**: 在Windows GBK编码下，print语句中避免使用Unicode表情符号（如 ✓、❌），或设置 `PYTHONIOENCODING=utf-8`。
- **路径处理**: 项目通过多个文件将根目录添加到 `sys.path` 来解决导入问题。
