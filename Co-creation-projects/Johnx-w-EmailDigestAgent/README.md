# 邮件智能摘要助手（EmailDigestAgent）

> 基于 HelloAgents 框架的智能邮件处理系统，自动获取收件箱邮件、AI 分类摘要、生成每日邮件日报，告别收件箱过载

## 📝 项目简介

每天早上打开邮箱，面对几十封未读邮件——哪些需要立即处理？哪些可以稍后阅读？哪些是垃圾信息？

**EmailDigestAgent** 解决的就是这个真实痛点。它自动获取你的收件箱邮件，通过大模型对每封邮件进行智能分类和摘要，最终生成一份结构化的「邮件日报」，让你在 5 分钟内掌握收件箱全貌。

**解决的问题：**
- 📧 收件箱邮件堆积，逐封阅读筛选耗时费力
- 🔍 重要邮件淹没在通知、促销和垃圾邮件中
- ⏰ 每天早上需要花 30-60 分钟处理邮件
- 📊 缺少对收件箱的整体视图和优先级排序

**特色功能：**
- 🤖 基于大模型的智能邮件摘要，而非简单截取前几行
- 🏷️ 自动多维度分类（工作/客户/个人/通知/垃圾）
- 📊 生成结构化的 Markdown 邮件日报
- 🔗 支持 IMAP 真实接入和模拟数据演示两种模式
- 🪶 轻量 Pipeline 设计：获取 → 分类 → 摘要 → 日报

## ✨ 核心功能

- [x] **邮件获取**：支持 IMAP 真实接入和模拟数据演示两种模式
- [x] **智能分类**：按类型和优先级自动分类
- [x] **AI 摘要**：用大模型对每封邮件生成一句话摘要，提取关键信息和待办事项
- [x] **日报生成**：结构化 Markdown 日报输出，含统计概览、分类详情、优先级排序
- [x] **模拟演示**：内置 10 封不同场景的模拟邮件，无需配置邮箱即可体验

## 🛠️ 技术栈

- **核心框架**：HelloAgents 框架（Tool 系统 + 自定义 Pipeline）
- **智能体范式**：Pipeline（获取 → 分类 → 摘要 → 日报）
- **LLM 接口**：兼容 OpenAI 格式的 API（DeepSeek / ModelScope / OpenAI 等）
- **邮件接入**：通用 IMAP 协议（QQ/163/126/Gmail/Outlook）
- **依赖库**：hello-agents, python-dotenv, rich

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Jupyter Notebook / JupyterLab
- 一个兼容 OpenAI 格式的 API Key（DeepSeek / ModelScope / OpenAI 等均可）

### 安装依赖

```bash
pip install -r requirements.txt
```

> **注意：** 如果报 `externally-managed-environment` 错误，加 `--break-system-packages` 参数，或者先创建虚拟环境（`python -m venv venv`）。

### Windows 用户额外配置

运行前在终端执行以下命令，避免中文输出乱码：

```bash
set PYTHONIOENCODING=utf-8
```

### 配置 API 密钥

```bash
# 创建 .env 文件并配置
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

### 运行项目

```bash
jupyter lab
# 打开 main.ipynb，按顺序运行所有单元格
```

## 📖 使用示例

### 演示模式（无需配置邮箱）

```python
pipeline = EmailDigestPipeline(llm=llm, use_demo=True)
report = pipeline.run()
print(report)
```

运行后输出如下日报：

```markdown
# 📬 邮件日报 - 2026-07-02

## 📊 概览
- 总邮件数: 10
- 高优先级: 3  |  中优先级: 4  |  低优先级: 3

## 🔴 高优先级
| # | 发件人 | 主题 | 类型 | 一句话摘要 |
|---|--------|------|------|-----------|
| 1 | boss@corp.com | 紧急：Q3预算确认 | 工作 | 老板要求今天内确认Q3预算方案 |
...

## 🟡 中优先级 | 🟢 低优先级 | 🗑️ 垃圾/促销
（按优先级分区展示）
```

### 真实 IMAP 接入

```python
pipeline = EmailDigestPipeline(llm=llm, use_demo=False)
report = pipeline.run(hours=24, max_emails=50)
```

## 🔧 真实邮箱配置（IMAP 通用协议）

支持 QQ邮箱 / 163 / 126 / Gmail / Outlook 等所有支持 IMAP 的邮箱。

### 启用 IMAP 并获取授权码

| 邮箱 | IMAP 服务器 | 端口 | 操作说明 |
|------|------------|------|---------|
| QQ邮箱 | imap.qq.com | 993 | 邮箱设置 → 账户 → 开启 IMAP/SMTP → 获取授权码 |
| 163邮箱 | imap.163.com | 993 | 邮箱设置 → POP3/SMTP/IMAP → 开启 IMAP → 获取授权码 |
| 126邮箱 | imap.126.com | 993 | 同 163 邮箱 |
| Gmail | imap.gmail.com | 993 | Google 账户 → 安全性 → 两步验证 → 应用专用密码 |
| Outlook | outlook.office365.com | 993 | Microsoft 账户 → 安全性 → 应用密码 |

### 配置方式（二选一）

**方式一（推荐）：** 编辑 `.env` 文件，填入 `IMAP_SERVER` / `IMAP_PORT` / `IMAP_USERNAME` / `IMAP_PASSWORD`。

**方式二：** 编辑 `config/email_config.json`，修改 `imap` 段中的对应字段。

配置完成后，`use_demo=False` 即可切换为真实模式。连接失败时会直接报错并展示原因，方便排查。

## 🎯 项目亮点

- **真实痛点驱动**：收件箱过载是每个职场人的日常困扰
- **LLM 原生摘要**：真正理解邮件内容后生成摘要，而非关键词匹配
- **Pipeline 清晰**：获取→分类→摘要→日报，四步完成
- **双重运行模式**：模拟数据演示 + 真实邮箱接入

## 🏗️ 项目结构

```
WHS-EmailDigestAgent/
├── main.ipynb              # 主 Jupyter Notebook
├── requirements.txt        # Python 依赖列表
├── README.md              # 项目说明文档
├── .env.example           # 环境变量示例
├── config/                # 配置文件目录
│   └── email_config.json  # 邮箱配置
└── output/                # 日报输出目录
```

## 🔮 未来计划

- [ ] 支持 Outlook API
- [ ] 定时任务：每日自动生成日报并推送
- [ ] 邮件趋势分析：周报/月报统计
- [ ] Web 界面展示

## 👤 作者

- GitHub: [Johnx-w (VyNox)](https://github.com/Johnx-w)
- 日期：2026-07-02

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
