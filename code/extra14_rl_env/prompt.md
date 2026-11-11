把下面这件日常工作做成一个 Harbor 任务，写在当前目录。

Harbor 的任务格式见 https://github.com/harbor-framework/harbor/tree/main/docs-mintlify/tasks ，
重点看 overview、separate-verifier 和 artifacts 三篇。

要求：
- 用 separate verifier，判分需要的 Agent 产出声明为 artifacts
- 判分用 tests/ 里另外准备的数据，只考 instruction.md 写了的要求
- 什么都不做得 0 分，参考解得 1 分
- 日志里不打印期望值
- 任务保持简单

任务：
每个月月底，我要把同事提交的报销明细汇总一下：按人算出报销总额，再把单笔超过 500 元的记录挑出来，交给财务复核。明细是一个 CSV 文件，列有日期、姓名、类别、金额。
