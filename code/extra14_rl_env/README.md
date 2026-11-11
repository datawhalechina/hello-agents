# Extra14 配套代码：Agent RL 环境入门

配合 [Extra14](../../Extra-Chapter/Extra14-Agent-RL环境入门与合成实战.md) 使用。用到 Docker 和 [Harbor](https://github.com/harbor-framework/harbor)：

```bash
uv tool install harbor
```

## 内容

| 路径 | 说明 |
| --- | --- |
| `prompt.md` | 让 Agent 把“月底汇总报销明细”做成 Harbor 任务的 prompt，可以直接复制给你的 Agent |
| `expense-summary/v1` 到 `v4` | Agent 生成的四个版本，v1 是第一次生成，后面每一版是把检查结果交回去修改后的结果 |
| `expense-summary/feedback-*.md` | 每一轮交回给 Agent 的检查结果原文 |
| `gate.py` | 门禁：`harbor lint`、参考解要满分、空解要 0 分 |
| `probe.py` | 探针：用 `oracle` 依次运行 `probes/` 里的解法，检查判分会不会判错 |
| `probes/` | 针对报销任务写的探针：正确变体、取巧解、单点改坏 |
| `sample-jobs/` | 用 Codex 和 gpt-6-luna 在 v4 上真实运行一次的结果，可以用 `harbor view sample-jobs` 查看。已去掉日志和带本机路径、账号信息的文件，轨迹里省略了 Codex 自带的系统提示词 |

## 运行

除了让 Agent 生成任务和让 Agent 真正做题这两步，下面都不需要 API key。

```bash
# 门禁
python3 gate.py expense-summary/v1
python3 gate.py expense-summary/v4

# 探针
python3 probe.py expense-summary/v2
python3 probe.py expense-summary/v4

# 只改了判分时，用旧结果回放：v2 上作弊拿到的 1 分，用 v3 的判分回放后变成 0 分
cp -R expense-summary/v2 /tmp/v2-cheat
cp probes/shortcut_rewrite_input.sh /tmp/v2-cheat/solution/solve.sh
harbor run -p /tmp/v2-cheat -a oracle -o jobs
harbor job regrade jobs/<job目录> -p expense-summary/v3

# 让真实的 Agent 来做（需要 API key 或 Codex 登录凭证）
harbor run -p expense-summary/v4 -a codex -m openai/gpt-6-luna --agent-setup-timeout-multiplier 4

# 查看附带的运行结果
harbor view sample-jobs
```

v1 在 macOS 的 Docker Desktop 上会因为断网配置跑不起来，这是正文里讲的第一个问题。

已在 Harbor v0.25.0 上验证。
