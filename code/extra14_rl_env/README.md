# Extra14 配套代码：Agent RL 环境入门

配合 [Extra14](../../Extra-Chapter/Extra14-Agent-RL环境入门与合成实战.md) 使用。只需要 Docker 和 [Harbor](https://github.com/harbor-framework/harbor)，不需要 API key。

```bash
uv tool install harbor
```

## 内容

| 路径 | 说明 |
| --- | --- |
| `tasks/order-stats-v1` | 故意写坏的 verifier，空解也能拿分 |
| `tasks/order-stats-v2` | 修好的版本 |
| `probes/` | 用来测试 verifier 的各种解法：正确变体、取巧解、单点改坏 |
| `probe.py` | 用 `oracle` agent 依次运行这些解法，检查 verifier 会不会判错 |
| `synth/` | 最小合成脚本：从种子生成任务，再逐个过门禁 |

## 运行

```bash
# 跑单个任务
harbor run -p tasks/order-stats-v1 -a nop
harbor run -p tasks/order-stats-v1 -a oracle

# 静态检查
harbor lint tasks/order-stats-v1

# 对比两版 verifier
python3 probe.py tasks/order-stats-v1
python3 probe.py tasks/order-stats-v2

# 批量合成并过门禁，任务生成在 synth/generated/
python3 synth/synthesize.py synth/seeds.json

# 只改 verifier 时，用旧结果回放
harbor job regrade jobs/<job目录> -p tasks/order-stats-v2
```

已在 Harbor v0.25.0 上验证。
