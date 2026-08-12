---
name: mx-zixuan
display_name: 妙想自选股管理 (MXSKILLS)
title: 妙想自选管理skill
description: 妙想自选管理skill，基于东方财富通行证账户数据及行情底层数据构建，支持通过自然语言查询、添加、删除自选股。
homepage: https://dl.dfcfs.com/m/itc4
author: 东方财富妙想团队
version: 1.0.0
required_env_vars:
  - MX_APIKEY
credentials:
  - type: api_key
    name: MX_APIKEY
    description: 从东方财富妙想Skills页面获取的 API Key
---

# mx-zixuan 妙想自选管理skill

通过自然语言查询或操作东方财富通行证账户下的自选股数据，接口返回JSON格式内容。

## 功能列表
- ✅ 查询我的自选股列表
- ✅ 添加指定股票到我的自选股列表
- ✅ 从我的自选股列表中删除指定股票

## 配置

- **API Key**: 通过环境变量 `MX_APIKEY` 设置（与其他妙想技能共享）
- **默认输出目录**: `/root/.openclaw/workspace/mx_data/output/`（自动创建）
- **输出文件名前缀**: `mx_zixuan_`
- **输出文件**:
  - `mx_zixuan_{query}.csv` - 自选股列表 CSV 格式
  - `mx_zixuan_{query}_raw.json` - API 原始 JSON 数据

## 前置要求
1. 获取东方财富妙想Skills页面的apikey
2. 将apikey配置到环境变量 `MX_APIKEY`
3. 确保网络可以访问 `https://mkapi2.dfcfs.com`

   > ⚠️ **安全注意事项**
   >
   > - **外部请求**: 本 Skill 会将您的查询文本发送至东方财富官方 API 域名 ( `mkapi2.dfcfs.com` ) 以获取金融数据。
   > - **凭据保护**: API Key 仅通过环境变量 `MX_APIKEY` 在服务端或受信任的运行环境中使用，不会在前端明文暴露。


## 使用方式（直接 Python 脚本调用）

```bash
# 先设置环境变量
export MX_APIKEY=your_apikey_here
```

### 1. 查询自选股列表
```bash
# 明确命令
python ./mx_zixuan.py query

# 自然语言查询
python ./mx_zixuan.py "查询我的自选股列表"
python ./mx_zixuan.py "我的自选"
python ./mx_zixuan.py "看一下自选"
```

### 2. 添加股票到自选股
```bash
# 明确命令
python ./mx_zixuan.py add "贵州茅台"
python ./mx_zixuan.py add "300059"

# 自然语言
python ./mx_zixuan.py "把贵州茅台添加到我的自选股列表"
python ./mx_zixuan.py "加入自选 比亚迪"
```

### 3. 删除自选股
```bash
# 明确命令
python ./mx_zixuan.py delete "贵州茅台"

# 自然语言
python ./mx_zixuan.py "把贵州茅台从我的自选股列表删除"
python ./mx_zixuan.py "删除自选 万科A"
```

## 异常情形与处理方式

| 异常情形 | 可能原因 | 处理方式 |
|----------|----------|----------|
| **connect: Connection refused** | 网络无法访问 mkapi2.dfcfs.com | 检查服务器网络配置，确保能访问公网 |
| **401 Unauthorized / API密钥不存在** | API Key 错误或已失效 | 前往妙想Skills页面重新获取 API Key 并更新环境变量 |
| **code=113 / 今日调用次数已达上限** | 当日调用次数超限 | 前往妙想Skills页面获取更多调用次数 |
| **自选股列表为空** | 账户下没有自选股 | 在东方财富App添加自选股后重试，或使用 add 命令添加 |
| **找不到该股票** | 股票名称/代码不正确 | 确认股票名称或代码正确，使用6位数字代码成功率更高 |
| **操作失败** | 股票已经在自选股中（添加）或不在自选股中（删除） | 先查询确认当前自选股列表再操作 |
| **JSON解析错误** | 网络中断或返回内容不完整 | 检查网络后重试 |

## 输出示例
### 查询自选股成功
```
📊 我的自选股列表
================================================================================
股票代码 | 股票名称 | 最新价(元) | 涨跌幅(%) | 涨跌额(元) | 换手率(%) | 量比
--------------------------------------------------------------------------------
600519   | 贵州茅台 | 1850.00    | +2.78%    | +50.00     | 0.35%     | 1.2
300750   | 宁德时代 | 380.00     | -1.25%    | -4.80      | 0.89%     | 0.9
================================================================================
共 2 只自选股
```

查询完成后会自动保存：
- CSV 格式方便 Excel 打开查看
- 原始 JSON 保存供二次开发

### 添加/删除成功
```
✅ 操作成功：贵州茅台已添加到自选股列表
```

## 错误处理
- 未配置apikey: 提示设置环境变量 `MX_APIKEY`
- 接口调用失败: 显示错误信息
- 数据为空: 提示用户到东方财富App查询

## 接口说明
### 查询接口
- URL: `https://mkapi2.dfcfs.com/finskillshub/api/claw/self-select/get`
- 方法: POST
- Header: `apikey: {MX_APIKEY}`

### 管理接口（添加/删除）
- URL: `https://mkapi2.dfcfs.com/finskillshub/api/claw/self-select/manage`
- 方法: POST
- Header: `apikey: {MX_APIKEY}`
- Body: `{"query": "自然语言指令"}`
