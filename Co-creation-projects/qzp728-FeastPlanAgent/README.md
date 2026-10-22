# FeastPlanAgent：宴席座次与菜单策划智能体

> 基于 HelloAgents 的可追溯宴席方案生成工具：输入人数、宾客身份、地域偏好与预算，输出一份可讨论、可核验的 Markdown 宴席计划。

## 项目简介

婚宴、商务宴等场景中，主办方通常需要同时处理宾客分桌、主位角色、地域口味、预算和场地候选。更容易被忽略的问题是：**同一批宾客、同一种宴请，在南方和北方办，座次称谓、陪席习惯、菜单结构与酒水准备不一定相同。**

FeastPlanAgent 让用户选择举办城市和希望遵循的地域偏好，检索相应的礼俗参考，再将它与名单、人数、预算和忌口一起编排为 `banquet_plan.md`。这样，系统不会把某一地的习惯当作全国通用规则，也不会只输出一份缺少地域依据的泛化菜单。

项目**不**声称替代主办方或礼宾人员，也不把旧的网络报价伪装成实时价格：每一份报告都会区分场地事实、演示/公开参考信息、规则推导建议和待确认事项。

## 核心功能

- 根据宾客人数和每桌人数计算桌数，并输出主桌与宾客桌座次；
- 为主位、主宾位、主陪位等角色给出安排理由；
- 用 Tavily 检索城市级场地套餐与当地菜单资料；没有通过来源审校时，不套用其他地区的菜单模板；
- 将餐费、酒水、服务费和备用金拆分为可复核预算；
- 深圳婚宴优先使用带来源页、采集日期、起价与桌数范围的公开婚宴目录/酒店官网缓存；地图 POI 只作补充，避免把普通酒店误当作可订婚宴场地；
- 报告附带酒店公开婚宴菜单样本（菜名、价格、来源页和采集日期），用于比较本地套餐，而不是把单一酒店菜单硬套到所有广东或河南宴席；
- 使用 HelloAgents `ToolRegistry` 注册并调度地图、网页证据、座次、地域礼俗、菜单预算工具；
- 使用 HelloAgents `SimpleAgent` 运行“场地证据研究员”和“本地菜单研究员”，再由 `ReflectionAgent` 担任证据审校员；
- 生成无前端依赖的 Markdown 报告。

## 架构

```text
需求 JSON
   ↓
BanquetPlannerAgent（协调者）
   ├─ ToolRegistry / venue_search：公开婚宴目录/酒店官网缓存，必要时高德 POI 补充
   ├─ ToolRegistry / web_evidence_search：Tavily 公开网页证据
   ├─ 场地证据研究员（SimpleAgent）
   ├─ 本地菜单研究员（SimpleAgent）
   ├─ 证据审校员（ReflectionAgent）
   ├─ seating_plan：分桌与角色座次
   └─ menu_budget：仅消费审校通过的本地菜单证据
   ↓
banquet_plan.md
```

研究员不会把搜索摘要直接写入报告：场地报价、容量、电话及菜单建议必须有原始 URL，且经过审校员复核。没有足够本地证据时，菜单区会明确停在“待确认”，而不是把广东、河南或任何其他地区的模板套进来。人数、预算和座次仍由确定性工具计算，因此可自动测试。

## 快速开始

环境：Python 3.12+（当前官方 HelloAgents 1.0.1 的要求）。

```bash
cd Co-creation-projects/qzp728-FeastPlanAgent
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

成功后会在 `outputs/banquet_plan.md` 生成报告。默认案例是深圳婚宴，但实际报告城市完全由输入 JSON 中的 `city` 和 `regional_preference` 决定。

运行测试：

```bash
python -m unittest discover -s tests -v
```

## 使用真实场地 POI

复制环境变量模板并填写自己的高德 Web 服务 Key：

```bash
cp .env.example .env
# 在 .env 中设置 AMAP_WEB_SERVICE_KEY、TAVILY_API_KEY 和 LLM_* 配置
python main.py --input data/cases/shenzhen_wedding.json
```

深圳的默认候选首先来自 `data/catalogs/shenzhen_wedding_venues.json`：每条均保留公开来源页、采集日期、起价、桌数范围和菜单套数（如果网页公开）。这不是“人工爬完再填表”，而是项目的可追溯种子目录；生产环境应以商家/平台授权的 API 或商家自维护后台定时刷新。高德 POI 用于补充地址、电话和坐标；使用前需申请 Web 服务 Key，接口说明见[高德地点搜索 2.0 文档](https://lbs.amap.com/api/webservice/guide/api/newpoisearch)。Tavily 用于检索官网、婚宴页面与当地菜单资料；它只提供候选网页，不提供“事实保证”。HelloAgents 研究员会提取候选信息，`ReflectionAgent` 会剔除无来源、来源不匹配或摘要不支持的结论。价格、档期、服务费、最低消费、开瓶费仍需向商家确认。未设置任一 Key 时，对应步骤安全降级，并会在报告中提示。

## 输入格式

参见 `data/cases/shenzhen_wedding.json`。`guest_count` 必须与 `guests` 数量一致；每位宾客最少应有 `name` 和 `role`。`city` 决定场地搜索范围，`regional_preference` 决定采用哪一份地域参考。可选字段：

- `must_with`：希望同桌的宾客姓名；
- `avoid_with`：希望避免同桌的宾客姓名；
- `seat_overrides`：可选地指定 `主位`、`主宾位`、`主陪位`、`次主宾位` 对应的姓名；它优先于任何通用礼俗推断；
- `dietary_constraints`：忌口、过敏、禁酒等；
- `venue_keyword`：例如“婚宴酒店”“商务包间”。

## 报告的边界

- “主位”等仅代表礼宾角色，实体椅位的朝向必须按现场入口、舞台和家庭习惯确认；
- 地域礼俗必须优先使用本次城市检索到、且经审校的来源；证据不足时不套用其他城市的模板；
- 任何场地报价、档期、菜单份量均需由用户与商家最终确认；
- 请仅处理主办方已获得授权的宾客信息，并避免把真实姓名和联系方式提交到公共仓库。

## 项目结构

```text
qzp728-FeastPlanAgent/
├── data/                  # 样例需求、礼俗/场地数据
├── src/                   # Agent、工具、报告渲染
├── tests/                 # 确定性逻辑测试
├── outputs/               # 生成的 Markdown 报告
├── main.py
└── main.ipynb             # Notebook 入口
```

## 作者

- GitHub: [@qzp728](https://github.com/qzp728)
