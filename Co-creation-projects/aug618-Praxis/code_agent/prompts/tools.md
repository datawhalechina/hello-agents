# 工具使用指南（Claude Code 风格精简版）

针对当前内置工具：`terminal`、`context_fetch`、`todo`、`note`、`memory`、`plan`。遵循“明确何时用 / 何时不用 / 如何用”，避免盲目调用。

## terminal
用途：只读检索与快速查看（ls/rg/cat/sed/head/tail/grep/git status/diff）。
- 何时用：定位文件/符号/报错；小范围查看片段；确认目录结构。
- 何时不用：写文件（用补丁）；大范围全库扫描（除非用户要求）；危险命令（rm/chmod/git reset --hard）。
- 调用示例：`terminal[{"command":"rg -n \"foo\" context/**/*.py","allow_dangerous":false}]`

## context_fetch
用途：聚合搜索（files/notes/memory/tests），自动摘要，控制预算。
- 何时用：需要“更多证据”时；搜类名/函数名/错误栈；需要相关笔记/记忆；比单独 note/memory 搜索更省步数。
- 何时不用：已经有足够证据；用户仅问对话历史。
- 调用示例：`context_fetch[{"sources":["files","notes"],"query":"ContextBuilder","paths":"context/**/*.py"}]`

## todo
用途：多步骤任务跟踪。状态：pending | in_progress（仅 1 个）| completed。
- 何时用：3 步以上或多文件/多特性；用户列出多项需求；跨回合/需确认的任务；开始工作前先标记 in_progress，完成后立即 completed。
- 何时不用：单一步、琐碎或纯问答。
- 示例：
  - `todo[{"action":"add","title":"设计简介页布局","desc":"头部/简介/技能","status":"pending"}]`
  - `todo[{"action":"update","id":1,"status":"in_progress"}]`
  - `todo[{"action":"update","id":1,"status":"completed"}]`
  - `todo[{"action":"list"}]`

## note
用途：结构化笔记（action/decision/blocker/task_state 等），Markdown 持久化。
- 何时用：记录关键结论/风险/阻塞；补丁成功/失败总结；阶段小结。
- 何时不用：临时想法可先留在对话，不必频繁写笔记。
- 示例：`note[{"action":"create","title":"Patch applied","content":"...","note_type":"action","tags":["patch"]}]`

## memory
用途：情景记忆（SQLite）；跨会话回忆“发生过什么”。默认不开自动写，需要显式添加。
- 何时用：需要在未来回忆本次决策/阻塞/结论；会话结束前写一条小结；复用过往经验时可先 search。
- 何时不用：即时对话短期内容已有 history；信息尚不确定。
- 示例：
  - `memory[{"action":"add","memory_type":"episodic","content":"完成 hello.html 样式改造，见补丁...","importance":0.7}]`
  - `memory[{"action":"search","query":"hello.html 样式","memory_types":["episodic"],"limit":5}]`

## plan
用途：显式规划工具，生成分步计划。
- 何时用：任务模糊或明显多步骤；用户要求出计划；执行前需要拆解。
- 何时不用：非常简单的一步任务。
- 示例：`:plan 添加 dark mode 开关` 或 `plan[{"goal":"优化渲染性能，先梳理瓶颈再改"}]`

## 重要提醒
- 写/改文件必须用补丁（*** Begin Patch ...），禁止 `cat > file` / Here-Doc / tee / 重定向写盘。
- 先用已有上下文推理，不足再调用工具；避免无端多次搜索。
- todo 只保持 1 个 in_progress；完成立刻标记完成；阻塞则新增一条说明阻塞。
