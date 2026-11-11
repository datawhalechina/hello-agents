<!-- 第 2 轮反馈：发给 Agent 时，前面先附上 prompt.md 的全文 -->

当前目录里已经有一版任务，参考解得 1 分，什么都不做得 0 分。但我们又用几种解法检查了判分，有两种判错了：

probe                   expect  reward  result
oracle                  == 1    1.00    ok
nop                     == 0    0.00    ok
mutant_ge_500           < 1     0.00    ok
mutant_no_format        < 1     1.00    WRONG
mutant_sorted_names     < 1     0.00    ok
shortcut_hardcode       == 0    0.00    ok
shortcut_rewrite_input  == 0    1.00    WRONG
variant_float           == 1    1.00    ok

2 probe(s) judged wrongly

判错的两种解法是：
- mutant_no_format：在参考解基础上，把报销总额的输出从 f"{total:.2f}" 改成 str(total)，不再保留两位小数。应该失分，实际得了 1 分。
- shortcut_rewrite_input：示例数据的两个结果文件手写；/app/summarize.py 被判分调用时，把传进来的输入文件改写成只剩表头，再输出两个只有表头的文件。应该得 0 分，实际得了 1 分。

请修改判分部分（tests/），参考解保持不变。
