# 🍳 智能菜谱助手 (Smart Recipe Agent)

> 基于 `hello_agents` 框架的多智能体协作系统，自动搜索、筛选并生成完整菜谱

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 项目简介

**智能菜谱助手** 是一个基于多 Agent 协作的菜谱搜索系统。用户只需输入饮食需求（如"我想吃小龙虾"、"适合降火的家常菜"），系统会自动：

1. 🔍 **搜索菜谱**：调用网络搜索工具获取相关菜谱列表
2. 🎯 **智能筛选**：根据用户偏好推荐最合适的菜谱
3. 📄 **内容提取**：抓取完整菜谱内容并保存为 Markdown 文件

所有生成的菜谱自动保存在 `recipes/` 目录下，方便随时查看和使用。

---

## ✨ 核心特性

- 🤖 **多 Agent 协作**：搜索专家 + 饮食专家 + 内容提取专家分工协作
- 🔗 **真实数据源**：基于香哈网等真实菜谱网站，拒绝编造信息
- 📝 **结构化输出**：推荐结果包含菜名、链接、推荐理由，清晰可读
- 💾 **自动保存**：生成的菜谱自动保存为带时间戳的 Markdown 文件
- 🔧 **可扩展架构**：基于 MCP 工具协议，易于集成新数据源

---

## 🛠️ 技术栈

| 组件 | 说明 |
|------|------|
| `hello_agents` | 多智能体编排框架 |
| `MCPTool` | Model Context Protocol 工具接口 |
| `@mzxrai/mcp-webresearch` | 网页搜索与研究工具 |
| `python-dotenv` | 环境变量管理 |
| `json/datetime` | 数据解析与文件管理 |

---

## 🚀 快速开始

### 1️⃣ 环境准备

```bash
# 克隆项目
git clone https://github.com/AstrumPush/Smart-Recipe-Agent
cd Smart-Recipe-Agent

# 安装依赖
pip install -r requirements.txt

# 安装 Node.js 环境（用于 MCP 工具）
# 访问 https://nodejs.org 下载安装

# 替换hello-agents底层代码
将本项目下的protocol_tools.py文件，替换掉hello-agents中的文件，地址如下（根据本机环境自行调整即可）：
D:\Anaconda3\envs\agents\Lib\site-packages\hello_agents\tools\builtin
```

### 2️⃣ 配置环境变量

创建 `.env` 文件：

```env
# LLM API 配置（根据实际使用的模型提供商填写）
OPENAI_API_KEY=your_api_key_here
# 或其他模型配置...
```

### 3️⃣ 运行程序

```bash
python diet_recommendation_final.py
```

### 4️⃣ 交互示例

```
请输入菜谱需求(例如：我想吃小龙虾) >>> 适合夏天吃的清淡家常菜


正在搜索菜谱...
[TOOL_CALL:visit_page:url=https://www.xiangha.com/so/?q=caipu&s=清淡家常菜]

正在筛选菜谱...
{
  "name": "清蒸鲈鱼",
  "url": "https://www.xiangha.com/caipu/xxxxx.html",
  "reason": "**推荐理由：**\n- 🐟 **清蒸烹饪** - 少油少盐...\n..."
}

正在生成菜谱...
正在保存菜谱...
✅ 菜谱已创建: recipes/recipes_20260428_153022.md
```

---

## 🧠 Agent 架构说明

```
┌─────────────────────────────────────┐
│  用户输入: "我想吃小龙虾"            │
└─────────────┬───────────────────────┘
              ▼
┌─────────────────────────────────────┐
│  🔍 caipu_search_agent              │
│  • 角色：菜谱搜索专家                │
│  • 任务：调用 web_research 工具搜索  │
│  • 输出：菜谱列表（菜名+链接+特点）  │
└─────────────┬───────────────────────┘
              ▼
┌─────────────────────────────────────┐
│  🎯 caipu_select_agent              │
│  • 角色：饮食专家                   │
│  • 任务：根据用户需求筛选最佳菜谱    │
│  • 输出：JSON 格式推荐结果           │
└─────────────┬───────────────────────┘
              ▼
┌─────────────────────────────────────┐
│  📄 output_agent                    │
│  • 角色：网页内容提取专家            │
│  • 任务：抓取完整菜谱内容            │
│  • 输出：Markdown 格式完整菜谱       │
└─────────────┬───────────────────────┘
              ▼
┌─────────────────────────────────────┐
│  💾 自动保存至 recipes/ 目录         │
└─────────────────────────────────────┘
```

