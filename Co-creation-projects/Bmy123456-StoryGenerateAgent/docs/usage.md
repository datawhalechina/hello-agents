# 使用指南

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境

复制环境变量模板并填写API密钥：

```bash
cp .env.example .env
# 编辑 .env 文件，填入OpenAI API密钥
```

### 3. 运行服务

```bash
python -m src.agent
```

服务将在 `http://localhost:8000` 启动。

## 基本用法

### 生成小说

```python
from src.agent import StoryGeneratorAgent

agent = StoryGeneratorAgent()
novel = agent.generate_novel("一个关于冒险的故事", "奇幻风格", length="中篇")
print(novel)
```

### 生成诗歌

```python
poem = agent.generate_poem("春天", "抒情诗", form="十四行诗")
print(poem)
```

### 生成剧本

```python
script = agent.generate_script("一个悬疑故事", "现代剧", genre="悬疑", scene_count=3)
print(script)
```

### 总结内容

```python
summary = agent.summarize("这是一个测试文本，用于测试总结功能。")
print(summary)
```

### 翻译内容

```python
translation = agent.translate("Hello, world!", "中文")
print(translation)
```

## API使用

### 使用FastAPI

```python
from fastapi import FastAPI
from src.api.routes import router

app = FastAPI()
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### 发送请求

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "generation_type": "novel",
    "theme": "一个关于友谊的故事",
    "style": "现实主义"
  }'
```

## 高级功能

### 自定义提示词

可以修改 `config/prompts.py` 中的提示词模板来自定义生成风格。

### 扩展生成类型

要添加新的生成类型，创建新的生成器类并继承 `BaseGenerator`：

```python
from .base import BaseGenerator

class EssayGenerator(BaseGenerator):
    def generate(self, theme, style=None, **kwargs):
        prompt = self._format_prompt(ESSAY_PROMPT, theme=theme, style=style)
        return self.llm_client.generate(prompt)
```

### 模型配置

在 `config/settings.py` 中可以配置：

- 使用的模型（gpt-4, gpt-3.5-turbo等）
- 温度参数
- 最大token数

## 调试和日志

### 启用调试模式

在 `.env` 文件中设置：

```
DEBUG=True
```

### 查看日志

日志文件位于 `logs/app.log`。

## 常见问题

### Q: 如何获取OpenAI API密钥？
A: 访问 [OpenAI官网](https://platform.openai.com/) 注册并获取API密钥。

### Q: 生成的内容不符合预期？
A: 尝试调整提示词模板或模型参数（温度、最大token数）。

### Q: 如何处理大文本？
A: 使用 `utils.text_utils.split_text()` 方法将长文本分割成多个片段。

### Q: 如何添加新的生成类型？
A: 参考 `src/generator/` 目录下的现有实现，创建新的生成器类。

## 最佳实践

1. **缓存结果**：对于重复的生成请求，考虑使用缓存。
2. **错误处理**：添加适当的错误处理逻辑。
3. **输入验证**：使用 `utils.validation` 模块验证用户输入。
4. **性能优化**：对于长文本，考虑流式生成。
5. **安全**：保护API密钥，不要硬编码在代码中。

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 许可证

本项目采用MIT许可证。