"""
考研复试资料自动下载脚本

功能：从 Excel 配置文件中读取 Git 仓库 URL 列表，自动克隆这些仓库到本地 datas 目录。

配置文件：data_sources.xlsx
  - 需要包含 '数据源' 列，每行是一个 Git 仓库 URL
  - 支持 GitHub、GitLab、Gitee 等各类 Git 仓库

使用示例：
  python download_repos.py

输出：
  - 所有克隆的仓库都保存在 datas/ 目录下
  - 已存在的仓库会自动跳过（不重复下载）
"""

import pandas as pd
import os
import subprocess
from urllib.parse import urlparse


def download_repos():
    """
    从 Excel 文件读取数据源 URL，自动克隆到本地
    
    流程：
      1. 读取 data_sources.xlsx 中的 '数据源' 列
      2. 对每个有效的 URL 进行验证
      3. 提取仓库名称作为本地文件夹名
      4. 检查本地是否已存在该仓库
      5. 如不存在则克隆，如存在则跳过
    """
    
    # ==================== 配置路径 ====================
    
    # 获取当前脚本所在目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Excel 配置文件路径（包含数据源 URL）
    excel_path = os.path.join(base_dir, 'data_sources.xlsx')
    
    # 数据输出目录
    datas_dir = os.path.join(base_dir, 'datas')

    # ==================== 创建输出目录 ====================
    
    # 确保 datas 目录存在
    if not os.path.exists(datas_dir):
        os.makedirs(datas_dir)
        print(f"Created directory: {datas_dir}")

    # ==================== 读取配置文件 ====================
    
    try:
        # 读取 Excel 文件中的所有行
        df = pd.read_excel(excel_path)
    except Exception as e:
        print(f"Error reading {excel_path}: {e}")
        return

    # ==================== 验证配置文件格式 ====================
    
    # 检查是否存在 '数据源' 列（必须有）
    if '数据源' not in df.columns:
        print("Column '数据源' not found in the Excel file.")
        return

    # ==================== 遍历并下载仓库 ====================
    
    # 循环处理每一个数据源
    for link in df['数据源']:
        # 跳过空值和非字符串值
        if not isinstance(link, str) or not link.strip():
            continue
        
        link = link.strip()
        
        # ==================== URL 验证 ====================
        
        # 检查是否为有效的 URL（以 http 开头）
        if not link.startswith('http'):
            print(f"Skipping invalid link: {link}")
            continue

        # ==================== 提取仓库名称 ====================
        
        # 从 URL 中提取仓库名
        # 例如：https://github.com/user/repo -> repo
        path = urlparse(link).path
        repo_name = os.path.basename(path)
        
        # 移除 .git 后缀（如果有）
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        # 如果无法解析仓库名，跳过此 URL
        if not repo_name:
            print(f"Could not determine repo name from {link}")
            continue

        # ==================== 检查是否已存在 ====================
        
        # 本地存储路径
        target_dir = os.path.join(datas_dir, repo_name)

        # 如果仓库已存在，跳过（避免重复克隆）
        if os.path.exists(target_dir):
            print(f"Directory {target_dir} already exists. Skipping {link}")
            continue

        # ==================== 克隆仓库 ====================
        
        print(f"Cloning {link} into {target_dir}...")
        try:
            # 执行 git clone 命令
            subprocess.run(['git', 'clone', link, target_dir], check=True)
            print(f"Successfully cloned {link}")
        except subprocess.CalledProcessError as e:
            # 处理 git 命令执行失败的情况
            print(f"Failed to clone {link}: {e}")
        except Exception as e:
            # 处理其他意外错误
            print(f"An unexpected error occurred while cloning {link}: {e}")


# ==================== 主程序入口 ====================

if __name__ == "__main__":
    # 执行数据下载
    download_repos()
