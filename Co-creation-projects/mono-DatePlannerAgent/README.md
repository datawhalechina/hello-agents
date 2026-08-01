# DatePlannerAgent

> 基于高德地图开放平台 REST API 的约会行程规划智能体——真实地点、真实距离、真实天气，不编造数据。

## 📝 项目简介

- **解决什么问题？** 安排约会时，人工在多个 App 之间反复搜索餐厅、活动、距离、天气，效率低且容易漏掉“营业时间坑”“排队风险”等细节。
- **有什么特色功能？** 一条流程完成：关键词/周边搜 POI → 查详情（营业时间/人均/评分/电话）→ 算地点间距离（驾车/骑行/步行）→ 查当日天气 → 输出 8 段式结构化方案；网络请求带双后端兜底与自动重试。
- **适用于什么场景？** 个人约会规划；也可作为上层 LLM Agent（如 HelloAgents 框架）的“真实数据工具层”，让大模型基于真实 POI 而非幻觉生成方案。

## ✨ 核心功能

- [x] 高德关键词搜索 / 周边搜索，返回真实 POI（餐厅、活动、公园等）
- [x] POI 详情：地址、电话、营业时间、人均、评分（缺失字段如实标“需要确认”）
- [x] 地点间距离：驾车 / 骑行 / 步行三种方式
- [x] 城市天气查询（含多日预报）
- [x] 8 段式方案报告模板（需求总结 / 推荐方向 / 关键事实 / 路线 / 时间交通 / 待确认 / 备用 / 省流版）
- [x] 专项调研 SOP 参考（references/：餐厅、户外、电影、手工、演出、展览）
- [x] 双后端 HTTP 兜底：requests → urllib，失败自动重试
- [x] HelloAgents 框架接入：4 个自定义 Tool + ToolRegistry 注册表（demo_agent.py）

## 🛠️ 技术栈

- Python 3.10+
- 高德开放平台 Web 服务 API（Place / Geocode / Distance / Weather）
- HelloAgents 框架（ToolRegistry / Tool / HelloAgentsLLM / ReActAgent）
- 依赖：`requests` + `hello-agents`

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 高德开放平台 Web 服务 Key（[申请地址](https://console.amap.com/dev/key/app)，免费）

### 安装依赖

```bash
# 推荐：哈希锁定安装（依赖版本与安全性可复现）
python -m pip install --require-hashes -r requirements.lock

# 或使用宽松版本约束
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
cp .env.example .env
# 编辑 .env，填入你的 Key
# AMAP_KEY=your_amap_web_key_here
```

### 运行项目

```bash
# 方式一：Jupyter Notebook（推荐，演示完整流程）
jupyter lab
# 打开 main.ipynb 依次运行

# 方式二：命令行一键演示
python -m date_planner.planner "西餐厅"

# 方式三：HelloAgents 框架接入演示（无需任何 Key 也可先跑 --dry-run）
python demo_agent.py --dry-run
# 配置 LLM 后由大模型自动规划：
python demo_agent.py "帮我在北京找一家评分高的西餐厅，再查一下今天天气"
```

## 📖 使用示例

```python
from date_planner import AMapClient, DatePlanner

client = AMapClient()  # 自动读取 .env 或环境变量 AMAP_KEY

# 1. 搜索餐厅
pois = client.text_search("西餐厅", city="北京")

# 2. 查看第一个候选详情
detail = client.detail(pois[0]["id"])
print(detail.get("name"), detail.get("tel"), detail.get("rating"))

# 3. 计算两点间骑行距离
r = client.distance("116.397428,39.90923", "116.391275,39.907212", type_="2")
print(f"骑行 {r['km']} km / 约 {r['min']} 分钟")

# 4. 查天气
for c in client.weather("410400"):
    print(c["date"], c["dayweather"], c["daytemp"], "°")

# 5. 一键演示：搜索+排序+天气
DatePlanner().demo(city="北京", keywords="桌游")
```

更多用法见 `date_planner/planner.py` 的 `build_report` 与 `demo` 方法。

### HelloAgents 框架接入

```python
from date_planner.hello_tools import build_registry

registry = build_registry()          # 注册 4 个高德工具
print(registry.get_tools_description())
res = registry.execute_tool("amap_text_search", {"keywords": "西餐厅", "city": "北京"})
print(res.text)

# 配合 HelloAgentsLLM + ReActAgent 实现 LLM 自动规划，见 demo_agent.py
```

`.env` 中新增 LLM 配置项（可选）：

```bash
LLM_MODEL_ID=deepseek-chat
LLM_API_KEY=your_llm_api_key
LLM_BASE_URL=https://api.deepseek.com/v1
```

## 🎯 项目亮点

- **真实数据闭环**：所有地点/距离/天气来自高德 API，杜绝 LLM 幻觉
- **诚实标注机制**：价格、营业时间、预约等缺失信息一律标“需要确认”，不编造
- **强健网络层**：requests → urllib 双后端 + 3 次重试，弱网/SSL 异常自动切换
- **可嵌入**：既可作为独立 CLI/Notebook 使用，也可作为 LLM Agent 的工具层

## 📊 性能评估

- 单次高德请求：约 0.5~2 秒（网络正常时）
- 网络异常兜底：连续失败 3 次自动放弃并报错，不静默返回假数据
- 数据可信度：全部字段来自高德官方接口原始返回

## 🔮 未来计划

- [x] 接入 LLM Agent（HelloAgents ReActAgent + 高德工具），自动完成“需求→调研→方案”全链路（见 demo_agent.py）
- [ ] 增加预约/排队等动态信息的网页搜索核验
- [ ] 支持多城市批量方案对比
- [ ] Gradio 可视化交互界面

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@mono](https://github.com/mono)
- 本项目为 Datawhale Hello-Agents 共创项目（Co-creation）投稿

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
