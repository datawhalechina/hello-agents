---
name: mx-search
display_name: 妙想资讯搜索 (MXSKILLS)
title: 妙想资讯搜索 skill
description: 本skill基于东方财富妙想搜索能力，基于金融场景进行信源智能筛选，用于获取涉及时效性信息或特定事件信息的任务，包括新闻、公告、研报、政策、交易规则、具体事件、各种影响分析、以及需要检索外部数据的非常识信息等。避免AI在搜索金融场景信息时，参考到非权威、及过时的信息。
homepage: https://dl.dfcfs.com/m/itc4
author: 东方财富妙想团队
version: 1.0.5
required_env_vars:
  - MX_APIKEY
credentials:
  - type: api_key
    name: MX_APIKEY
    description: 从东方财富妙想Skills页面获取的 API Key
---

# mx-search 妙想资讯搜索 skill

本 Skill 基于东方财富妙想搜索能力，基于金融场景进行信源智能筛选，用于获取涉及时效性信息或特定事件信息的任务，包括新闻、公告、研报、政策、交易规则、具体事件、各种影响分析、以及需要检索外部数据的非常识信息等。避免AI在搜索金融场景信息时，参考到非权威、及过时的信息。

## 功能说明

根据**用户问句**搜索相关**金融资讯**，获取与问句相关的资讯信息（如研报、新闻、解读等），并返回可读的文本内容。

## 配置

- **API Key**: 通过环境变量 `MX_APIKEY` 设置
- **默认输出目录**: `/root/.openclaw/workspace/mx_data/output/`（自动创建）
- **输出文件名前缀**: `mx_search_`
- **输出文件**:
  - `mx_search_{query}.txt` - 提取后的纯文本结果
  - `mx_search_{query}.json` - API 原始 JSON 数据

## 使用方式（直接 Python 脚本调用）

1. 需要用户在妙想Skills页面获取apikey。
2. 将apikey存到环境变量，命名为MX_APIKEY：
   ```bash
   export MX_APIKEY=your_apikey_here
   ```
3. 直接运行 Python 脚本搜索，支持自然语言问句：

```bash
# ==================== 常用调用示例 ====================

# 1. 个股相关资讯
python ./mx_search.py "东方财富最新公告"
python ./mx_search.py "贵州茅台最新研报"
python ./mx_search.py "比亚迪机构观点汇总"

# 2. 行业/板块新闻
python ./mx_search.py "人工智能板块近期新闻"
python ./mx_search.py "新能源汽车产业政策最新解读"

# 3. 宏观经济与市场分析
python ./mx_search.py "美联储加息对A股影响分析"
python ./mx_search.py "今日大盘异动原因分析"
python ./mx_search.py "北向资金最新流向解读"

# 4. 个股事件
python ./mx_search.py "贵州茅台分红派息实施公告"
python ./mx_search.py "宁德时代定增预案解读"

# 5. 交易规则
python ./mx_search.py "科创板交易涨跌幅限制"
python ./mx_search.py "新股申购规则"

# 6. 指定输出目录（可选）
python ./mx_search.py "格力电器最新研报" /path/to/output
```

   > ⚠️ **安全注意事项**
   >
   > - **外部请求**: 本 Skill 会将您的查询文本发送至东方财富官方 API 域名 ( `mkapi2.dfcfs.com` ) 以获取金融数据。
   > - **凭据保护**: API Key 仅通过环境变量 `MX_APIKEY` 在服务端或受信任的运行环境中使用，不会在前端明文暴露。

## 输出说明

脚本执行后会：
1. 在终端格式化输出搜索结果，列出每条资讯的标题、来源、日期、内容
2. 自动创建输出目录 `/root/.openclaw/workspace/mx_data/output/`
3. 保存纯文本提取结果到 `.txt` 文件
4. 保存原始 JSON 响应供二次处理

## 异常情形与处理方式

| 异常情形 | 可能原因 | 处理方式 |
|----------|----------|----------|
| **connect: Connection refused** | 网络无法访问 mkapi2.dfcfs.com | 检查服务器网络配置，确保能访问公网 |
| **401 Unauthorized / API密钥不存在** | API Key 错误或已失效 | 前往妙想Skills页面重新获取 API Key 并更新环境变量 |
| **code=113 / 今日调用次数已达上限** | 当日调用次数超限 | 前往妙想Skills页面获取更多调用次数 |
| **未找到相关资讯** | 关键词太偏门或没有最新相关信息 | 尝试更换关键词，或扩大搜索范围 |
| **返回内容为空** | 网络中断或请求超时 | 检查网络后重试 |
| **JSON解析错误** | 网络不完整导致内容截断 | 检查网络后重试 |

## 问句示例

|类型|示例问句|
|----|----|
|个股资讯|格力电器最新研报、贵州茅台机构观点|
|板块/主题|商业航天板块近期新闻、新能源政策解读|
|宏观/风险|A股具备自然对冲优势的公司 汇率风险、美联储加息对A股影响|
|综合解读|今日大盘异动原因、北向资金流向解读|

## 返回说明

|字段路径|简短释义|
|----|----|
|`title`|信息标题，高度概括核心内容|
|`secuList`|关联证券列表，含代码、名称、类型等|
|`secuList[].secuCode`|证券代码（如 002475）|
|`secuList[].secuName`|证券名称（如立讯精密）|
|`secuList[].secuType`|证券类型（如股票 / 债券）|
|`trunk`|信息核心正文 / 结构化数据块，承载具体业务数据|
