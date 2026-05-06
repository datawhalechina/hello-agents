---
name: mx-data
display_name: 妙想金融数据 (MXSKILLS)
title: 妙想金融数据 skill
description: 基于东方财富权威数据库的金融数据查询工具，支持行情、财务及关联关系数据。
homepage: https://dl.dfcfs.com/m/itc4
author: 东方财富妙想团队
version: 1.0.0
env:
  - MX_APIKEY: "通过东方财富妙想Skills页面获取的 API Key"
---

# mx-data 妙想金融数据 skill

本 Skill 基于**东方财富权威数据库**及**最新行情底层数据**构建，支持通过**自然语言**查询以下三类数据：

1. **行情类数据**  
 股票、行业、板块、指数、基金、债券的实时行情、主力资金流向、估值等数据。
2. **财务类数据**  
 上市公司与非上市公司的基本信息、财务指标、高管信息、主营业务、股东结构、融资情况等数据。
3. **关系与经营类数据**  
 股票、非上市公司、股东及高管之间的关联关系数据，以及企业经营相关数据。

采用此skill可避免模型基于自身过时知识回答金融相关数据问题，可为大模型提供权威及时的金融数据。

## 配置

- **API Key**: 通过环境变量 `MX_APIKEY` 设置
- **默认输出目录**: `/root/.openclaw/workspace/mx_data/output/`（自动创建）
- **输出文件名前缀**: `mx_data_`
- **输出文件**:
  - `mx_data_{query}.xlsx` - Excel 文件，每个数据表一个 sheet（多 sheet）
  - `mx_data_{query}_description.txt` - 查询结果描述文件
  - `mx_data_{query}_raw.json` - API 原始 JSON 数据

## 使用方式（直接 Python 脚本调用）

