---
name: CloudSeed
description: 科研处理工作台的已实现视觉系统
colors:
  ink: "#172c3b"
  muted: "#526679"
  blue: "#164f7b"
  teal: "#146c63"
  line: "#d8e2e8"
  canvas: "#f3f6f8"
  white: "#fff"
  wash: "#e8f2f4"
  error: "#a33030"
typography:
  headline:
    fontFamily: '"Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "27px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "-0.025em"
  title:
    fontFamily: '"Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.5
  body:
    fontFamily: '"Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: '"Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "14px"
    fontWeight: 600
    lineHeight: 1.65
  table:
    fontFamily: '"Segoe UI", "Microsoft YaHei", sans-serif'
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.7
rounded:
  evidence: "3px"
  badge: "4px"
  hypothesis: "5px"
  control: "6px"
  container: "8px"
spacing:
  tight: "8px"
  field: "18px"
  content: "22px"
  section: "24px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.white}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
    width: "100%"
  button-secondary:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  input:
    backgroundColor: "{colors.white}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 11px"
    width: "100%"
  tab-selected:
    textColor: "{colors.blue}"
    typography: "{typography.label}"
    padding: "10px 1px"
  badge:
    backgroundColor: "{colors.wash}"
    rounded: "{rounded.badge}"
    padding: "4px 9px"
  topic:
    backgroundColor: "{colors.white}"
    rounded: "{rounded.container}"
    padding: "23px 26px"
---

# Design System: CloudSeed

## Overview

**Creative North Star: "科研处理工作台"**

浅灰蓝画布托起高密度的研究资料和结果。科研蓝标识主要操作、资料编号与当前页，克制青绿标识证据与完成状态。系统使用行、表格、标签和明确的字段标题，让研究者在阅读与操作之间切换。

视觉以正文可读性、证据归属和状态清晰为中心。形状和颜色支持信息组织；本文记录 `ui/index.html` 的实际实现，不将候选研究结论变成视觉上的确定事实。

**Key Characteristics:**
- 系统字体与紧凑但有段落间距的阅读密度。
- 平面白色内容区、灰蓝设置区和细边界。
- 蓝色行动与青绿证据状态分工。
- 来源编号、阅读范围和研究草案标记始终有独立层级。

## Colors

色彩通过中性层区分区域，通过两种克制的强调色表达行动与证据。

### Primary
- **科研蓝**（`blue`）：主分析按钮、链接、资料编号、选中标签和正在运行的阶段。

### Secondary
- **证据青绿**（`teal`）：已完成阶段与输入光标；相关的浅青绿局部底色用于证据定位和假设区。
- **错误红**（`error`）：错误提示文字和移除操作的悬停反馈；具体审查状态同时包含文字。

### Neutral
- **深灰蓝正文**（`ink`）：正文与字段内容。
- **次要灰蓝**（`muted`）：阅读范围、运行说明与辅助操作。
- **灰蓝画布**（`canvas`）：页面背景。
- **纸白内容区**（`white`）：资料、表格、输入与选题内容区。
- **浅灰蓝边界**（`line`）：容器轮廓和行分隔。
- **浅青蓝洗色**（`wash`）：小型上下文标签。

**The State With Text Rule.** 颜色伴随状态文字；示例、草案、待核验和错误不能仅靠色彩辨认。

## Typography

**Display / Body Font:** 同一套 `Segoe UI`、`Microsoft YaHei`、sans-serif 系统字体。项目没有独立展示字体、外部字体文件或专用等宽字体。

文字层级服务科研阅读。主标题沿用正文家族，通过字号、字重和稍紧的字距建立层级。

### Hierarchy
- **Headline**：主页面标题；移动端缩小到（24px）。
- **Title**：资料与结果区标题；选题标题使用（20px），三级标题使用（16px）。
- **Body**：一般说明、输入与研究文字；结果摘要限制在（90ch），证据段落限制在（85ch）。
- **Label**：字段与标签页使用较重字重；辅助说明与标签多为（12px），引用按钮为（11px）。
- **Table**：表格正文使用独立的紧凑角色；表头为（12px）。来源编号与引用编号启用 tabular-nums。

