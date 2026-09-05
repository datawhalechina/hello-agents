#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安装脚本
"""

import subprocess
import sys
import os

def run_command(cmd):
    """运行命令"""
    print(f"运行命令: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ 成功")
        return True
    else:
        print(f"❌ 失败: {result.stderr}")
        return False

def install_requirements():
    """安装依赖"""
    print("正在安装依赖...")

    # 升级pip
    run_command(f"{sys.executable} -m pip install --upgrade pip")

    # 安装基础依赖
    run_command(f"{sys.executable} -m pip install python-dotenv requests")

    # 安装AI相关依赖
    run_command(f"{sys.executable} -m pip install openai pydantic")

    # 安装Web框架
    run_command(f"{sys.executable} -m pip install fastapi uvicorn")

    # 安装其他依赖
    run_command(f"{sys.executable} -m pip install tqdm numpy pandas jinja2")

    # 安装开发依赖（可选）
    print("安装开发依赖...")
    run_command(f"{sys.executable} -m pip install pytest black flake8 mypy")

def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")

    if version.major >= 3 and version.minor >= 7:
        print("✅ Python版本符合要求")
        return True
    else:
        print("❌ 需要Python 3.7或更高版本")
        return False

def main():
    """主函数"""
    print("=== 故事生成器智能体安装脚本 ===\n")

    # 检查Python版本
    if not check_python_version():
        return 1

    # 创建必要的目录
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data/prompts", exist_ok=True)
    os.makedirs("data/examples", exist_ok=True)
    print("✅ 目录已创建")

    # 安装依赖
    install_requirements()

    print("\n✅ 安装完成！")
    print("\n下一步：")
    print("1. 编辑 .env 文件，设置API密钥")
    print("2. 运行 python simple_test.py 测试配置")
    print("3. 运行 python main.ipynb 开始使用")

    return 0

if __name__ == "__main__":
    sys.exit(main())