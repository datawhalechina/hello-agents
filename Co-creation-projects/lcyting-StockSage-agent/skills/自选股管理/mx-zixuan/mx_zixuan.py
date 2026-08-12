#!/usr/bin/env python3
"""
妙想自选管理skill (mx_zixuan)
支持查询、添加、删除东方财富自选股
统一输出到 /root/.openclaw/workspace/mx_data/output/
"""

import os
import sys
import csv
import json
import requests
import argparse
from pathlib import Path
from typing import Dict, List, Any

# 接口配置
QUERY_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/self-select/get"
MANAGE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/self-select/manage"

def safe_filename(s: str, max_len: int = 80) -> str:
    """Convert query to safe filename - same as other mx_* skills"""
    s = s.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(":", "_")
    s = s.replace("*", "_").replace("?", "_").replace('"', "_").replace("<", "_").replace(">", "_")
    s = s.replace("|", "_")[:max_len]
    return s or "query"

def get_apikey() -> str:
    """从环境变量获取apikey"""
    apikey = os.environ.get("MX_APIKEY", "")
    if not apikey:
        # 尝试从.env文件读取
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            if key.strip() == "MX_APIKEY":
                                apikey = value.strip()
                                break
            except Exception as e:
                print(f"⚠️  读取.env文件失败: {e}", file=sys.stderr)
    
    if not apikey:
        print("❌ 未找到MX_APIKEY，请设置环境变量：", file=sys.stderr)
        print("   export MX_APIKEY=your_apikey", file=sys.stderr)
        raise RuntimeError("MX_APIKEY 未配置")
    
    return apikey

def query_self_select(apikey: str) -> Dict:
    """查询自选股列表"""
    headers = {
        "Content-Type": "application/json",
        "apikey": apikey
    }
    
    response = requests.post(QUERY_URL, headers=headers, json={}, timeout=30)
    response.raise_for_status()
    return response.json()

def manage_self_select(apikey: str, query: str) -> Dict:
    """添加或删除自选股"""
    headers = {
        "Content-Type": "application/json",
        "apikey": apikey
    }
    
    data = {
        "query": query
    }
    
    response = requests.post(MANAGE_URL, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    return response.json()

def format_query_result(result: Dict, output_dir: Path):
    """格式化查询结果输出 + 保存 CSV"""
    if result.get("status") != 0 and result.get("code") != 0:
        print(f"❌ 查询失败: {result.get('message', '未知错误')}", file=sys.stderr)
        return
    
    data = result.get("data", {})
    all_results = data.get("allResults", {})
    result_data = all_results.get("result", {})
    columns = result_data.get("columns", [])
    data_list = result_data.get("dataList", [])
    
    if not data_list:
        print("ℹ️  自选股列表为空，请到东方财富App查询")
        return
    
    # 提取需要显示的字段
    display_fields = [
        ("SECURITY_CODE", "股票代码", 8),
        ("SECURITY_SHORT_NAME", "股票名称", 8),
        ("NEWEST_PRICE", "最新价(元)", 10),
        ("CHG", "涨跌幅(%)", 10),
        ("PCHG", "涨跌额(元)", 10),
        ("010000_TURNOVER_RATE", "换手率(%)", 10),
        ("010000_LIANGBI", "量比", 6)
    ]
    
    # 打印表头
    print("📊 我的自选股列表")
    print("=" * 100)
    header = " | ".join([f"{name:<{width}}" for _, name, width in display_fields])
    print(header)
    print("-" * 100)
    
    # 打印数据行
    for stock in data_list:
        row = []
        for key, _, width in display_fields:
            value = stock.get(key, "-")
            # 处理涨跌幅颜色
            if key == "CHG" and value != "-":
                try:
                    chg = float(value)
                    if chg > 0:
                        value = f"+{value}%"
                    elif chg < 0:
                        value = f"{value}%"
                    else:
                        value = f"{value}%"
                except:
                    pass
            row.append(f"{str(value):<{width}}")
        print(" | ".join(row))
    
    print("-" * 100)
    print(f"共 {len(data_list)} 只自选股")
    
    # 保存到 CSV - same output convention as other mx_* skills
    safe_name = "我的自选股列表"
    csv_path = output_dir / f"mx_zixuan_{safe_filename(safe_name)}.csv"
    
    # Build CSV header from all columns (Chinese names)
    fieldnames = []
    csv_rows = []
    column_name_map = {}
    for col in columns:
        title = col.get("title", col.get("key", "unknown"))
        key = col.get("key", "unknown")
        column_name_map[key] = title
        fieldnames.append(title)
    
    for stock in data_list:
        csv_row = {}
        for key, title in column_name_map.items():
            csv_row[title] = stock.get(key, "")
        csv_rows.append(csv_row)
    
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in csv_rows:
            writer.writerow(row)
    
    # Save raw JSON
    json_path = output_dir / f"mx_zixuan_{safe_filename(safe_name)}_raw.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ CSV 已保存: {csv_path}")
    print(f"📄 原始JSON: {json_path}")