## Layout

桌面为双区域网格：左栏（300px），右栏 `minmax(0, 1fr)`；主区最大宽度（1560px），内边距（30px 36px 60px）。左栏内边距（26px 24px）。资料清单与候选实验内容在宽屏各自使用两列。

（1100px）及以下左栏缩为（270px），资料与选题内部改为单列，主区内边距（25px 24px）。（700px）及以下左栏位于主区上方，四阶段进度变为两列；主区内边距（23px 18px 40px），结果标题和导出链接上下排列。

宽对比表保留（780px）最小宽度，在本地容器内横向滚动；标签页也允许横向滚动。长资料名和证据正文允许任意位置断行。布局使用（8px）小间距、（18px）字段间距及（22–24px）内容间距，避免挤压材料的阅读范围。

## Elevation & Depth

实际实现没有 box-shadow。深度由页面、设置栏、白色内容区和轻浅状态底色产生；细边界区分相邻内容。证据定位使用背景洗色，键盘焦点使用轮廓，不依靠阴影表示交互状态。

**The Flat Workbench Rule.** 继续使用平面内容区与细分隔，保持资料和结论的阅读优先级。

## Shapes

输入和按钮使用温和圆角，内容容器使用稍大的圆角。标签与引用更紧凑；进度点为圆形。细边界通常为（1px），选中标签页以底边线（3px）标识。表格由横向分隔组织，不逐格围出重网格。

## Components

### Buttons
- 主操作为通栏科研蓝实底、白字，悬停深蓝（`#103e61`）。次要操作为白底细描边，悬停浅灰蓝（`#e7f0f4`）。
- 全局背景过渡为（0.15s）。禁用状态使用等待光标和（0.65）透明度。
- 可见键盘焦点为（3px）青绿轮廓（`#369889`），外偏移（3px）。

### Inputs / Fields
- 白底、细边界（`#b9cbd5`）、完整宽度，文本区域可垂直调整高度。
- 字段标题独立于占位文本；输入光标采用证据青绿。焦点沿用统一轮廓。

### Navigation
- 标签页为无圆角平面文字按钮。未选中为次要灰蓝，选中为科研蓝与底边线，悬停强化文字色。
- 实现支持左右箭头、Home、End；当前页保留 Tab 停靠点，面板归属由 ARIA 关联。

### Chips / Evidence References
- 上下文标签为小型浅底色矩形；示例状态使用独立浅紫灰配色。
- 引用为紧凑青绿按钮。点击转入来源证据页，目标证据获得焦点、浅底色和滚动定位；来源编号保持可追溯性。

### Cards / Containers
- 资料容器和选题内容区为白底、细边界、无阴影；选题内边距（23px 26px）。
- 证据以带底部分隔的阅读行呈现。假设区使用浅青绿底色，不赋予已验证结论的外观。

### Results / States
- 输入修改立即显示失效提示、清除旧结果与进度、隐藏下载。加载、失败、示例和真实分析草案各有文字说明。
- 面板入场为（0.2s）轻微裁切展开；`prefers-reduced-motion` 关闭动画和过渡。

## Do's and Don'ts

### Do:
- **Do** 保留来源编号、材料阅读范围、示例与草案状态的文字层级。
- **Do** 延续科研蓝行动、青绿证据、中性背景的颜色分工。
- **Do** 用细分隔、行和表格承载密集资料，并保留局部滚动与长文本换行。
- **Do** 保留所有可操作元素的可见键盘焦点和减少动态效果偏好。

### Don't:
- **Don't** 给平面研究内容区添加装饰性阴影或夸大的展示标题。
- **Don't** 在研究输入已修改后继续显示旧结果的下载入口或完成标记。
- **Don't** 将候选假设、摘要转述或示例资料表现为已验证的论文结论。