# FitHealthAgent

> 基于 HelloAgents1.0.0 的本地优先健身与健康管理智能体

## 📝 项目简介

FitHealthAgent 是一个面向个人用户的单用户 Web 应用，将 AI 对话、Garmin 健康数据、训练记录、营养估算、训练计划和肌群恢复整合在同一个本地界面中。

- **解决什么问题？** 将分散的训练记录、手表数据、每日状态、饮食信息和训练计划统一保存、查询与管理，并让智能体在回答时参考用户档案、已确认记忆、历史训练、健康限制和恢复状态。
- **有什么特色功能？** 支持 Garmin 活动 FIT 解析与训练组纠错、全天健康 ZIP/CSV 导入、餐盘照片营养估算、训练计划管理、肌群恢复计算、健康风险筛查以及完整数据备份恢复。
- **适用于什么场景？** 适合希望在个人电脑或受保护的私人服务器中管理健身健康数据，并使用 OpenAI 兼容模型辅助记录、分析和制定训练计划的用户。

项目采用“本地存储、按需联网”的方式。训练、档案、健康和记忆数据默认保存在 `data/`；AI 对话、餐盘识别和 YouTube 搜索需要访问用户配置的外部服务。当前版本没有登录认证，请勿将服务未经保护地直接暴露到公网。

> FitHealthAgent 不是医疗器械。风险筛查、恢复时间、营养估算和训练建议仅供个人健康管理参考，不能替代医生诊断、急救服务或专业指导。

## ✨ 核心功能

- [x] Garmin 训练解析：解析力量训练、有氧和其他活动 FIT，支持修改、合并、删除、撤销和恢复训练组或活动分段
- [x] 全天健康导入：导入 Garmin 健康 ZIP、健康监测 FIT 和睡眠 CSV，保存心率、睡眠、步数、压力、血氧、呼吸、HRV 和活动消耗等数据
- [x] 健身健康智能体：结合用户档案、已确认记忆、历史记录、健康限制和恢复状态进行对话、查询与训练计划生成
- [x] 每日记录与趋势：管理体重、睡眠质量、精力、疲劳、疼痛、训练完成度和营养数据，并查看健康总览与趋势
- [x] 餐盘营养估算：通过视觉模型估算食物、份量、热量、蛋白质、碳水和脂肪，支持人工修改后保存
- [x] 训练计划管理：生成、上传、保存、编辑和删除 `.md` 或 `.txt` 训练计划，并检查健康限制与恢复冲突
- [x] 肌群恢复管理：根据动作、训练容量、主次肌群、近期负荷、Garmin 恢复小时和酸痛报告估算恢复状态
- [x] 健康安全筛查：使用本地确定性规则识别可能紧急、需要尽快就医或需要谨慎处理的症状
- [x] 档案与记忆确认：长期偏好、限制和训练反馈经用户确认后写入上下文，并支持编辑、拒绝、回滚和遗忘
- [x] 本地备份恢复：备份 JSON、SQLite、Garmin 原始文件和训练心率流，并在重置或恢复前创建恢复点

## 🛠️ 技术栈

- **HelloAgents 框架**：HelloAgents 1.0.0
- **智能体范式**：ReAct（Reasoning + Acting），通过工具完成记录查询、保存和健康数据检索
- **模型接口**：OpenAI 兼容文本与视觉模型 API，默认配置示例为 DeepSeek
- **后端框架**：FastAPI、Uvicorn、Starlette
- **前端技术**：原生 HTML、CSS、JavaScript 单页应用
- **数据存储**：本地 JSON、SQLite、原始导入文件和旁挂 1 Hz 心率流
- **Garmin 解析**：`fitparse`、`fitfile`
- **外部 API**：YouTube Data API v3
- **部署方式**：Docker、Docker Compose 或 Python 3.11–3.12

## 🚀 快速开始

### 环境要求

- Python 3.11 或 3.12，推荐 Python 3.12
- 或 Docker Desktop / Docker Engine 与 Docker Compose
- 可访问所选 OpenAI 兼容模型服务
- 可选：支持图片输入的视觉模型和 YouTube Data API v3 密钥

### 安装依赖

推荐直接使用 Docker Compose，镜像构建时会自动安装锁定依赖：

```bash
docker compose build
```

使用 Python 本地运行时：

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# Linux / macOS
# source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install --require-hashes --find-links=vendor -r requirements.lock
```

`vendor/` 已附带 `hello-agents==1.0.0` wheel。请优先使用 `requirements.lock`，以安装发布验证时使用的完整依赖版本。

### 配置API密钥

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux / macOS
# cp .env.example .env

# 编辑 .env，至少配置主对话模型
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_ID=deepseek-chat

# 可选：轻量路由、计划鉴定和摘要模型
LLM_LITE_API_KEY=
LLM_LITE_BASE_URL=https://api.deepseek.com
LLM_LITE_MODE_ID=deepseek-chat

# 可选：餐盘照片识别
VISION_API_KEY=
VISION_BASE_URL=
VISION_MODEL_ID=

# 可选：YouTube 动作教学视频搜索
YOUTUBE_API_KEY=
```

完整变量见 `.env.example`。不要提交包含真实密钥的 `.env`。外部模型开关初始为开启状态，可在 Web 界面的“数据管理 → 外部模型与数据外发”中关闭。

