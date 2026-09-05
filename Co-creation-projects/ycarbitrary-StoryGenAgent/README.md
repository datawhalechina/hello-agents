# StoryGenAgent: 基于千问的多智能体故事生成器

## 项目简介

`ycarbitrary-StoryGenAgent` 是一个基于千问大模型的多智能体故事生成器。项目通过多个 Agent 的分工协作，将用户输入的故事主题、风格、篇幅、主角设定和结局倾向，逐步扩展为完整的 Markdown 故事文本。

```bash
hello-agents/Co-creation-projects/ycarbitrary-StoryGenAgent
```

项目默认使用 DashScope 千问 OpenAI 兼容接口，也支持切换到本地部署的 Qwen/OpenAI 兼容模型。

## 核心功能

- 根据用户需求生成故事标题、世界观、主线冲突和章节大纲
- 自动生成主角、配角、反派以及人物关系
- 按章节生成故事正文，保持角色设定和情节连续性
- 使用记忆管理器保存世界观、角色设定和章节摘要
- 通过编辑 Agent 进行润色、逻辑检查和故事评分
- 将最终结果导出为 `outputs/generated_story.md`

## 技术栈

- Python
- Jupyter Notebook
- OpenAI Python SDK
- DashScope 千问 OpenAI 兼容接口
- python-dotenv
- rich
- markdown

## 项目结构

```bash
ycarbitrary-StoryGenAgent/
├── README.md
├── requirements.txt
├── main.ipynb
├── prompts/
│   ├── planner_prompt.txt
│   ├── character_prompt.txt
│   ├── writer_prompt.txt
│   └── editor_prompt.txt
├── outputs/
│   └── generated_story.md
└── .env.example
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置千问模型环境变量

复制环境变量示例文件：

```bash
cp .env.example .env
```

在 `.env` 中填写你的 DashScope API Key：

```env
OPENAI_API_KEY=your_dashscope_api_key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen-plus
```

API Key 不要写死在代码里，也不要提交到公开仓库。

你可以根据需求切换模型：

```env
MODEL_NAME=qwen-turbo
MODEL_NAME=qwen-plus
MODEL_NAME=qwen-max
```

如果使用本地部署的 Qwen 模型，例如 Ollama、vLLM 或 LM Studio，只需要改为本地 OpenAI 兼容接口：

```env
OPENAI_API_KEY=your_local_api_key
OPENAI_BASE_URL=http://localhost:8000/v1
MODEL_NAME=qwen
```

### 3. 运行 Notebook

```bash
jupyter notebook main.ipynb
```

按顺序执行 Notebook 中的单元格即可生成故事。执行完成后，最终结果会保存到：

```bash
outputs/generated_story.md
```

## 使用示例

```python
user_requirement = """
主题：赛博朋克城市里的少年侦探
风格：悬疑、热血、轻小说
篇幅：3章
主角：林川，17岁，擅长黑客技术
结局倾向：反转
目标读者：喜欢科幻和推理的年轻读者
"""

final_story = generate_story(user_requirement, chapter_count=3)
```

## Agent 工作流程

1. `StoryPlannerAgent`：生成标题、类型、世界观、主线冲突和章节大纲。
2. `CharacterAgent`：根据故事大纲生成角色设定和人物关系。
3. `MemoryManager`：保存世界观、角色设定和已生成章节摘要。
4. `WriterAgent`：结合记忆上下文，逐章生成故事正文。
5. `summarize_chapter`：为每章生成简短摘要，更新记忆。
6. `EditorAgent`：润色全文，检查逻辑，并从剧情完整度、人物塑造、风格一致性、可读性和反转亮点评分。
7. `save_story_to_markdown`：将故事大纲、角色设定、正文和编辑评分导出为 Markdown。

## 输出示例

运行成功后，`outputs/generated_story.md` 会包含以下内容：

- 用户原始需求
- 故事策划结果
- 角色设定
- 分章节正文
- 编辑润色版本
- 多维度评分和优化建议

## 后续优化方向

- 增加 Web UI 或 Streamlit 前端
- 支持用户在章节生成后进行人工反馈和二次改写
- 增加更多专业 Agent，例如伏笔检查 Agent、风格模仿 Agent、分镜 Agent
- 支持长篇故事的向量数据库记忆管理
- 支持导出为 PDF、HTML 或电子书格式

## 作者信息

GitHub：【ycarbitrary】（<https://github.com/ycarbitrary>）\
Email：<tiger123yfq@gmail.com>

## 🙏 致谢&#x20;

&#x20;感谢Datawhale社区和Hello-Agents项目！
