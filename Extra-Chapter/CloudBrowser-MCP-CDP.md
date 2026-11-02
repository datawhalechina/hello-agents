# 用百智云浏览器读取公开网页：MCP 配置与 CDP 实操

本练习用百智云浏览器（Baizhi Cloud Browser，也称 CapyBrowser）打开 `https://example.com/`，读取页面标题和第一个 `h1`。完成后，你应看到两项都是 `Example Domain`，并确认本次云运行已经结束。

你会用到两种客户端：MCP 客户端管理云运行，Python 脚本通过 CDP 操作页面。它是一份独立实践教程，可以接着[第十章](../docs/chapter10/第十章%20智能体通信协议.md)和 [WebAgent 实战](Extra11-WebAgent科普与实战.md)阅读；无需安装 HelloAgents 框架，也不要求在 HelloAgents 中运行模型。

## 1. 准备好两个操作位置

- **A：MCP 客户端。** 使用你选择的、支持 Streamable HTTP、能查看工具结果并调用工具的客户端。它可以是带 MCP 功能的桌面 Agent 或开发工具。下面会给出连接字段和可复制的任务指令；具体添加入口以该客户端说明为准。
- **B：本机终端。** 用 Python 3.12 执行仓库附带的两个脚本。终端负责连接浏览器并读取页面，A 负责创建和结束云运行。
- 云端阶段需要自己的百智云浏览器账号和 API Key。如果暂时没有 MCP 客户端或不想创建可能收费的运行，可只做第 3 节的只读检查。

先在 B 单独执行 `bash` 进入 Bash，再从仓库根目录安装示例依赖：

```bash
python3 -m venv .venv-cloud-browser
source .venv-cloud-browser/bin/activate
python -m pip install -r code/extra/cloud_browser/requirements.txt
```

示例固定了本地验证使用的 MCP SDK 1.26.0 和 Playwright 1.56.0，便于复现，不代表最新版本建议。这里只连接已有 Chromium，无需执行 `playwright install` 或在本机启动浏览器。

## 2. 在 A 添加百智云浏览器 MCP

在客户端的远程 MCP 配置中填写：

| 字段 | 值 |
| --- | --- |
| 显示名称 | 百智云浏览器 |
| 传输方式 | Streamable HTTP |
| 服务地址 | `https://capybrowser.app.baizhi.cloud/mcp` |
| 请求头名称 | `Authorization` |
| 请求头值 | `Bearer YOUR_API_KEY`，将占位值换成完整 Key |

`Bearer` 与 Key 之间有一个空格，不能只填 `Bearer`。在客户端设置中填写凭据，不发到聊天正文；填写具备百智云浏览器访问权限的 Key；不要假定其他应用的专用 Key 可以通用。保存后连接并查看工具列表，应能找到 `browser_auth_check`、`browser_pricing` 等 `browser_*` 管理工具。

这些工具管理浏览器运行；页面导航和读取由后面的 CDP 脚本完成。若客户端无法发现工具，先检查 URL、传输方式和请求头，不创建运行试错。

## 3. 在 B 做只读检查

在同一 Bash 中隐藏输入原始 Key，不加 `Bearer`：

```bash
IFS= read -r -s -p 'Capy API Key: ' CAPYBROWSER_API_KEY
printf '\n'
export CAPYBROWSER_API_KEY
python code/extra/cloud_browser/mcp_probe.py
unset CAPYBROWSER_API_KEY
```

[探针脚本](../code/extra/cloud_browser/mcp_probe.py)只初始化 MCP、发现工具并调用 `browser_auth_check` 和 `browser_pricing`，不会创建浏览器，也不调用模型。成功输出包含 `discovery: "passed"` 和两项只读工具名称；失败时先修正配置。

探针不打印账户或价格原文。在 A 继续查看价格后再决定是否进行下一节。如果 A 是聊天 Agent，可复制下面指令；若是手动调试客户端，按其中的工具顺序调用并阅读返回值：

> 只使用已配置的百智云浏览器 MCP，调用 browser_auth_check 和 browser_pricing。告诉我凭据检查是否通过，以及当前浏览器启动和运行价格；不要输出账户详情，不创建运行。

## 4. 可选：让 A 创建本次运行并等你接入

**从这里开始可能产生云运行费用，等待你操作期间也可能计费；所用聊天 Agent 的模型费用另计。** 确认价格和本次授权后，把下面的指令交给 A。B 的依赖应已安装好，以便取得控制地址后马上接入。

