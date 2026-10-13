# GitHub 部署操作手册

> 记录如何将本项目推送到 GitHub（`https://github.com/0609x/PubMed-Research-Agent`），
> 供日常更新与故障排查使用。本文档本身也随项目一起提交。

## 1. 仓库信息

- 本地项目：`C:\Users\xqg\Documents\New project（AI）\PubMed-Research-Agent`
- GitHub 仓库：`https://github.com/0609x/PubMed-Research-Agent`
- 本地分支：`main`（跟踪 `origin/main`）
- 远端（remote）：`origin` → `https://github.com/0609x/PubMed-Research-Agent.git`

## 2. 前置条件

1. 本机已安装 Git，并能访问 GitHub（HTTPS 凭据已保存）。
2. 本地仓库已存在并关联远端（首次克隆/推送除外）。

查看当前关联的远端：

```powershell
cd "C:\Users\xqg\Documents\New project（AI）\PubMed-Research-Agent"
git remote -v
```

## 3. 日常更新流程（每次修改后推送）

```powershell
cd "C:\Users\xqg\Documents\New project（AI）\PubMed-Research-Agent"

# 1. 查看改动（确认要提交的内容）
git status

# 2. 查看具体差异（可选）
git diff

# 3. 暂存全部改动（或 git add <具体文件>）
git add -A

# 4. 提交前安全检查：确认没有把 .env / 数据库 / 缓存文件提交进去
git diff --cached --name-only | findstr /i "\.env node_modules __pycache__ \.pytest_cache \.db data\cache"

# 5. 提交（type 用 feat / fix / docs / refactor / test / chore）
git commit -m "feat: 描述本次改动"

# 6. 推送到 GitHub
git push origin main
```

提交信息规范：

| 类型 | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 文档更新 |
| `refactor` | 代码重构 |
| `test` | 测试相关 |
| `chore` | 依赖、配置等杂项 |

## 4. 本次操作记录（2026-08-14）

将项目从旧结构重构为「backend / frontend / data / deploy / docs」五文件夹结构后推送：

```powershell
git remote -v                                   # 确认 origin 指向 0609x/PubMed-Research-Agent
git status                                      # 确认变更：旧目录删除 + backend/ 新增
# 补充 .gitignore 忽略 .pytest_cache/
git add -A
git diff --cached --name-only                   # 123 个文件，无敏感文件
git commit -m "feat: 重构为五文件夹结构，新增RAG混合检索、知识图谱、研究看板、翻译与排序筛选功能"
git commit -m "docs: 添加GitHub部署操作手册"     # （第二个提交，本手册）
git push origin main
```

## 5. 常见问题

### 5.1 fatal: detected dubious ownership in repository

原因：仓库 `.git` 目录的所有者与当前 Git 用户不一致（例如项目由其他账户/沙箱创建）。

解决：

```powershell
git config --global --add safe.directory "C:/Users/xqg/Documents/New project（AI）/PubMed-Research-Agent"
```

### 5.2 fatal: unable to access ... schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS

原因：当前进程（如某些自动化终端）无法访问 Windows 凭据管理器，拿不到 GitHub 凭据。

解决：**在你自己登录的交互式 PowerShell / CMD 终端中执行** `git push`，凭据管理器会正常弹窗或使用已保存的凭据。

### 5.3 warning: LF will be replaced by CRLF

无害提示（Windows 换行符）。不影响功能，可忽略；也可在仓库根添加 `.gitattributes` 统一换行风格。

### 5.4 推送到错误的仓库 / 需要更换远端

```powershell
git remote set-url origin https://github.com/你的用户名/PubMed-Research-Agent.git
```

### 5.5 强制覆盖远端历史（慎用，仅本地历史混乱时）

```powershell
git push -f origin main
```

## 6. 安全注意事项

- `.env`（含真实密钥）已在 `.gitignore` 中忽略，**严禁** `git add .env`。
- 提交前用 `git diff --cached --name-only` 检查暂存清单。
- 数据库文件（`*.db`）、缓存（`data/cache/`、`.pytest_cache/`）、前端 `node_modules/` 均不提交。
- 若误提交敏感信息：立即在 GitHub 上删除该提交并重置/轮换密钥，不要只删文件。

## 7. 查看推送结果

```powershell
git log --oneline -5     # 本地提交历史
git status               # 应显示 working tree clean 或仅未跟踪文件
```

也可在浏览器打开 `https://github.com/0609x/PubMed-Research-Agent/commits/main` 确认提交已上线。
