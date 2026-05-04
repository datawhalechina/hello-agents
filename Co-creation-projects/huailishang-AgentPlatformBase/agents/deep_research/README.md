# deep_research

`deep_research` 是 chapter16 平台内置的搜索调研智能体，源码位于：

```text
agents/deep_research/src/
```

这份源码来自 chapter14 的 DeepResearchAgent，并已内置到 chapter16 项目中。默认运行不再依赖 `code/chapter14`，因此只保留 `code/chapter16/agent_platform_base` 也可以运行搜索员。

运行数据写入：

```text
data/deep_research/runs/
data/deep_research/notes/
```

- `runs/`：单次运行过程产物，可按保留期清理。
- `notes/`：研究笔记和索引，默认长期保留。