### 运行项目

```bash
# 推荐：Docker Compose
docker compose up -d --build

# 查看运行状态
docker compose ps

# 或使用 Python 本地运行，仅监听本机回环地址
python -m uvicorn main:app --host 127.0.0.1 --port 9999
```

打开 `http://127.0.0.1:9999`。服务与存储状态可通过 `http://127.0.0.1:9999/health/storage-status` 检查，API 文档位于 `http://127.0.0.1:9999/docs` 。

Docker Compose 默认仅绑定 `127.0.0.1:9999`，并将宿主机 `./data` 挂载到容器 `/app/data`。应用目前没有登录认证；如需远程访问，必须自行配置 HTTPS、身份认证和访问控制。

## 📖 使用示例

启动后在浏览器中打开首页，可以直接对话或上传文件：

```text
用户：查看我这周的训练记录和恢复情况。
Agent：汇总近期训练，并结合肌群恢复、酸痛记录和已确认的健康限制回答。

用户：明天想练背，帮我生成一份训练计划。
Agent：检查周训练安排、历史计划、临时健康约束和恢复冲突后，生成可保存的训练计划。
```

上传 Garmin 训练文件：

```text
1. 在页面中选择或拖入 .fit 文件。
2. 应用自动判断它是活动记录还是全天健康监测文件。
3. 活动记录进入训练编辑区，可修改动作、重量、次数或活动分段。
4. 确认后保存训练，肌群恢复状态会随记录更新。
```

支持的主要上传格式和限制：

```text
.fit             Garmin 活动或健康监测，最大 50 MiB
.zip             Garmin 全天健康批量导入，最大 50 MiB
.csv             Garmin 睡眠数据，最大 2 MiB
.md / .txt       训练计划，最大 1 MiB
JPEG/PNG/WebP    餐盘照片，最大 10 MiB
```

健康批量导入每次最多选择 5 个 `.zip` 或 `.csv` 文件。餐盘照片会发送到配置的视觉模型服务，但不会保存原始图片。

## 🎯 项目亮点

- **本地优先与统一数据目录**：训练、健康、档案、记忆、计划和恢复数据统一由 `FITHEALTH_DATA_DIR` 定位，容器重建不会清空宿主机数据
- **明确的模型外发边界**：用户可关闭外部模型；关闭后本地导入、查询、训练编辑、删除和备份功能仍可使用
- **Garmin 深度集成**：区分活动 FIT 与健康监测 FIT，支持力量训练组、有氧分段、全天健康 ZIP、睡眠 CSV 和 ZIP 内活动选择
- **可追溯的训练编辑**：待确认训练持久化保存，支持撤销、恢复原始解析结果和损坏状态隔离恢复
- **肌群级恢复裁决**：综合训练容量、主次肌群、连续负荷、Garmin 恢复小时和用户酸痛报告参与计划生成
- **可靠的数据保护**：采用 JSON 原子替换与文件锁、SQLite 一致性快照、备份校验和、维护状态保护和重置前恢复点

## 📊 性能评估

当前发布版完成了功能和部署验证，尚未进行正式的并发压测或模型效果准确率评测：

- **发布包规模**：77 个文件，约 1.36 MiB，不包含依赖安装体积和个人运行数据
- **HTTP 路由**：应用装配后共 65 条路由
- **启动验证**：Docker 镜像构建成功，容器内 `/health/storage-status` 返回 HTTP 200
- **接口验证**：`/`、`/health/storage-status`、`/docs` 和 `/redoc` 均通过 HTTP 200 冒烟测试
- **部署验证**：`docker compose config` 校验通过，Python 代码编译通过
- **存储保护**：备份导入上限 1 GiB，解压总量上限 3 GiB；Garmin ZIP 还包含成员数量、单成员大小、压缩比和路径安全限制

实际响应速度主要受模型服务、网络、Garmin 文件大小和本地磁盘性能影响。生产或多人使用前应根据目标环境补充并发、长时间运行和大数据量测试。

## 🔮 未来计划

- [ ] 增加正式的模型效果评估集、端到端基准和并发性能测试
- [ ] 支持更多运动手表品牌和通用健康数据格式
- [ ] 增加训练容量、身体指标、营养和恢复的组合分析视图
- [ ] 提供可选的账号认证、HTTPS 部署方案和多用户数据隔离
- [ ] 增加跨设备同步与可选的远程备份能力
- [ ] 完善 PyPI 包数据和入口配置，提供经过验证的标准安装包

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

提交代码前请确认：

1. 不包含 `.env`、API 密钥、个人健康数据或真实备份文件；
2. 涉及数据解析、持久化、备份恢复或健康安全逻辑时补充相应测试；
3. 使用 Python 3.11 或 3.12 运行测试；
4. 保持 Docker Compose 配置和本地运行方式可用。

## 📄 许可证

MIT License，详见 [LICENSE](LICENSE)。

## 👤 作者

- GitHub: [@Malones314](https://github.com/Malones314)
- 项目链接：[fithealth-agent](https://github.com/Malones314/fithealth-agent))
- Email： zrchen314@gmail.com
## 🙏 致谢

感谢 [Datawhale](https://github.com/datawhalechina) 社区和 [HelloAgents](https://github.com/datawhalechina/hello-agents) 项目！
