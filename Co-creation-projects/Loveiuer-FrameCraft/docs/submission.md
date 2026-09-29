# FrameCraft 共创提交记录

- 作者：[Loveiuer](https://github.com/Loveiuer)
- 上游：[datawhalechina/hello-agents](https://github.com/datawhalechina/hello-agents)
- Fork：[Loveiuer/hello-agents](https://github.com/Loveiuer/hello-agents)
- 项目目录：`Co-creation-projects/Loveiuer-FrameCraft/`
- 提交分支：`feat/loveiuer-framecraft`
- 许可证：CC BY-NC-SA 4.0，与上游共创目录要求一致。

第 16 章允许 Python 脚本或 Notebook；共创目录 README 另将 `main.ipynb` 列为必需。本项目同时提供 `main.py` 和离线演示 Notebook，满足两处说明。PR 的实际状态和是否合并以 GitHub 页面为准。

## 已完成的交付

- [x] 提供 CLI、本地 Web 工作台、Notebook 和依赖说明。
- [x] 内置 104 节点完整样例及 6 节点在线验收样例。
- [x] 离线运行、44 项单元测试和 8 项浏览器检查通过。
- [x] 生成的 React / TypeScript 项目通过构建及桌面、手机运行检查。
- [x] 6 节点样例完成四个真实 HelloAgents 角色调用，约 118.5 秒，保留轨迹与报告。
- [x] 提供源码、截图、架构、答辩和实际验证记录。
- [x] 明确 demo 不调用模型，节点覆盖不等于视觉还原，按钮没有业务交互。
- [x] 使用 GitHub 作者身份，排除环境文件、密钥、缓存、依赖目录和重复运行产物。
- [x] 提交内容小于 5 MB。

具体命令与证据见 [validation.json](validation.json)、[evaluation.json](evaluation.json)、[browser-report.json](browser-report.json) 和 [在线轨迹](live-smoke/agent-trace.json)。提交副本的测试和 Notebook 执行情况另记于 `submission-validation.json`。

## 尚未验证或未完成

- [ ] 在完全独立的环境安装并验证全部应用依赖；当前应用测试使用已有开发环境，Notebook 使用独立执行环境。
- [ ] 用可访问的真实 Figma Frame 和 Token 完成远程导入验收。
- [ ] 证明大设计的在线稳定性。104 节点样例此前在线出现模型请求或输出契约错误，JSON 模式修正后未重测完整样例。
- [ ] 建立 Figma 原图与生成页面的像素差异评估。
- [ ] 上游维护者完成 PR 评审与合并。

这些事项没有被记为测试通过，离线测试和桩对象不能替代外部服务验证。

## 提交内容

保留 `README.md`、`main.py`、`main.ipynb`、`evaluate.py`、`requirements.txt`、`requirements-notebook.txt`、`.env.example`、`.gitignore`、`LICENSE`、`d2c/`、`web/`、`data/`、`tests/` 和 `docs/`。

不提交 `.env`、虚拟环境、`node_modules/`、缓存、原始调试日志或 `outputs/`。项目 `.gitignore` 显式保留 `tests/test_*.py`，避免被上游根目录的忽略规则遗漏。

PR 标题为：

```text
[毕业设计] FrameCraft - Figma 设计转 React 的多智能体助手
```

PR 正文说明输入范围、四角色职责、受控编译器、实际验证和上述限制，不宣称任意设计一键生成完整业务应用。