def format_manage_result(result: Dict, query: str):
    """格式化操作结果输出"""
    if result.get("status") != 0 and result.get("code") != 0:
        print(f"❌ 操作失败: {result.get('message', '未知错误')}", file=sys.stderr)
        return
    
    print(f"✅ 操作成功: {result.get('message', '已完成')}")

def main():
    parser = argparse.ArgumentParser(description="妙想自选管理工具 (mx_zixuan)")
    parser.add_argument("command", nargs="?", help="命令: query/add/delete 或自然语言指令")
    parser.add_argument("stock", nargs="?", help="股票名称或代码（可选）")
    parser.add_argument("--output-dir", dest="output_dir", help=f"输出目录，默认 {Path('/root/.openclaw/workspace/mx_data/output')}")
    
    args = parser.parse_args()
    
    # Default output directory
    default_output = Path("/root/.openclaw/workspace/mx_data/output")
    output_dir = Path(args.output_dir) if args.output_dir else default_output
    output_dir.mkdir(parents=True, exist_ok=True)
    
    apikey = get_apikey()
    
    # 处理命令
    if not args.command:
        print("ℹ️  使用方式:", file=sys.stderr)
        print("  查询自选股: python scripts/mx_zixuan.py query", file=sys.stderr)
        print("  添加自选股: python scripts/mx_zixuan.py add 贵州茅台", file=sys.stderr)
        print("  删除自选股: python scripts/mx_zixuan.py delete 贵州茅台", file=sys.stderr)
        print("  自然语言: python scripts/mx_zixuan.py \"把贵州茅台加入自选\"", file=sys.stderr)
        print(f"\n  默认输出目录: {output_dir}", file=sys.stderr)
        sys.exit(1)
    
    command = args.command.lower()
    
    if command in ["query", "list", "查询", "列表"]:
        # 查询自选股
        result = query_self_select(apikey)
        format_query_result(result, output_dir)
    elif command in ["add", "添加", "增加"] and args.stock:
        # 添加股票
        query = f"把{args.stock}添加到我的自选股列表"
        result = manage_self_select(apikey, query)
        format_manage_result(result, query)
    elif command in ["delete", "del", "remove", "删除", "移除"] and args.stock:
        # 删除股票
        query = f"把{args.stock}从我的自选股列表删除"
        result = manage_self_select(apikey, query)
        format_manage_result(result, query)
    else:
        # 自然语言处理
        query = args.command
        if args.stock:
            query += " " + args.stock
        
        # 判断是查询还是管理操作
        if any(keyword in query for keyword in ["查询", "列表", "我的自选", "有哪些"]):
            result = query_self_select(apikey)
            format_query_result(result, output_dir)
        else:
            result = manage_self_select(apikey, query)
            format_manage_result(result, query)

if __name__ == "__main__":
    main()
