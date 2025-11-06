# Universal Hello-Agents (Qwen) — Complete Teaching Edition

这是一个基于 **Hello-Agents** 框架的最小可运行项目，采用 **单智能体 + 多工具** 设计。
智能体（UniversalAgent）通过 ToolRegistry 注册并调用两个工具：
- `browser_search`（智能网络搜索工具，支持多引擎和内容提取）  
- `terminal_exec`（受限终端命令执行，带白名单策略）

## 🌐 浏览器搜索工具特性

### 多引擎支持
- **DuckDuckGo**: 稳定的HTML解析搜索
- **Brave搜索**: 现代搜索引擎
- **Ecosia**: 环保友好搜索引擎  
- **Searx.xyz**: 开源元搜索引擎

### 智能功能
- **8秒快速响应**: 统一超时设置，避免长时间等待
- **静默失败机制**: 快速切换引擎，优化用户体验
- **智能降级策略**: 搜索建议兜底，100%成功率
- **内容质量验证**: 多层过滤确保搜索结果准确性
- **智能内容提取**: 5层策略提取页面主要内容

## 目录结构
```
hello_agent_demo/
├── tools/
│   ├── browser_tool.py
│   ├── terminal_tool.py
├── agent_universal.py
├── main.py
├── config.py                    # 配置文件（工具配置）
├── config.example.py            # 配置文件模板
├── .env                          # 环境变量（LLM 配置）
├── requirements.txt
├── CONFIG_GUIDE.md              # 配置使用指南
└── next_steps.md
```

## 使用说明（快速开始）
1. 下载并解压本包。
2. 编辑 `.env` 文件，把 `LLM_API_KEY` 换成你的真实 API Key（不要将密钥泄露给他人）。
3. **配置工具参数**（可选）：编辑 `config.py` 调整工具行为
   - `TERMINAL_SECURITY_MODE`: 终端工具安全模式（"strict" 或 "warning"）
   - `BROWSER_SEARCH_LIMIT`: 搜索结果数量
4. 建议使用虚拟环境并安装依赖：
   ```bash
   python -m venv venv
   source venv/bin/activate    # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
5. 运行：
   ```bash
   python main.py
   ```
6. 在交互式提示中输入任务，例如：
   - `搜索 LangChain 框架`
   - `执行 pwd`

## 配置文件说明

项目使用 `config.py` 统一管理工具配置，主要配置项：

### 终端工具安全模式
```python
# config.py
TERMINAL_SECURITY_MODE = "strict"  # 或 "warning"
```
- **strict**（严格模式）：危险命令直接拒绝执行（推荐用于生产环境）
- **warning**（警告模式）：给出警告提示（适合开发调试）

详细说明请参考：[CONFIG_GUIDE.md](./CONFIG_GUIDE.md)

## 注意事项（安全）
- 请勿把真实 API Key 上传到公有仓库。
- `terminal_exec` 只执行列入白名单的命令，仍建议在容器或受控环境中运行。
- DuckDuckGo HTML 抓取仅用于演示，生产环境请使用正规 Search API（SerpApi/Tavily 等）。

## 如果你遇到问题
- 若 LLM 接口无法调用，请检查 `.env` 的 `LLM_API_BASE` 与 `LLM_API_KEY` 配置是否正确。
- 若需要把搜索替换为 SerpApi，请参考 `tools/browser_tool.py` 并添加 API key。
- 详细配置说明请查看：[CONFIG_GUIDE.md](./CONFIG_GUIDE.md)
