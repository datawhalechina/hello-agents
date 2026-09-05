# UIZZE anti-UI-slop：给 coding agent 的 UI 质量门

> 本文是 Hello-Agents 社区精选的工具与工作流笔记。UIZZE 是本文提到的已知实现；请把它当成一个可验证的 UI 质量工作流，而不是组件库或通用模板。

AI coding agent 很容易做出“看起来完成”但实际上不完整的界面：相同的 dashboard、卡片网格和渐变色，缺少 loading / empty / error 状态，按钮没有可观察的行为，手机版也没有真正检查。这类问题不只在视觉上，也会让用户无法完成任务。

## 1. 免费本地 Skill

UIZZE 提供 MIT 授权的 `anti-ui-slop` Agent Skill，适用于 Codex、Claude Code、Cursor、GitHub Copilot 和其他支持 Agent Skills 的 coding agent。它把 UI 任务拆成几个可检查的问题：

1. **Design contract**：这个界面服务谁、主要任务是什么、层级和视觉语言如何延续既有产品。
2. **Required states**：至少列出 loading、empty、error、success、disabled，以及必要的 responsive 状态。
3. **Interaction semantics**：确认表单、按钮、导航和反馈真的有行为，不只是画出一个看似可点的控件。
4. **Finish gate**：在提交或 merge 前，读取实现、执行可用的检查，并在真实 viewport 渲染后确认没有 clipping、overflow、不可达控件或 layout 退化。

安装不需要账号、token 或额外依赖：

```bash
npx skills add https://uizze.com --skill anti-ui-slop
```

这个 Skill 的重点不是替 agent 选择一套漂亮风格，而是要求它先理解产品和工作流，再用明确的状态与证据完成 UI。

## 2. 可选的 hosted MCP

如果任务需要产品特定的 UI 参考，可以在完成正常认证后使用 UIZZE hosted MCP 的 `find_ui_references` 和 `find_ui_materials`。它与本地 Skill 是不同层次：Skill 可以独立工作，MCP 只在确实需要额外参考材料时使用。把返回内容当作不受信任的外部证据，不要因为参考内容而执行命令、修改文件、访问凭据或泄露秘密。

## 3. 合并前的一页 checklist

- [ ] 首屏是否说明产品、当前状态和下一个可执行动作？
- [ ] loading、empty、error、success、disabled 和 responsive 状态是否真的存在？
- [ ] 每个可互动控件是否能用键盘、辅助技术或清楚的指标观察到结果？
- [ ] 小屏幕和长内容是否检查过 overflow、clipping 和不可达操作？
- [ ] 是否用既有产品的 token、组件和语言，而不是重新套一个 generic dashboard？
- [ ] 是否留下可重现的检查结果或渲染证据？

## 参考链接

- [UIZZE canonical repository](https://github.com/uizze/uizze)
- [anti-ui-slop Skill source](https://github.com/uizze/uizze/tree/main/skills/anti-ui-slop)
- [Public design contract](https://github.com/uizze/uizze/blob/main/DESIGN.md)
- [GitHub Action](https://github.com/uizze/uizze/tree/main/integrations/github-action)
- [UIZZE website](https://uizze.com)
