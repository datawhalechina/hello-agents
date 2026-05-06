---
name: mx-moni
display_name: 妙想模拟组合管理 (MXSKILLS)
title: 妙想模拟组合管理 skill
description: 妙想提供的股票模拟组合管理系统，支持持仓查询、买卖操作、撤单、委托查询、历史成交查询和资金查询等功能。通过安全认证的API接口实现真实交易体验。
homepage: https://dl.dfcfs.com/m/itc4
author: 东方财富妙想团队
version: 1.0.4
required_env_vars:
  - MX_APIKEY
  - MX_API_URL
primary_credential: 
  - MX_APIKEY
credentials:
  - name: MX_APIKEY
    description: 妙想Skills页面获取的专属API密钥，用于接口认证
    required: true
    type: secret
  - name: MX_API_URL
    description: 模拟交易API的基础地址，默认为 https://mkapi2.dfcfs.com/finskillshub
    required: false
    type: string
    default: "https://mkapi2.dfcfs.com/finskillshub"
---

# mx-moni 妙想模拟组合管理 skill

本 Skill 由妙想提供一个股票模拟组合管理系统，支持股票组合持仓查询、买卖操作、撤单、委托查询、历史成交查询和资金查询等功能。通过调用后端模拟组合交易相关原生接口，实现真实的交易体验，所有操作均通过安全认证的 API 接口完成。

```yaml
tags: ["模拟炒股", "A股", "投资练手", "策略验证"]
use_when:
  - 用户需要模拟炒股练手、验证交易策略
  - 用户需要进行模拟交易操作（买卖/撤单）
  - 用户需要查询模拟账户的持仓、资金、委托、历史成交记录
not_for:
  - 真实资金交易、投资建议生成、交易决策指引
  - 非A股类投资模拟（期货、外汇、港股、美股等）
  - 商业用途、代他人操作、非法交易演示
# 环境变量配置
parameters:
  - name: MX_APIKEY
    description: 妙想Skills页面获取专属API密钥
    required: true
    type: secret
    default: process.env.MX_APIKEY
  - name: MX_API_URL
    description: 模拟交易API基础地址
    required: false
    type: string
    default: process.env.MX_API_URL || "https://mkapi2.dfcfs.com/finskillshub"
```

## 功能说明

根据**用户问句**自动识别意图并调用对应接口，支持以下功能：
 
1. **持仓查询**：查询指定账户的当前持仓股票。
2. **买入卖出操作**：执行买入和卖出操作，支持限价/市价委托，自动识别市场号和价格小数位。
3. **撤单操作**：撤销指定委托单，也支持一键撤单。
4. **委托查询**：查询账户下的所有委托订单（含已成交、未成交、已撤单）以及账户的历史成交记录。
5. **资金查询**：查询账户可用资金与总资产。

## 配置

- **MX_APIKEY**：妙想Skills页面获取的API密钥，需保密。
- **MX_API_URL**：模拟交易API的基础URL，默认为 `https://mkapi2.dfcfs.com/finskillshub`。
- **默认输出目录**: `/root/.openclaw/workspace/mx_data/output/`（自动创建）
- **输出文件名前缀**: `mx_moni_`
- **输出文件**:
  - `mx_moni_{query}.txt` - 提取后的纯文本结果
  - `mx_moni_{query}.json` - API 原始 JSON 数据

在使用前，请确保已配置以下环境变量：

```bash
# 导出API Key和API地址
export MX_APIKEY=your_api_key_here
export MX_API_URL=${MX_API_URL:-"https://mkapi2.dfcfs.com/finskillshub"}
```

## 使用方式（直接 Python 脚本调用）

1. 在妙想Skills页面获取apikey。
2. 将apikey存到环境变量，命名为MX_APIKEY，检查本地apikey是否存在，若存在可直接用。
3. 直接运行 Python 脚本，根据自然语言问句自动识别功能：

```bash
# ==================== 常用调用示例 ====================

# 1. 账户查询类
python ./mx_moni.py "我的持仓"
python ./mx_moni.py "查询持仓"
python ./mx_moni.py "我的资金"
python ./mx_moni.py "账户余额"
python ./mx_moni.py "我的委托"
python ./mx_moni.py "查询订单"

# 2. 买入操作
python ./mx_moni.py "买入 600519 价格 1700 数量 100 股"       # 限价买入
python ./mx_moni.py "市价买入 600519 100 股"                   # 市价买入
python ./mx_moni.py "买 300059 19.4 100股"                     # 简写也支持

# 3. 卖出操作
python ./mx_moni.py "卖出 600519 价格 1750 数量 100 股"      # 限价卖出
python ./mx_moni.py "市价卖出 600519 100 股"                  # 市价卖出
python ./mx_moni.py "卖 300059 19.5 100股"                     # 简写也支持

# 4. 撤单操作
python ./mx_moni.py "撤单 260854300000078983"                 # 按委托编号撤单
python ./mx_moni.py "一键撤单"                                 # 撤销当日所有未成交委托
```

   > ⚠️ **安全注意事项**
   >
   > - **外部请求**: 本 Skill 会通过 Python 脚本发送请求至东方财富官方 API 域名 ( `mkapi2.dfcfs.com` ) 以获取模拟交易数据。
   > - **凭据保护**: API Key 仅通过环境变量 `MX_APIKEY` 在服务端或受信任的运行环境中使用，不会在前端明文暴露。

## 异常情形与处理方式

