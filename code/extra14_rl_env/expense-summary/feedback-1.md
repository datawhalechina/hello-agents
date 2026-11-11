<!-- 第 1 轮反馈：发给 Agent 时，前面先附上 prompt.md 的全文 -->

当前目录里已经有一版任务，但没有通过检查：

gate    expect    result  status
lint    no error  ok      ok
oracle  == 1      infra   FAIL
nop     == 0      infra   FAIL

oracle 没有拿到 reward，Harbor 输出：
ValueError: network_mode='no-network' is not supported by EnvironmentType.DOCKER environment. Environment providers must enforce the requested network policy or reject the task.

nop 没有拿到 reward，Harbor 输出：
ValueError: network_mode='no-network' is not supported by EnvironmentType.DOCKER environment. Environment providers must enforce the requested network policy or reject the task.

把 task.toml 里的 network_mode 去掉之后再跑：

gate    expect    result  status
lint    no error  ok      ok
oracle  == 1      0.00    FAIL
nop     == 0      0.00    ok

oracle 得分 0.00，判分脚本输出：
Summary CSV does not match the required per-person totals.

请修改当前目录里的任务。