1. 在妙想Skills页面获取apikey。(链接:https://dl.dfcfs.com/m/itc4)
2. 将apikey存到环境变量，命名为MX_APIKEY：
   ```bash
   export MX_APIKEY=your_apikey_here
   ```
3. 直接运行 Python 脚本查询，支持自然语言问句：

```bash
# ==================== 常用调用示例 ====================

# 1. 个股实时行情查询
python ./mx_data.py "东方财富最新价"
python ./mx_data.py "贵州茅台今日收盘价 涨跌幅"
python ./mx_data.py "宁德时代主力资金流向"

# 2. 历史行情数据查询
python ./mx_data.py "贵州茅台近五年年报收盘价"
python ./mx_data.py "比亚迪近一年每个交易日的开盘价收盘价成交量"

# 3. 财务数据查询
python ./mx_data.py "贵州茅台近三年净利润 营业收入"
python ./mx_data.py "东方财富每股收益 净资产收益率 近五年"
python ./mx_data.py "万科A资产负债率 毛利率 近三年"

# 4. 上市公司基本信息
python ./mx_data.py "比亚迪公司简介 主营业务 成立时间"
python ./mx_data.py "贵州茅台董事长是谁 总股本多少"

# 5. 股东信息
python ./mx_data.py "贵州茅台十大股东"
python ./mx_data.py "比亚迪机构持股比例"
# 6. 板块/指数行情
python ./mx_data.py "沪深300指数最新点位 涨跌幅"
python ./mx_data.py "新能源板块成分股平均涨跌幅"

# 7. 指定输出目录（可选）
python ./mx_data.py "贵州茅台近五年年报" /path/to/output
```

   > ⚠️ **安全注意事项**
   >
   > - **外部请求**: 本 Skill 会将您的查询文本发送至东方财富官方 API 域名 ( `mkapi2.dfcfs.com` ) 以获取金融数据。
   > - **凭据保护**: API Key 仅通过环境变量 `MX_APIKEY` 在服务端或受信任的运行环境中使用，不会在前端明文暴露。

## 数据限制说明

请谨慎查询大数据范围的数据，如某只股票3年的每日最新价，可能会导致返回内容过多，模型上下文爆炸问题。

## 输出说明

脚本执行后会：
1. 在终端输出查询结果预览（前20行）
2. 自动创建输出目录 `/root/.openclaw/workspace/mx_data/output/`
3. 保存完整数据到 Excel 文件（多 sheet）
4. 保存原始 JSON 响应供二次处理
5. 保存描述文件记录查询条件和结果统计

## 异常情形与处理方式

| 异常情形 | 可能原因 | 处理方式 |
|----------|----------|----------|
| **connect: Connection refused** | 网络无法访问 mkapi2.dfcfs.com | 检查服务器网络配置，确保能访问公网 |
| **401 Unauthorized / code=114 / API密钥不存在** | API Key 错误或已失效 | 前往妙想Skills页面重新获取 API Key 并更新环境变量 |
| **code=113 / 今日调用次数已达上限** | 当日调用次数超限 | 前往妙想Skills页面获取更多调用次数 |
| **数据结果为空 / No dataTable found** | 查询条件太严格或查询内容不支持 | 放宽查询条件，或确认查询内容是否正确 |
| **返回数据行数过多 / 输出过大** | 查询范围过大（如多年每日数据） | 缩小查询时间范围，减少返回数据量 |
| **JSON解析错误** | 网络中断或返回内容不完整 | 检查网络后重试 |

## 返回结果字段释义

### 一级核心路径：`data`

|字段路径|类型|核心释义|
|----|----|----|
|`data.questionId`|字符串|查数请求唯一标识 ID，关联单次查询任务|
|`data.dataTableDTOList`|数组|【核心】标准化后的证券指标数据列表，每个元素对应**1 个证券 + 1 个指标**的完整数据|
|`data.rawDataTableDTOList`|数组|原始未加工的证券指标数据列表，与标准化列表结构完全一致，供原始数据调用|
|`data.condition`|对象|本次查数的查询条件，记录查询关键词、时间范围等|
|`data.entityTagDTOList`|数组|本次查询关联的**证券主体汇总信息**，去重后展示所有涉事证券的基础属性|

### 二级核心路径：`data.dataTableDTOList[]`（单指标对象，表格核心）

数组内每个对象为**独立的指标数据单元**，包含**证券信息 + 表格数据 + 指标元信息 + 证券标签**四大部分，是表格渲染的核心载体，表格逻辑为：`table/rawTable`为**单元格数据**，`nameMap`为**列名映射**，`indicatorOrder`为**指标列排序**。

#### 2.1 证券基础信息

|字段路径|类型|核心释义|
|----|----|----|
|`dataTableDTOList[].code`|字符串|证券完整代码（含市场标识，如 300059.SZ）|
|`dataTableDTOList[].entityName`|字符串|证券全称（含代码，如东方财富 (300059.SZ)）|
|`dataTableDTOList[].title`|字符串|本指标数据的标题，概括查询结果（如东方财富最新价）|

#### 2.2 表格数据核心（渲染用）

|字段路径|类型|核心释义|表格逻辑|
|----|----|----|----|
|`dataTableDTOList[].table`|对象|【核心】标准化表格数据，**键 = 指标编码，值 = 指标数值数组**；`headName`为时间 / 维度列值|键为**指标列**，`headName`为**时间列**，值为交叉单元格的**指标数值**|
|`dataTableDTOList[].rawTable`|对象|原始表格数据，与`table`结构一致，未做数据标准化处理|同`table`，为原始数值，无格式 / 单位修正|
|`dataTableDTOList[].nameMap`|对象|【核心】列名映射关系，将**指标编码 / 内置字段**转为**业务中文名**（如 f2→最新价）|解决表格列名 "编码转中文" 的问题，`headNameSub`为时间列的固定名称|
|`dataTableDTOList[].indicatorOrder`|数组|指标列的展示排序，元素为指标编码（如 \[f2\]）|控制表格中多个指标列的前后顺序，单指标时为单元素数组|

#### 2.3 指标元信息（属性 / 规则）

|字段路径|类型|核心释义|
|----|----|----|
|`dataTableDTOList[].dataType`|字符串|数据来源类型（如行情数据 / 数据浏览器）|
|`dataTableDTOList[].dataTypeEnum`|字符串|数据类型枚举值（HQ = 行情，DATA_BROWSER = 数据浏览器），供系统判断|
|`dataTableDTOList[].dataTableType`|字符串|表格类型（NORM_TABLE = 标准表格），固定值|
|`dataTableDTOList[].field`|对象|【核心】当前指标的详细元信息，含指标编码、名称、查询时间、粒度等|
|`dataTableDTOList[].fieldSet`|数组|指标元信息集合，与`field`内容一致，为兼容多指标设计，单指标时为单元素数组|

#### 2.4 证券标签信息（主体属性）

|字段路径|类型|核心释义|
|----|----|----|
|`dataTableDTOList[].entityTagDTO`|对象|本指标关联证券的详细主体属性（如证券类型、市场、简称等）|
|`dataTableDTOList[].entityTagDTOList`|数组|证券主体属性集合，与`entityTagDTO`一致，兼容多证券设计|

### 三级核心路径：`field`/`entityTagDTO`（元信息子字段）

#### 3.1 指标元信息：`dataTableDTOList[].field`

|字段路径|类型|核心释义|
|----|----|----|
|`field.returnCode`|字符串|指标唯一编码（如 ZXJ_f2_3/100000000017975）|
|`field.returnName`|字符串|指标业务中文名（如最新价 / 收盘价）|
|`field.returnSourceCode`|字符串|指标原始来源编码（如 f2/CLOSE），对接底层数据源|
|`field.returnSourceName`|字符串|指标原始来源名称，与`returnName`一致|
|`field.startDate/endDate`|字符串|本次查询的时间范围（开始 / 结束）|
|`field.dateGranularity`|字符串|数据粒度（DAY = 日度，MIN = 分钟等）|
|`field.classCode`|字符串|指标分类编码，用于指标归类|

#### 3.2 证券主体属性：`dataTableDTOList[].entityTagDTO`

|字段路径|类型|核心释义|
|----|----|----|
|`entityTagDTO.secuCode`|字符串|证券纯代码（无市场标识，如 300059）|
|`entityTagDTO.marketChar`|字符串|市场标识（.SZ = 深交所，.SH = 上交所）|
|`entityTagDTO.entityTypeName`|字符串|证券类型（如 A 股 / 港股 / 债券）|
|`entityTagDTO.fullName`|字符串|证券完整中文名（如东方财富）|
|`entityTagDTO.entityId`|字符串|证券在系统内的唯一主体 ID|
|`entityTagDTO.className`|字符串|证券大类（如沪深京股票 / 创业板股票）|

### 其他核心路径：`condition`/`entityTagDTOList`

#### 4.1 查询条件：`data.condition`

|字段路径|类型|核心释义|
|----|----|----|
|`condition.search_data_task_0`|数组|本次查数的原始条件，按【证券名 + 指标名 + 时间范围】排序|

#### 4.2 证券主体汇总：`data.entityTagDTOList`

与`dataTableDTOList[].entityTagDTO`结构完全一致，为本次查询所有关联证券的去重汇总信息，避免重复展示，供页面顶部 / 筛选栏使用。

## 数据结果为空

提示用户到东方财富妙想AI查询。
如果请求失败，检查API Key是否正确，网络是否正常
