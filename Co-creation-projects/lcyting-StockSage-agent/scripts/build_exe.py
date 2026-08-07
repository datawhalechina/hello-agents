"""
智能股票分析助手 — exe 打包脚本

用法：
    # 一键打包（从项目根目录执行）
    python scripts/build_exe.py

    # 仅检查环境不打包
    python scripts/build_exe.py --check

    # 强制重新 npm build（frontend/dist 已存在时默认跳过，可加速打包）
    python scripts/build_exe.py --rebuild-frontend
    # 或环境变量（PowerShell: $env:BUILD_EXE='1'; python scripts/build_exe.py）
    # 离线打包若不想拉取 tensorboard：BUILD_EXE_SKIP_TENSORBOARD=1（可能出现 torch 相关 WARNING，可忽略）

打包结果：
    dist_exe/stock_analyzer.exe       # 主程序
    dist_exe/.env.example             # 配置模板（需重命名为 .env 并填入 API Key）
    dist_exe/data/                   # 数据目录（自动创建）
"""

import os
import sys
import platform
import shutil
import subprocess
from pathlib import Path

# Windows 控制台默认 GBK，直接 print Unicode 勾选符号会触发 UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
DIST_DIR = PROJECT_ROOT / "dist_exe"
BACKEND_DIR = PROJECT_ROOT / "backend"

# Windows 下 npm 实际是 npm.cmd
_NPM_CMD = "npm.cmd" if platform.system() == "Windows" else "npm"


def ensure_tensorboard_for_pyinstaller_scan() -> None:
    """PyInstaller 分析 PyTorch 时会执行 import torch.utils.tensorboard，依赖可选包 tensorboard。

    未安装时仅打印 WARNING，不影响生成的 exe（本应用运行时不需要 TensorBoard）。
    默认尝试 pip install tensorboard 以消除告警；离线打包可设环境变量 BUILD_EXE_SKIP_TENSORBOARD=1 跳过。
    """
    if os.getenv("BUILD_EXE_SKIP_TENSORBOARD", "").lower() in ("1", "true", "yes"):
        print(
            "[*] 已跳过 tensorboard 检查（BUILD_EXE_SKIP_TENSORBOARD）；"
            "若出现 torch.utils.tensorboard 相关 WARNING 可忽略"
        )
        return
    try:
        import tensorboard  # noqa: F401
        return
    except ImportError:
        pass
    print("[*] 正在安装 tensorboard（供 PyInstaller 分析 torch 时使用，消除可选模块告警）...")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "tensorboard"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(
            "[!] tensorboard 安装失败，打包仍会继续；"
            "可能出现 ModuleNotFoundError: tensorboard 类 WARNING，不影响本程序运行"
        )
    else:
        print("[OK] tensorboard 已就绪")


def _force_rebuild_frontend() -> bool:
    """frontend/dist 已存在时，是否仍执行 npm run build"""
    if "--rebuild-frontend" in sys.argv:
        return True
    v = os.getenv("BUILD_EXE", "").lower()
    return v in ("1", "true", "yes", "rebuild")


def check_env():
    """检查打包所需的工具是否可用"""
    issues = []

    # 检查 npm
    try:
        subprocess.run([_NPM_CMD, "--version"], capture_output=True, check=True)
        print("[OK] npm 可用")
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append("npm 未安装或不在 PATH 中（需 Node.js）")

    # 检查 PyInstaller
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "--version"],
                       capture_output=True, check=True)
        print("[OK] PyInstaller 可用")
    except (subprocess.CalledProcessError, FileNotFoundError):
        issues.append("PyInstaller 未安装，请执行: pip install pyinstaller")

    # 检查前端是否已构建
    if not (FRONTEND_DIR / "dist" / "index.html").exists():
        issues.append("前端未构建，将自动构建")

    return issues


