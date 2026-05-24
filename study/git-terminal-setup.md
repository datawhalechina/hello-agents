# Git 终端配置记录

本文记录本机 PowerShell / Git 终端相关配置，方便以后复现或排查。

## 1. Git 快捷命令

已在 PowerShell profile 中添加 Git 快捷函数。

配置文件位置：

```powershell
C:\Users\Lenovo\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1
```

已添加的快捷命令：

```powershell
gst    # git status
ga     # git add
gaa    # git add --all
gco    # git checkout
gb     # git branch
gd     # git diff
gds    # git diff --staged
glog   # git log --oneline --graph --decorate
gpl    # git pull
gpsh   # git push
gcmsg  # git commit -m
```

修改后可通过下面命令立即重新加载：

```powershell
. $PROFILE
```

## 2. 当前仓库 remote 检查

检查当前仓库 remote 时，`git remote -v` 因为 Git 的 dubious ownership 保护被拦截。

提示内容大意：

```text
fatal: detected dubious ownership in repository at 'D:/front/agent'
```

如果确认该目录可信，可以执行：

```powershell
git config --global --add safe.directory D:/front/agent
```

随后直接读取 `.git/config`，发现当前仓库没有配置 remote 地址，也就是没有 `[remote "origin"]` 配置段。

## 3. 推荐并安装的终端 Git 插件

推荐的工具包括：

```text
posh-git        PowerShell Git 状态提示和 Git 补全
Terminal-Icons  终端文件列表图标
PSReadLine      命令历史预测和补全体验
Oh My Posh      美化 prompt，并显示 Git 分支、状态、环境信息
delta           美化 git diff
lazygit         终端 Git 图形界面
```

推荐安装命令：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Scope CurrentUser -Force
Set-PSRepository -Name PSGallery -InstallationPolicy Trusted

Install-Module posh-git -Scope CurrentUser -Force -AllowClobber
Install-Module Terminal-Icons -Scope CurrentUser -Force -AllowClobber
Install-Module PSReadLine -Scope CurrentUser -Force -AllowClobber

winget install JanDeDobbeleer.OhMyPosh --source winget
winget install dandavison.delta
winget install JesseDuffield.lazygit
```

Git diff 美化配置：

```powershell
git config --global core.pager delta
git config --global interactive.diffFilter "delta --color-only"
git config --global delta.navigate true
git config --global merge.conflictstyle zdiff3
```

## 4. Oh My Posh 主题

下载过的 Oh My Posh 主题保存位置：

```powershell
C:\Users\Lenovo\.config\oh-my-posh\themes
```

已下载过的主题：

```text
catppuccin_mocha
tokyonight_storm
gruvbox
pure
slim
clean-detailed
agnoster
agnoster-local
```

官方主题预览页：

```text
https://ohmyposh.dev/docs/themes
```

当前默认主题设置为：

```powershell
$env:POSH_THEME_NAME = 'agnoster-local'
```

其中 `agnoster-local` 是基于官方 `agnoster` 的本地修正版，用来解决部分图标在当前终端字体下显示为空白的问题。

## 5. 字体设置

为了让 `agnoster` 这类 Powerline / Nerd Font 主题正常显示，已设置终端字体为：

```text
MesloLGM Nerd Font Mono
```

已尝试写入这些配置：

```text
VS Code:
C:\Users\Lenovo\AppData\Roaming\Code\User\settings.json

Cursor:
C:\Users\Lenovo\AppData\Roaming\Cursor\User\settings.json

Windows Terminal:
C:\Users\Lenovo\AppData\Local\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json
```

VS Code / Cursor 中的配置项：

```json
"terminal.integrated.fontFamily": "MesloLGM Nerd Font Mono"
```

Windows Terminal 中的配置项：

```json
"profiles": {
  "defaults": {
    "font": {
      "face": "MesloLGM Nerd Font Mono"
    }
  }
}
```

修改字体后，需要关闭并重新打开终端面板。VS Code / Cursor 中可以执行：

```text
Ctrl + Shift + P -> Developer: Reload Window
```

## 6. 常见问题

### CONFIG NOT FOUND

这个提示来自 Oh My Posh，表示主题配置路径不存在。

原因通常是：

```powershell
$env:POSH_THEMES_PATH
```

为空，导致主题路径拼错。

当前处理方式是在 profile 中显式设置主题目录：

```powershell
$env:POSH_THEMES_PATH = Join-Path $HOME '.config\oh-my-posh\themes'
```

### 图标显示成问号或空白

这通常不是 Git 问题，而是当前终端字体不支持主题使用的图标字符。

处理方式：

```text
1. 安装 Nerd Font，比如 Meslo。
2. 把 VS Code / Cursor / Windows Terminal 的终端字体改成 MesloLGM Nerd Font Mono。
3. 如果仍有个别图标空白，使用本地修正版主题 agnoster-local。
```

### PSReadLine 在非交互环境报错

PowerShell profile 中已把 PSReadLine 设置包进 `try/catch`，避免在非交互命令执行环境中刷错误。

当前写法：

```powershell
try { Set-PSReadLineOption -PredictionSource History -ErrorAction Stop } catch {}
try { Set-PSReadLineOption -PredictionViewStyle ListView -ErrorAction Stop } catch {}
```

## 7. 后续切换主题

打开 PowerShell profile：

```powershell
notepad $PROFILE
```

修改这一行：

```powershell
$env:POSH_THEME_NAME = 'agnoster-local'
```

例如切换成 `pure`：

```powershell
$env:POSH_THEME_NAME = 'pure'
```

保存后执行：

```powershell
. $PROFILE
```


