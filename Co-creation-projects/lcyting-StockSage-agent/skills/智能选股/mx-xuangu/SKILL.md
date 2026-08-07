---
name: mx-xuangu
display_name: 妙想智能选股 (MXSKILLS)
title: 妙想智能选股 skill
description: 本 Skill 支持基于股票选股条件，如行情指标、财务指标等，筛选满足条件的股票；可查询指定行业 / 板块内的股票、上市公司，以及板块指数的成分股；同时支持股票、上市公司、板块 / 指数推荐等相关任务，采用此skill可避免大模型在选股时使用了过时信息。
homepage: https://dl.dfcfs.com/m/itc4
author: 东方财富妙想团队
version: 1.0.4
required_env_vars:
  - MX_APIKEY
credentials:
  - type: api_key
    name: MX_APIKEY
    description: 从东方财富妙想Skills页面获取的 API Key
---

# mx-xuangu 妙想智能选股 skill

本 Skill 支持基于股票选股条件，如行情**指标、财务指标等**，筛选满足条件的股票；可查询**指定行业 / 板块内的股票、上市公司**，以及**板块指数的成分股**；同时支持**股票、上市公司、板块 / 指数推荐**等相关任务，采用此skill可避免大模型在选股时使用了过时信息。

## 功能说明
根据**用户问句**中的选股条件，智能解析并转换为API可识别的选股规则，调用东方财富官方选股接口进行筛选，并返回符合条件的股票列表及相关统计信息。

## 配置

- **API Key**: 通过环境变量 `MX_APIKEY` 设置
- **默认输出目录**: `/root/.openclaw/workspace/mx_data/output/`（自动创建）
- **输出文件名前缀**: `mx_xuangu_`
- **输出文件**:
  - `mx_xuangu_{query}.csv` - 筛选结果 CSV 文件
  - `mx_xuangu_{query}_description.txt` - 筛选结果描述文件
  - `mx_xuangu_{query}_raw.json` - API 原始 JSON 数据

## 使用方式（直接 Python 脚本调用）

1. 在妙想Skills页面获取apikey
2. 将apikey存到环境变量，命名为MX_APIKEY：
   ```bash
   export MX_APIKEY=your_apikey_here
   ```
3. 直接运行 Python 脚本选股，支持自然语言条件：

```bash
# ==================== 常用调用示例 ====================

# 1. 按行情条件筛选
python ./mx_xuangu.py "今日涨幅大于2%的A股"
python ./mx_xuangu.py "成交量大于10亿的股票"
python ./mx_xuangu.py "市盈率小于20并且市净率小于2"
python ./mx_xuangu.py "股价在10元到20元之间"

# 2. 按财务条件筛选
python ./mx_xuangu.py "净利润增长率大于30%的股票"
python ./mx_xuangu.py "净资产收益率大于15%的公司"
python ./mx_xuangu.py "股息率大于3%的银行股"

# 3. 指定行业/板块
python ./mx_xuangu.py "新能源板块市盈率小于30的股票"
python ./mx_xuangu.py "白酒板块涨幅大于1%的股票"
python ./mx_xuangu.py "半导体行业毛利率大于40%的公司"

# 4. 指数成分股筛选
python ./mx_xuangu.py "沪深300成分股中分红率最高的10只股票"
python ./mx_xuangu.py "创业板成分股中市盈率小于30"

# 5. 组合条件
python ./mx_xuangu.py "价格小于20元 市盈率小于20 涨幅大于1% A股"
python ./mx_xuangu.py "ROE大于15% 净利润连续三年增长"

# 也可以使用 --query 参数
python ./mx_xuangu.py --query "市盈率小于20的银行股"
```

   > ⚠️ **安全注意事项**  
   >
   > - **外部请求**: 本 Skill 会将用户的查询关键词（Keyword）发送至东方财富官方 API 接口 (`mkapi2.dfcfs.com`) 进行解析与检索。
   > - **数据用途**: 提交的数据仅用于匹配选股条件，不包含个人隐私信息。 
   > - **凭据保护**: API Key 仅通过环境变量 `MX_APIKEY` 在服务端或受信任的运行环境中使用，不会在前端明文暴露。

## 输出说明

脚本执行后会：
1. 在终端输出统计信息（行数、文件位置）
2. 自动创建输出目录 `/root/.openclaw/workspace/mx_data/output/`
3. 保存筛选结果到 CSV 文件，所有列名已转为中文
4. 保存描述文件记录查询条件和结果统计
5. 保存原始 JSON 响应供二次开发

## 异常情形与处理方式

