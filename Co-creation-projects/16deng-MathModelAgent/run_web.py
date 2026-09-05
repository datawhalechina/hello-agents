"""
启动Web界面

启动Streamlit Web界面
"""

import subprocess
import sys
from pathlib import Path


def main():
    """启动Web界面"""
    
    # 获取当前目录
    current_dir = Path(__file__).parent
    
    # 启动Streamlit
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(current_dir / "app.py"),
        "--server.port", "8501",
        "--server.headless", "true"
    ]
    
    print("启动Web界面...")
    print(f"访问地址: http://localhost:8501")
    print("按 Ctrl+C 停止服务")
    print()
    
    try:
        subprocess.run(cmd, cwd=str(current_dir))
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == "__main__":
    main()
