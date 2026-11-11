# Hello-Agents 仓库适配

## 项目边界

目录按照共创区要求命名，包含 `README.md`、根目录 `requirements.txt`、`main.ipynb` 和可选的 Web/CLI 入口 `main.py`。安装、运行与停止命令统一维护在 [README](../README.md)，避免多份命令漂移。

- 从根目录依赖清单安装固定版本的 `hello-agents`，不依赖其他共创项目或本机教程目录。
- `FunctionCallAgent` 执行面试工具循环；`SimpleAgent` 处理结构化分析、独立评分与参考答案；`HelloAgentsLLM` 的兼容客户端负责流式示范作答。
- 业务状态、证据核验、幂等和失败恢复由本项目负责，不改动上游框架或其他项目。
- Web 与 Notebook 使用同一 API。路径由入口定位，允许从其他工作目录调用，不需要手动配置 `PYTHONPATH`。
- Windows 使用 `.cmd` 包装，macOS/Linux 使用 POSIX shell 包装，均调用 `main.py`；`--stop` 通过本机实例令牌正常关闭服务。

## 贡献规范

依据 [共创说明](../../README.md)与[项目模板](../../EXAMPLE-ProjectTemplate/README.md)维护必需文件；从本文件位置访问共创区应使用上述相对路径。

项目 `.gitignore` 放行自身 `backend/tests/test_*.py`，兼容上游测试文件忽略规则。`.gitattributes` 固定 shell/Python/文档为 LF，Windows 包装脚本为 CRLF。

`.env`、临时配置文件、运行状态、SQLite、个人材料、依赖和构建产物不提交。Notebook 仅保留可复现代码，不保留输出、内核绝对路径或真实模型调用内容。项目内不放置无效的嵌套 GitHub Actions 工作流，也不修改上游 CI。

所有演示简历和 JD 均为虚构，仅保留 Agent 开发稳定工作区 ID，通过幂等插入避免重复；真实模型逐轮示范作答并独立复盘，个人工作区继续使用独立 ID。

## 共创规范核对

核对日期：2026-10-22。依据上游 [共创区说明](https://github.com/datawhalechina/hello-agents/blob/main/Co-creation-projects/README.md)、[项目模板](https://github.com/datawhalechina/hello-agents/blob/main/Co-creation-projects/EXAMPLE-ProjectTemplate/README.md)和[毕业设计指南](../../../docs/chapter16/第十六章%20毕业设计.md)。

| 要求                  | 本项目对应内容                                                       |
| ------------------- | ------------------------------------------------------------- |
| 目录为 GitHub 用户名-项目名称 | `WBoxian-OfferNote`，位于 `Co-creation-projects/`                |
| 必需入口与依赖文件           | 根目录 `README.md`、`requirements.txt`、`main.ipynb`；另提供 `main.py` |
| 项目简介、核心功能、技术栈       | README 对应章节，说明 HelloAgents 的职责与业务代码边界                         |
| 安装、配置与运行            | README 给出 Windows、macOS/Linux 安装、前端构建、模型配置及启动/停止命令            |
| 使用示例                | README 六步流程与六张截图，标明虚构材料、真实模型历史回放及单次评分边界                       |
| 作者信息                | 公开 GitHub 账号 `@WBoxian` 与作者指定的联系邮箱，不附真实姓名                      |
| 共创许可证               | 遵循仓库 `LICENSE.txt` 的 CC BY-NC-SA 4.0                          |
| 可复现与提交卫生            | 固定框架版本、前端锁文件；不提交密钥、个人材料、数据库、依赖、构建产物或 Notebook 输出              |

共创区说明明确要求 CC BY-NC-SA 4.0；项目模板中的 MIT 是与该要求不一致的占位内容。本项目遵循共创区说明和仓库根许可证。

本次核对修正了 README 对不存在的停止脚本的引用，改为实际支持的 `main.py --stop`；明确 Web 演示必须配置真实模型，并对齐流式作答的框架说明。Notebook 的离线演示仅验证业务闭环，不作为真实模型效果证据。

以上为本地提交准备核对，不代表上游已审查或接收；Fork、推送、PR 与维护者 review 仍属后续贡献流程。