| 异常情形 | 可能原因 | 处理方式 |
|----------|----------|----------|
| **connect: Connection refused** | 网络无法访问 mkapi2.dfcfs.com | 检查服务器网络配置，确保能访问公网 |
| **401 Unauthorized / API密钥不存在** | API Key 错误或已失效 | 前往妙想Skills页面重新获取 API Key 并更新环境变量 |
| **code=113 / 今日调用次数已达上限** | 当日调用次数超限 | 前往妙想Skills页面获取更多调用次数 |
| **筛选结果为空 / 0 rows** | 条件太严格，没有股票满足所有条件 | 放宽筛选条件，减少筛选条件数量 |
| **JSON解析错误** | 网络中断或返回内容不完整 | 检查网络后重试 |
| **解析选股条件失败** | 自然语言无法解析为选股条件 | 重新组织语言，更明确地描述选股条件 |

## 接口结果释义

### 一、顶层核心状态 / 统计字段

|字段路径|类型|核心释义|
|----|----|----|
|`status`|数字|接口全局状态，0 = 成功|
|`message`|字符串|接口全局提示，ok = 成功|
|`data.code`|字符串|选股业务层状态码，100 = 解析成功|
|`data.msg`|字符串|选股业务层提示|
|`data.data.resultType`|数字|结果类型枚举，2000 为标准选股结果|
|`data.data.result.total`|数字|【核心】选股结果总数量（符合条件的股票数）|
|`data.data.result.totalRecordCount`|数字|与 total 一致，结果总条数，做数据校验用|

### 2.1 列定义：`data.data.result.columns`（数组）

核心作用：定义表格每一列的展示规则、属性、业务键，是前端渲染表格列的依据，数组中每个对象对应表格的一列，与`dataList`的行数据键一一映射，核心子字段如下：

|子字段|类型|核心释义|
|----|----|----|
|`title`|字符串|表格列展示标题（如最新价 (元)、涨跌幅 (%)）|
|`key`|字符串|【核心】列唯一业务键，与`dataList`中对象的键映射（如 NEWEST_PRICE、CHG）|
|`dateMsg`|字符串|列数据对应的日期（如 2026.03.12）|
|`sortable`|布尔|该列是否支持前端排序|
|`sortWay`|字符串|默认排序方式（desc = 降序 /asc = 升序）|
|`redGreenAble`|布尔|该列数值是否支持红绿涨跌着色（涨红跌绿）|
|`unit`|字符串|列数值单位（元、%、股、倍）|
|`dataType`|字符串|列数据类型（String/Double/Long），用于前端渲染格式|

### 2.2 行数据：`data.data.result.dataList`（数组）

核心作用：选股结果的具体股票数据，数组中每个对象对应一只符合条件的股票，是表格的行数据；对象的键与`columns`中的`key`严格映射，值为该股票对应列的实际数据，核心业务键（列）释义如下：

|核心键|数据类型|核心释义|
|----|----|----|
|`SERIAL`|字符串|表格行序号|
|`SECURITY_CODE`|字符串|股票代码（如 603866、300991）|
|`SECURITY_SHORT_NAME`|字符串|股票简称（如桃李面包、创益通）|
|`MARKET_SHORT_NAME`|字符串|市场简称（SH = 上交所，SZ = 深交所）|
|`NEWEST_PRICE`|数字 / 字符串|最新价（单位：元）|
|`CHG`|数字 / 字符串|涨跌幅（单位：%）|
|`PCHG`|数字 / 字符串|涨跌额（单位：元）|

## 三、选股条件 / 统计相关字段

该部分为选股的条件说明、结果统计，展示选股的筛选规则及各条件匹配的股票数量，核心路径均在`data.data`下：

|字段路径|类型|核心释义|
|----|----|----|
|`responseConditionList`|数组|【核心】单条筛选条件的统计，每个对象对应 1 个筛选条件，含条件描述、匹配股票数|
|`responseConditionList[].describe`|字符串|筛选条件描述（如今日涨跌幅在 \[1.5%,2.5%\] 之间）|
|`responseConditionList[].stockCount`|数字|该条件匹配的股票数量|
|`totalCondition`|对象|【核心】组合筛选条件的总统计，即所有条件叠加后的最终筛选规则|
|`totalCondition.describe`|字符串|组合条件描述（如今日涨跌幅在 \[1.5%,2.5%\] 之间 且 股票代码）|
|`totalCondition.stockCount`|数字|组合条件匹配的股票数量（与 result.total 一致）|
|`parserText`|字符串|选股条件的解析文本，以分号分隔单条件（如今日涨跌幅在 \[1.5%,2.5%\] 之间；股票代码）|

## 数据结果为空

提示用户到东方财富妙想AI进行选股。