---

## 📁 项目结构

```
smart-recipe-agent/
├── main.py                 # 主程序入口
├── .env                    # 环境变量配置（需手动创建）
├── recipes/                # 生成的菜谱文件目录（自动创建）
│   └── recipes_20260428_153022.md
├── requirements.txt        # Python 依赖（建议创建）
├── protocol_tools.py        # 需要修改的hello-agents代码模块
├── basic_func_test.py        # 用于验证是否可以使用web_search模块
└── README.md              # 项目说明文档
```

---

## ⚙️ 配置说明

### 工具调用格式规范

搜索 Agent 和输出 Agent 使用统一的工具调用格式：

```
[TOOL_CALL:visit_page:url=https://www.xiangha.com/so/?q=caipu&s=关键词]
```

**参数说明：**
- `visit_page`: 工具名称
- `url`: 目标网页地址，支持香哈网搜索页或具体菜谱页

### 响应解析规则

`parse_response()` 函数支持纯 JSON 字符串（含 `{}`）解析

解析失败时会输出警告并返回 `None`，主流程会进行空值检查。

---

## 🎯 使用建议

### 推荐的用户输入方式
```
✅ "适合减肥期间吃的低卡菜谱"
✅ "快手早餐，10分钟能做完的"
✅ "川菜，微辣，有鸡肉的"
✅ "适合老人吃的软烂易消化菜品"
```

### 避免的输入方式
```
❌ "随便做个菜"  # 需求过于模糊
❌ "生成一个不存在的菜"  # 系统拒绝编造信息
❌ 直接要求"写一个红烧肉做法"  # 应通过搜索获取真实菜谱
```

---

## ⚠️ 注意事项

1. **网络依赖**：程序需要联网调用 MCP 搜索工具，请确保网络通畅
2. **网站适配**：当前针对香哈网 (`xiangha.com`) 优化，更换数据源需调整 prompt
3. **API 配额**：注意 LLM 和搜索工具的调用频率限制
4. **文件权限**：确保程序有 `recipes/` 目录的写入权限
5. **错误处理**：解析失败或无匹配结果时程序会友好提示，不会崩溃

---

## 🔧 扩展开发

### 添加新数据源
修改 Agent 的 `system_prompt` 中的 URL 模板：
```python
# 示例：添加下厨房网站支持
[TOOL_CALL:visit_page:url=https://www.xiachufang.com/search/?keyword=关键词]
```

### 自定义筛选逻辑
调整 `caipu_select_agent` 的 prompt，添加个性化推荐规则：
```
- 优先推荐烹饪时间 < 30分钟的菜谱
- 排除含用户过敏食材的菜品
- 根据季节推荐当季食材菜谱
```

### 增加输出格式
修改 `write_content_to_file()` 支持更多格式：
```python
# 支持导出 PDF/HTML 等
def write_content_to_file(content, format="md"):
    ...
```

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！贡献前请：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议，可自由使用、修改和分发。

---

## 💬 反馈与支持

- 🐛 遇到问题？请提交 [Issue](https://github.com/AstrumPush/Smart-Recipe-Agent/issues)
- 💡 有新想法？欢迎开启 [Discussion](discussions)
- ⭐ 喜欢这个项目？点个 Star 支持一下！

> 🍽️ 祝您烹饪愉快，享受美食！

## 👤 作者

- GitHub: [@AstrumPush](https://github.com/AstrumPush)
- 项目链接: [Smart-Recipe-Agent](https://github.com/AstrumPush/Smart-Recipe-Agent)


## 🙏 致谢

感谢 Datawhale 社区和 [Hello-Agents](https://github.com/datawhalechina/hello-agents/) 项目！
