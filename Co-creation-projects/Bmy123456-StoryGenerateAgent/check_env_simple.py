#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
环境检查脚本 - 不使用Unicode字符
"""

import os
import sys

def check_env_file():
    """检查.env文件"""
    env_file = ".env"
    if os.path.exists(env_file):
        print("[OK] .env 文件存在")

        # 读取并显示配置
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        print("\n当前配置:")
        for line in lines:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                if 'KEY' in key or 'SECRET' in key:
                    value = value[:10] + "..."  # 隐藏敏感信息
                print("  {}={}".format(key, value))

        return True
    else:
        print("[ERROR] .env 文件不存在")
        print("\n请创建 .env 文件，包含以下内容：")
        print("""
OPENAI_API_KEY=your_api_key_here
BASE_URL=https://open.bigmodel.cn/api/paas/v4
MODEL_NAME=glm-4.5-air
TEMPERATURE=0.7
MAX_TOKENS=1000
DEBUG=True
""")
        return False

def check_directories():
    """检查必要的目录"""
    directories = ["config", "src", "src/generator", "src/models", "src/utils", "src/api", "logs", "data"]

    print("\n检查目录结构:")
    for dir_name in directories:
        if os.path.exists(dir_name):
            print("[OK] {}/".format(dir_name))
        else:
            print("[ERROR] {}/".format(dir_name))

def check_python_modules():
    """检查Python模块"""
    print("\nPython版本: {}".format(sys.version))

    # 检查基本模块
    basic_modules = ["os", "sys", "json"]

    # 检查可选模块
    optional_modules = ["dotenv", "requests", "openai", "pydantic", "fastapi", "uvicorn"]

    print("\n检查基本模块:")
    for module in basic_modules:
        try:
            __import__(module)
            print("[OK] {}".format(module))
        except ImportError:
            print("[ERROR] {}".format(module))

    print("\n检查可选模块:")
    for module in optional_modules:
        try:
            __import__(module)
            print("[OK] {}".format(module))
        except ImportError:
            print("[WARN] {} (可选)".format(module))

def main():
    """主函数"""
    print("=== 环境检查 ===\n")

    # 检查.env文件
    env_ok = check_env_file()

    # 检查目录
    check_directories()

    # 检查Python模块
    check_python_modules()

    if env_ok:
        print("\n[OK] 环境配置基本正常")
        print("下一步: 安装依赖")
        print("pip install python-dotenv requests openai pydantic fastapi uvicorn")
    else:
        print("\n[ERROR] 请先配置 .env 文件")

if __name__ == "__main__":
    main()