| 异常情形 | 可能原因 | 处理方式 |
|----------|----------|----------|
| **connect: Connection refused** | 网络无法访问 mkapi2.dfcfs.com | 检查服务器网络配置，确保能访问公网 |
| **401 Unauthorized / API密钥不存在** | API Key 错误或已失效 | 前往妙想Skills页面重新获取 API Key 并更新环境变量 |
| **code=113 / 今日调用次数已达上限** | 当日调用次数超限 | 前往妙想Skills页面获取更多调用次数 |
| **code=404 / 未绑定模拟组合账户** | 账户未创建绑定 | 前往妙想Skills页面创建模拟账户并绑定后重试 |
| **委托方式错误 / 委托失败** | 当前非交易时间，或价格格式错误 | A股交易时间为 9:30-11:30/13:00-15:00，非交易时间无法下单；检查价格小数位是否符合市场规则 |
| **可撤委托不存在** | 委托已经成交或已撤单 | 查询委托列表确认委托状态 |
| **数据结果为空** | 账户无持仓/无委托 | 确认账户状态后重试 |
| **JSON解析错误** | 网络中断或返回内容不完整 | 检查网络后重试 |

## 交易操作说明

### 买入操作

**语法格式：**
```
python ./mx_moni.py "买入 [股票代码] [价格] [数量] 股"
python ./mx_moni.py "市价买入 [股票代码] [数量] 股"
```

**参数规则：**

| 参数 | 必填 | 说明 |
|------|------|------|
| `股票代码` | 是 | 6位数字A股代码，系统自动识别市场 |
| `价格` | 是（限价） | 委托价格，沪市不超过2位小数，深市不超过3位小数 |
| `数量` | 是 | 委托数量（股），必须为100的整数倍（100、200、300...） |
| `市价委托` | - | 使用 `市价买入` 时无需提供价格，自动以当前最新价成交 |

### 卖出操作

**语法格式：**
```
python ./mx_moni.py "卖出 [股票代码] [价格] [数量] 股"
python ./mx_moni.py "市价卖出 [股票代码] [数量] 股"
```

参数规则与买入一致。

### 撤单操作

**语法格式：**
```
python ./mx_moni.py "撤单 [委托编号]"
python ./mx_moni.py "一键撤单"
```

- **按委托编号撤单**：需要从委托查询中获取委托编号
- **一键撤单**：撤销当日所有未成交委托，无需参数

### 股票代码格式说明

买入/卖出/撤单接口的股票代码入参仅支持A股，格式为6位数字，例如 `600519`、`000001`。

### 委托数量说明

必须为整数，且需为100的整数倍（如100、200、300等），否则会被交易所拒单。

### 委托价格说明

当 `useMarketPrice=false` （限价委托）时，price参数必填，且需符合市场规则：沪市价格小数位不超过2位，深市价格小数位不超过3位；当 `useMarketPrice=true` （市价委托）时，price参数会被忽略，系统会自动以行情最新价进行买入。

---

## 前置要求

- 用户需在妙想Skills页面获取并配置 `MX_APIKEY` 和 `MX_API_URL` 环境变量。
- 模拟组合账户操作前，用户需在妙想Skills页面（地址：https://dl.dfcfs.com/m/itc4 ），创建模拟账户后，并绑定模拟组合。
- 买入/卖出操作需提供正确的股票代码、价格和数量，且价格需符合市场规则（如价格小数位）。
- 撤单操作需提供有效的委托编号，且该委托必须处于可撤销状态。
- 查询操作需确保账户已绑定且存在有效数据。

## 支持功能与触发词（脚本自动识别）

| 功能 | 触发词 | 使用示例 |
|------|--------|----------|
| 持仓查询 | `查询持仓`、`我的持仓`、`持仓情况` | `python mx_moni.py 我的持仓` |
| 资金查询 | `查询资金`、`我的资金`、`账户余额`、`资金情况` | `python mx_moni.py 我的资金` |
| 委托查询 | `查询委托`、`我的委托`、`订单`、`委托记录` | `python mx_moni.py 我的委托` |
| 买入操作 | `买入`、`买进`、`建仓`、`市价买入` | `python mx_moni.py 买入 600519 1700 100股` |
| 卖出操作 | `卖出`、`抛售`、`减仓`、`市价卖出` | `python mx_moni.py 卖出 600519 1750 100股` |
| 撤单操作 | `撤单`、`撤销`、`一键撤单` | `python mx_moni.py 撤单 260854300000078983` |

脚本会根据关键词自动识别并调用对应接口。结果输出到终端，并保存原始 JSON 到输出目录。

## 安全与错误处理

| 错误类型                | 处理方式                                        |
| ----------------------- | ----------------------------------------------- |
| 今日调用次数已达上限 (113)          | 提示用户前往妙想Skills页面，获取更多次数           |
| API密钥不存在或已失效，请确认密钥是否正确 (114)          | 提示用户前往妙想Skills页面，更新apikey           |
| 请求未携带API密钥，请检查请求参数 (115)          | 提示用户检查 `MX_APIKEY` 是否配置正确           |
| API密钥不存在，请确认密钥是否正确 (116)          | 提示用户检查 `MX_APIKEY` 是否配置正确           |
| 未绑定模拟组合账户 (404)          | 提示用户前往妙想Skills页面创建并绑定模拟账户           |
| 网络错误                | 重试最多3次，仍失败则提示“网络异常，请稍后重试” |