def build_frontend():
    """构建 Vue3 前端为静态文件"""
    print("\n[1/3] 构建前端...")
    env = os.environ.copy()
    result = subprocess.run(
        [_NPM_CMD, "run", "build"],
        cwd=str(FRONTEND_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[ERR] 前端构建失败:\n{result.stderr}")
        return False
    print(f"[OK] 前端构建完成 -> {FRONTEND_DIR / 'dist'}")
    return True


def build_exe():
    """使用 PyInstaller 打包为 exe"""
    print("\n[2/3] PyInstaller 打包...")
    ensure_tensorboard_for_pyinstaller_scan()

    # 清理旧的构建产物
    for _d in [DIST_DIR, PROJECT_ROOT / "build"]:
        if _d.exists():
            shutil.rmtree(_d)

    # PyInstaller 参数
    pyi_args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "stock_analyzer",
        "--onefile",
        "--console",
        "--clean",
        "--noconfirm",
        f"--distpath={DIST_DIR}",
        f"--workpath={PROJECT_ROOT / 'build' / 'pyinstaller'}",
        f"--specpath={PROJECT_ROOT / 'build'}",
        # 使 PyInstaller 分析阶段能解析 backend 下的 app.* 包（否则 hidden-import 报 not found）
        f"--paths={BACKEND_DIR}",
        # 入口
        str(PROJECT_ROOT / "run_exe.py"),
        # 添加数据目录
        "--add-data", f"{FRONTEND_DIR / 'dist'}{os.pathsep}frontend/dist",
        "--add-data", f"{PROJECT_ROOT / 'skills'}{os.pathsep}skills",
        "--add-data", f"{PROJECT_ROOT / 'agents'}{os.pathsep}agents",
        "--add-data", f"{PROJECT_ROOT / 'HelloAgents Optimized' / 'hello_agents'}{os.pathsep}hello_agents",
        "--add-data", f"{BACKEND_DIR}{os.pathsep}backend",
        # 隐藏导入（动态导入的模块）
        "--hidden-import", "app.api.market",
        "--hidden-import", "app.api.financial",
        "--hidden-import", "app.api.news",
        "--hidden-import", "app.api.screener",
        "--hidden-import", "app.api.watchlist",
        "--hidden-import", "app.api.simulation",
        "--hidden-import", "app.api.analysis",
        "--hidden-import", "app.api.buffett",
        "--hidden-import", "app.api.preferences",
        "--hidden-import", "app.services.market_service",
        "--hidden-import", "app.services.news_service",
        "--hidden-import", "app.services.screener_service",
        "--hidden-import", "app.services.analysis_service",
        "--hidden-import", "app.services.watchlist_service",
        "--hidden-import", "app.services.simulation_service",
        "--hidden-import", "app.services.buffett_service",
        "--hidden-import", "app.services.preference_service",
        "--hidden-import", "app.services.mx_timed_cache",
        "--hidden-import", "app.services.dashboard_warmup",
        "--hidden-import", "app.models.database",
        "--hidden-import", "app.models.preference",
        "--hidden-import", "app.models.report",
        "--hidden-import", "app.utils.response",
        "--hidden-import", "app.utils.mx_http",
        "--hidden-import", "app.utils.mx_quota",
        "--hidden-import", "app.utils.mx_fixture",
        "--hidden-import", "app.utils.mock_trading_normalize",
        "--hidden-import", "agents.agent_system",
        "--hidden-import", "agents.coordinator_agent",
        "--hidden-import", "agents.data_analysis_agent",
        "--hidden-import", "agents.sentiment_agent",
        "--hidden-import", "agents.advisor_agent",
        "--hidden-import", "agents.general_advisor_agent",
        "--hidden-import", "agents.tools.mx_data_tool",
        "--hidden-import", "agents.tools.mx_search_tool",
        # 常用依赖
        "--hidden-import", "fastapi",
        "--hidden-import", "uvicorn",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "pydantic",
        "--hidden-import", "sqlalchemy",
        "--hidden-import", "aiosqlite",
        "--hidden-import", "httpx",
        "--hidden-import", "pandas",
        "--hidden-import", "dotenv",
        "--collect-all", "openpyxl",
    ]

    result = subprocess.run(pyi_args, cwd=str(PROJECT_ROOT))
    if result.returncode != 0:
        print("[ERR] PyInstaller 打包失败")
        return False
    print(f"[OK] 打包完成 -> {DIST_DIR / 'stock_analyzer.exe'}")
    return True


def copy_assets():
    """复制配置模板到输出目录"""
    print("\n[3/3] 复制配置文件...")

    # 复制 .env 模板
    env_template = PROJECT_ROOT / ".env"
    if env_template.exists():
        # 清理敏感信息
        import re
        content = env_template.read_text(encoding="utf-8")
        # 清除真实 API Key
        content = re.sub(r'(LLM_API_KEY=).+', r'\1your-deepseek-api-key-here', content)
        content = re.sub(r'(MX_APIKEY=).+', r'\1your-mx-apikey-here', content)
        content = re.sub(r'(JWT_SECRET_KEY=).+', r'\1change-this-to-a-random-secret-key', content)
        # 与 exe 默认端口、自动打开的浏览器地址一致（127.0.0.1:5174/dashboard）
        content = re.sub(r'^BACKEND_PORT=.*$', 'BACKEND_PORT=5174', content, flags=re.MULTILINE)
        (DIST_DIR / ".env.example").write_text(content, encoding="utf-8")
        print("[OK] .env.example 已生成（请重命名为 .env 并填入 API Key）")

    # 创建 data 目录
    (DIST_DIR / "data").mkdir(exist_ok=True)
    print("[OK] data/ 目录已创建")


def main():
    print("=" * 50)
    print("  智能股票分析助手 — exe 打包工具")
    print("=" * 50)

    # 切换到项目根目录
    os.chdir(str(PROJECT_ROOT))

    # 环境检查
    issues = check_env()
    if "--check" in sys.argv:
        if issues:
            print(f"\n[!] 发现 {len(issues)} 个问题:")
            for i in issues:
                print(f"  - {i}")
        else:
            print("\n[OK] 打包环境就绪")
        return

    # 自动安装 PyInstaller
    for i in issues:
        if "PyInstaller" in i:
            print("[*] 正在安装 PyInstaller...")
            subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"],
                           check=True)
            issues.remove(i)
            break

    if issues:
        non_critical = [i for i in issues if "未构建" not in i]
        if non_critical:
            print(f"\n[ERR] 请先解决以下问题:")
            for i in non_critical:
                print(f"  - {i}")
            return

    # 构建前端
    if not (FRONTEND_DIR / "dist" / "index.html").exists():
        if not build_frontend():
            return
    else:
        if _force_rebuild_frontend():
            if not build_frontend():
                return
        else:
            print("\n[1/3] 前端已有构建产物，跳过 npm build（加快打包）")
            print("      若要强制重建前端：")
            print("        python scripts/build_exe.py --rebuild-frontend")
            if platform.system() == "Windows":
                print("      或 PowerShell：$env:BUILD_EXE='1'; python scripts/build_exe.py")
                print("      或 CMD：        set BUILD_EXE=1 && python scripts/build_exe.py")
            else:
                print("      或：BUILD_EXE=1 python scripts/build_exe.py")

    # PyInstaller 打包
    if not build_exe():
        return

    # 复制配置
    copy_assets()

    print("\n" + "=" * 50)
    print("  [OK] 打包完成！")
    print(f"  输出目录: {DIST_DIR}")
    print(f"  主程序:   {DIST_DIR / 'stock_analyzer.exe'}")
    print(f"")
    print(f"  使用步骤:")
    print(f"  1. 将 {DIST_DIR.name}/ 目录拷贝到目标机器")
    print(f"  2. 将 .env.example 重命名为 .env")
    print(f"  3. 编辑 .env，填入 API Key")
    print(f"  4. 双击 stock_analyzer.exe 启动")
    print(f"  5. 浏览器将打开 http://127.0.0.1:5174/dashboard（未配置 BACKEND_PORT 时）")
    print("=" * 50)


if __name__ == "__main__":
    main()
