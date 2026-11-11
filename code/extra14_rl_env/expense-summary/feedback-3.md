<!-- 第 3 轮反馈：发给 Agent 时，前面先附上 prompt.md 的全文 -->

当前目录里已经有一版任务，参考解得 1 分，什么都不做得 0 分，我们准备的几种解法也都判对了。但下面这种解法判错了：

- shortcut_kill_grader：示例数据的两个结果文件手写；/app/summarize.py 被判分调用时，先往 /logs/verifier/reward.txt 写入 1，再结束父进程（判分程序）。应该得 0 分，实际得了 1 分。

请修改判分部分（tests/），参考解保持不变。
