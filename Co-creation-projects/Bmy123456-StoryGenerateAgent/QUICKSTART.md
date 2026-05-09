# 快速启动指南

## 环境准备

### 1. 安装依赖
```bash
pip install openai pydantic fastapi uvicorn python-dotenv requests
```

### 2. 配置环境变量
编辑 `.env` 文件：
```env
OPENAI_API_KEY=your_api_key_here
BASE_URL=https://open.bigmodel.cn/api/paas/v4
MODEL_NAME=glm-4.5-air
TEMPERATURE=0.7
MAX_TOKENS=1000
```

## 快速开始

### 运行Jupyter Notebook
```bash
jupyter notebook main.ipynb
```

### 直接使用智能体
```python
from src.agent import StoryGeneratorAgent

# 创建智能体
agent = StoryGeneratorAgent()

# 生成小说
novel = agent.generate_novel("友谊的故事", "现实主义")
print(novel)

# 生成诗歌
poem = agent.generate_poem("春天", "抒情诗")
print(poem)

# 生成剧本
script = agent.generate_script("悬疑故事", "现代剧", genre="悬疑")
print(script)
```

## 支持的模型

- **智谱AI**: GLM-4.5
- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude系列
- **Google**: Gemini系列
- **其他**: 兼容OpenAI接口的模型

## 注意事项

1. 确保已设置正确的API密钥
2. 根据使用的模型调整BASE_URL
3. 首次运行可能需要较长时间