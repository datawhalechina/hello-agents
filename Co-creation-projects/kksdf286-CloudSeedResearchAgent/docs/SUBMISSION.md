# GitHub 作业提交

代码、README、依赖列表、运行示例、来源说明和测试均包含在项目目录中。不提交真实 `.env`、私有 PDF 或整套个人知识库。

## 提交到 Hello-Agents 共创项目

1. 在 GitHub Fork `datawhalechina/hello-agents`，克隆自己的 Fork。
2. 创建分支，将本项目目录放入 `Co-creation-projects/kksdf286-CloudSeedResearchAgent/`。复制时不复制本项目 `.git`、`__pycache__`、`.env` 和本地产生的 `outputs/`。
3. 在该 Fork 中执行测试和离线示例，确认 README 的相对链接有效。
4. 提交分支，再从 Fork 向上游创建 PR。按课程格式使用标题：`[毕业设计] CloudSeedResearchAgent - 人工增雨科研选题助手`。

```powershell
git switch -c feature/cloudseed-research-agent
git add Co-creation-projects/kksdf286-CloudSeedResearchAgent
git commit -m "feat: 添加 CloudSeedResearchAgent 毕业设计项目"
git push -u origin feature/cloudseed-research-agent
```

## 独立仓库

在 GitHub 创建自己的空仓库，将本项目作为仓库根目录。若本地尚未初始化：

```powershell
git init -b main
git add .
git commit -m "Add runnable cloud-seeding research assistant"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
git push -u origin main
```

若 Git 要求作者身份，设置自己的真实 `user.name` 和 `user.email`；使用仓库级配置即可。认证使用你自己的 GitHub 登录，不把 token 写进代码、README 或仓库 URL。

## 可用的 PR 描述

新增 CloudSeedResearchAgent，围绕人工增雨作业条件识别，通过四个 HelloAgents 角色完成证据提取、跨论文比较、候选实验设计和审查。提供本地网页与 CLI，支持文本/PDF/JSON 资料、Crossref 检索，以及 Markdown、BibTeX 和 Obsidian 导出。

内置三篇论文与一份标准的短转述，明确阅读范围；离线 fixture 与真实模型调用分开标记。已运行单元测试和真实 DeepSeek 示例，未训练气象识别模型或声称科研新颖性。