> 这次授权创建至多一个临时浏览器运行，max_seconds=180，不关联 Profile。目标只是在 https://example.com/ 读取标题和第一个 h1，不登录、不提交表单。你负责创建和结束原运行，我将在本机 Python 终端执行页面读取。
>
> 创建前先保存本次稳定的 idempotency_key 与原创建参数，再调用 browser_create_session，记录返回的完整 session_id。若创建结果不明，只用原键、原参数恢复，不换键重开。对原运行有界查询 browser_get_session；只有 ready、未到期且无人正在操作时，才调用一次 browser_control。
>
> 取得 cdp_url 后暂停，等我报告脚本结果。告诉我 session_id 和剩余时间，不复述控制地址到聊天正文；我会从工具结果中将它复制到本机终端。你继续持有原 session_id，等我完成、失败或取消后都负责收尾。若运行到期或无法继续，也结束并核对原运行，不另开一轮。

按工具实际 Schema 填参数；[正式指南](https://capybrowser.app.baizhi.cloud/docs/installation.md)说明当前接口及恢复规则。保存好原 Session ID。CDP 地址是一次性控制地址，首次连接期限与运行到期时间不同；不要打开到浏览器地址栏，也不要在健康连接中再申请备用地址。

## 5. 在 B 连接并读取页面

从 A 的工具结果取得 `cdp_url`，在 B 隐藏输入后立刻运行：

```bash
IFS= read -r -s -p '一次性 CDP 地址: ' CAPY_CDP_ENDPOINT
printf '\n'
export CAPY_CDP_ENDPOINT
python code/extra/cloud_browser/cdp_read.py
unset CAPY_CDP_ENDPOINT
```

[页面脚本](../code/extra/cloud_browser/cdp_read.py)连接一次，在默认 context 中新建自己的页面，打开 `https://example.com/` 并读取 DOM。核对输出中的标题和 `h1`：

```json
{
  "page_task": "passed",
  "title": "Example Domain",
  "heading": "Example Domain",
  "client_cleanup": "completed",
  "cloud_release": "not_checked"
}
```

脚本会关闭自己创建的页面并断开 Playwright。`cloud_release: "not_checked"` 提醒你云运行还要由 A 结束；脚本失败或被中断也要继续下一节。连接断开后先查原运行，不重复使用旧地址或直接重跑创建步骤。

## 6. 回到 A，结束原运行

把本次实际结果告诉 A，并要求收尾。例如：

> Python 脚本已结束，标题和 h1 都是 Example Domain。请停止刚才保存的原 session_id：调用 browser_stop_session，再有界查询 browser_get_session，确认是否 released。单独报告 billing.status；settled 时按 actual_charge_centipoints / 100 报实际积分，waived 时报告免收，其他状态写待确认。不要重新创建运行。

如果失败，第一句换成“Python 脚本失败或已取消”，其余收尾要求保持。只有 `released` 才表示已释放；停止请求受理或断开 CDP 都不能代替它。若 A 不可用，使用控制台查看并结束同一 Session；释放或结算仍不明时保留 ID 与脱敏状态，向服务支持反馈。

最后在 B 运行 `deactivate`，再 `exit` 退出本练习的 Bash。需要移除本地依赖时，只删除本练习新建的 `.venv-cloud-browser`。退出终端、移除客户端配置和撤销 Key 都不能代替结束已有云运行。

## 使用范围与支持

本例的两个脚本在本地合成 MCP 服务和本地 Chrome 上做过验证；真实云端完整流程和 HelloAgents 原生模型回合尚未验证。它没有自动创建包装器或自动恢复模型任务，云端阶段以你实际看到的页面、释放与费用结果为准。

服务用途见[产品说明](https://baizhibrowser.cloud/zh/)，接口以[正式指南](https://capybrowser.app.baizhi.cloud/docs/installation.md)为准；账号、费用和私密问题通过[控制台](https://capybrowser.app.baizhi.cloud/)支持入口反馈。本文作者参与维护 [ctcbyzx 独立接入材料](https://github.com/ctcbyzx/baizhi-cloud-browser)，并向 [Chaitin 公共接入指南](https://github.com/chaitin/baizhi-cloud-browser)贡献材料；示例问题可到[维护仓 Issues](https://github.com/ctcbyzx/baizhi-cloud-browser/issues)附脱敏步骤反馈。这些是接入材料仓库，本文不表示服务被 Hello-Agents 内置或推荐。
