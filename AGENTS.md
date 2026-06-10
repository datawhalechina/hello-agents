# AGENTS.md

给在本仓库中工作的 AI 助手（Claude Code、Cursor、Codex、OpenClaw、Hermes 等）的操作指引。

## 这个仓库是什么

**Hello-Agents** —— Datawhale 社区的系统性智能体学习教程：5 个部分、16 章，理论与实战并重。教程正文是产品：`docs/` 是书，`code/` 是配套代码。

## 仓库结构

```text
docs/chapterN/第N章 XXX.md     各章中文正文（注意：文件名含空格）
docs/chapterN/ChapterN-*.md    对应英文版
docs/_sidebar.md               全书目录
code/chapterN/                 各章配套代码
Extra-Chapter/                 番外篇（FAQ、环境配置、面试题、Skill 写作等）
Co-creation-projects/          社区共创毕业设计项目
.claude/skills/                学习伴学技能（见下）
```

## 学习伴学技能（重要）

当用户输入以下命令、或用自然语言表达相应意图时，**读取对应的 SKILL.md 并严格按其中的流程执行**：

| 触发方式 | 技能文件 |
| -------- | -------- |
| `/find-your-level`，或「我该从哪章开始」「帮我定级」「测测我的水平」 | `.claude/skills/find-your-level/SKILL.md` |
| `/check-understanding <章节>`，或「测测我对第 N 章的掌握」「学完第 N 章了，考考我」 | `.claude/skills/check-understanding/SKILL.md` |

Claude Code 会自动发现这些技能；其他助手请在触发时读取上述文件并遵循执行。

## 帮助学习者时的约定

- 默认使用简体中文交流（除非用户使用其他语言）。
- 解答章节内容问题时，先读 `docs/chapterN/` 对应正文再回答，以书中讲法为准，不要凭通用知识发挥。
- 第 8-15 章的配套代码大量使用 HelloAgents 框架（第 7 章从零构建的框架，实际通过 pip 包 `hello-agents` 安装；部分章节的 requirements 有版本约束）。调试相关问题时先确认 `hello-agents` 包已安装且版本匹配。第 16 章毕业设计无配套代码。
- 环境配置问题优先参考 `Extra-Chapter/Extra07-环境配置.md`。

## 修改本仓库时的约定

- 各章正文有中英两个版本（`第N章 XXX.md` 与 `ChapterN-*.md`），修改内容时保持两者同步。
- 修改章节结构（增删小节）后，检查 `docs/_sidebar.md` 与 README 的内容导航表是否需要同步。
- 测验技能的题目与章节内容强相关：大幅改写某章后，检查 `.claude/skills/` 下引用该章的题目和小节编号是否仍然成立。
