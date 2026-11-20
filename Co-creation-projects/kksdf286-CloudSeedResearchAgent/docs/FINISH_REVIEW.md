disposition: ship

缺少输入：未提供批准视觉 comp 或外部 QUALITY BAR 页面；按已确认的科研处理工作台契约与课程交付质量要求审查。未使用浏览器；论文事实、后端与下载行为不属于本次截图/源码审查的核验结论。

## persistence

pass — `PRODUCT.md` 存在，明确用户、任务、Python 本地服务/CLI、研究草案和资料阅读范围。`ui/index.html` 的 body 首项保存了 THESIS、OWN-WORLD、STORY、FIRST VIEWPORT、FORM 与 FINISH；FORM 的 `direction 5 / seed 24a53df1` 与交接输入一致。新视觉世界的 `DESIGN.md` 应在本审查之后由 documenter 记录，其此时缺席不是缺陷。未提供批准 comp，故不把 comp 审批记录当成本次通过的证据。

## fidelity

| 元素/承诺 | 裁定 | 证据与影响 |
|---|---|---|
| THESIS：把可比较证据转为可证伪实验 | match | 资料、对比、选题、证据、审查是明确的工作顺序；mobile-results 显示候选假设及最小验证实验结构。 |
| OWN-WORLD：灰蓝、科研蓝、克制青绿 | match | 两个中性层分隔设置和工作区；蓝色用于主要操作与选中状态，青绿用于进度与证据。 |
| TYPE | match | 系统 sans、紧凑字号层级、数据表数字对齐适合 Operate 模式；标题没有营销式展示字或夸张比例。 |
| MATERIAL | match | 工作台使用平面表单、行和数据表；没有假纸、假金属、CSS 压印或以渐变替代真实资产。该方向未承诺图片区域。 |
| FIRST VIEWPORT：左研究设置，右资料及结果 | match / adaptation | desktop 保留 300px 设置栏与右工作区；700px 以下折成上下顺序，mobile 显示完整设置和四阶段网格。重排由移动端可读性要求支持。desktop 当前选中证据页而非对比页，是已有 tab 的操作状态。 |
| 层级与内容密度 | match | 输入 → 主操作 → 进度，右侧资料 → 结果标题 → tabs → 内容；资料使用行而非重复图标卡片。mobile-results 的长候选标题换行且没有可见整页横溢。源码将宽表格限制在本地横向滚动容器。 |
| STORY：输入、分析、追溯、导出 | match（F1 resolved） | 修正后的 `input-changed.png` 明确显示“当前输入尚未分析”“原结果已失效”，四阶段完成标记清除。源码的统一 `invalidateResult` 清空 result/currentJob/面板，隐藏下载并移除 href；问题、资源、添加、移除和JSON替换均调用。运行开始及失败也不保留旧结果。 |
| 分析方式与结果模式语义 | match（F2 resolved） | 修正后的 mobile 可见“下一次分析方式”，其设置与已完成结果的真实分析标签分别表述。真实结果仍标为草案、待核验。 |
| 研究诚实性 | match（限定范围） | 源清单明确“摘要人工转述/未导入全文”；证据页明确不是原文引句，摘要不能代表全文精读；结果称草案、待核验，候选新颖性待核实，资源框说明尚无专家独立标注数据。此裁定不验证论文中的数字或论断。 |
| tab detector：border-accent-on-rounded | match | `.tab` 为无圆角按钮，3px bottom border 标识选中页；截图为常规 tabs 下划线。它不是卡片/提示/列表的粗彩色侧边框，本警告不成立。 |
| 键盘与焦点 | match（F3 resolved） | `evidence-focus.png` 显示 P1-E1 的可见焦点框；源码对目标 evidence article 使用 `tabindex=-1` 与 `focus({preventScroll:true})`。`import-focus.png` 显示PDF按钮焦点；PDF/JSON均为真实button并继承统一 focus-visible，隐藏文件输入退出Tab顺序，运行期间按钮禁用。 |
| 正文/控制文字对比度 | match（F4 resolved） | `.remove` 的后置生效规则为 `var(--muted)` / `#526679`，白底比值5.94:1；资料行保持次要文字层级。 |

## ceiling

reached — 在提供的课程交付质量要求下，工作台已使用其原生组织方式：设置栏、资料行、对比表、来源编号、候选实验、审查反馈与状态标记。没有为快速课程工具添加未承诺的图片、装饰深度或营销结构的必要。批准 comp、外部 QUALITY BAR 未提供，不能声称通过与其的相似度比较。

## material_fixes

| ID | 修复验收（按原清单，不展开新缺陷） | 最终 verdict |
|---|---|---|
| F1 | 输入变化截图显示当前尚未分析和旧结果失效、完成标记清除；源码独立确认结果与下载统一清空，覆盖问题/资源/资料及运行失败路径。清除旧结果是原修复要求允许的明确实现。 | resolved |
| F2 | 移动与桌面修正版截图可见“下一次分析方式”，结果侧仍保留本次模式与待核验说明。 | resolved |
| F3 | 证据截图显示目标焦点框，导入截图显示PDF按钮焦点框；源码确认JSON采用同一button与focus-visible方案。 | resolved |
| F4 | 生效文字色为#526679，白底5.94:1，高于4.5:1；截图显示其仍为次要操作。 | resolved |

remaining: clear。修复批次在所提供截图中未出现既有要求的可见回归。最终 disposition: ship。

## keep

保持资料阅读范围、候选假设与待核验标记，保留科研工作台的克制层级、可追溯证据和移动端结构重排；修复状态与焦点时不要稀释这些信息。
