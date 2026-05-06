#!/usr/bin/env python3
# mx_xuangu - 妙想智能选股 skill
# 基于东方财富妙想API提供智能选股能力

import os
import sys
import json
import csv
import re
import argparse
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

def safe_filename(s: str, max_len: int = 80) -> str:
    """将查询文本转为安全文件名片段"""
    s = re.sub(r'[<>:"/\\|?*]', "_", s)
    s = s.strip().replace(" ", "_")[:max_len]
    return s or "query"

def build_column_map(columns: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    从返回的 columns 构建 原始列名 -> 中文列名 的映射
    """
    name_map: Dict[str, str] = {}
    for col in columns or []:
        if not isinstance(col, dict):
            continue
        en_key = col.get("field", "") or col.get("name", "") or col.get("key", "")
        cn_name = col.get("displayName", "") or col.get("title", "") or col.get("label", "")
        date_msg = col.get('dateMsg', '')
        if date_msg:
            cn_name = cn_name + ' ' + date_msg
        if en_key is not None and cn_name is not None:
            name_map[str(en_key)] = str(cn_name)
    return name_map

def columns_order(columns: List[Dict[str, Any]]) -> List[str]:
    """按 columns 顺序返回原始列名列表，用于 CSV 表头顺序"""
    order: List[str] = []
    for col in columns or []:
        if not isinstance(col, dict):
            continue
        en_key = col.get("field") or col.get("name") or col.get("key")
        if en_key is not None:
            order.append(str(en_key))
    return order

def parse_partial_results_table(partial_results: str) -> List[Dict[str, str]]:
    """
    将 partialResults 的 Markdown 表格字符串解析为行字典列表
    """
    if not partial_results or not isinstance(partial_results, str):
        return []
    lines = [ln.strip() for ln in partial_results.strip().splitlines() if ln.strip()]
    if not lines:
        return []

    def split_cells(line: str) -> List[str]:
        return [c.strip() for c in line.split("|") if c.strip() != ""]

    header_cells = split_cells(lines[0])
    if not header_cells:
        return []
    # 跳过分隔行（如 |---|---|）
    data_start = 1
    if data_start < len(lines) and re.match(r"^[\s\|\-]+$", lines[data_start]):
        data_start = 2
    rows: List[Dict[str, str]] = []
    for i in range(data_start, len(lines)):
        cells = split_cells(lines[i])
        if len(cells) != len(header_cells):
            # 列数不一致时按长度对齐，缺的补空
            if len(cells) < len(header_cells):
                cells.extend([""] * (len(header_cells) - len(cells)))
            else:
                cells = cells[: len(header_cells)]
        rows.append(dict(zip(header_cells, cells)))
    return rows

def datalist_to_rows(
        datalist: List[Dict[str, Any]],
        column_map: Dict[str, str],
        column_order: List[str],
) -> List[Dict[str, str]]:
    """
    将 datalist 中每行的原始键按 column_map 替换为中文键，保证顺序
    """
    if not datalist:
        return []

    # 表头顺序：优先按 columns 顺序，未在 columns 中的键按首次出现顺序排在后面
    first = datalist[0]
    extra_keys = [k for k in first if k not in column_order]
    header_order = column_order + extra_keys

    rows: List[Dict[str, str]] = []
    for row in datalist:
        if not isinstance(row, dict):
            continue
        cn_row: Dict[str, str] = {}
        for en_key in header_order:
            if en_key not in row:
                continue
            cn_name = column_map.get(en_key, en_key)
            val = row[en_key]
            if val is None:
                cn_row[cn_name] = ""
            elif isinstance(val, (dict, list)):
                cn_row[cn_name] = json.dumps(val, ensure_ascii=False)
            else:
                cn_row[cn_name] = str(val)
        rows.append(cn_row)

    return rows

class MXSelectStock:
    """妙想智能选股客户端"""
    
    BASE_URL = "https://mkapi2.dfcfs.com/finskillshub/api/claw/stock-screen"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        初始化客户端
        :param api_key: MX API Key，如果不提供则从环境变量 MX_APIKEY 读取
        """
        self.api_key = api_key or os.getenv("MX_APIKEY")
        if not self.api_key:
            raise ValueError(
                "MX_APIKEY 环境变量未设置，请先设置环境变量：\n"
                "export MX_APIKEY=your_api_key_here\n"
                "或者在初始化时传入 api_key 参数"
            )
    
    def search(self, query: str) -> Dict[str, Any]:
        """
        智能选股
        :param query: 自然语言查询，如 "今天A股价格大于10元"
        :return: API 响应结果
        """
        headers = {
            "Content-Type": "application/json",
            "apikey": self.api_key
        }
        data = {
            "keyword": query
        }
        
        response = requests.post(self.BASE_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    
    @staticmethod
    def extract_data(result: Dict[str, Any]) -> Tuple[List[Dict[str, str]], str, Optional[str]]:
        """
        提取数据 :
        - 优先使用 allResults.result.dataList 全量数据
        - 若无则回退到解析 partialResults Markdown 表格
        :return: (rows, data_source, error)
        """
        status = result.get("status")
        if status != 0:
            return [], "", f"顶层错误: 状态码 {status} - {result.get('message', '')}"
        
        data = result.get("data", {})
        inner_data = data.get("data", {})
        
        # 优先使用全量数据 dataList
        data_list = inner_data.get("allResults", {}).get("result", {}).get("dataList", [])
        columns = inner_data.get("allResults", {}).get("result", {}).get("columns", [])
        
        if isinstance(data_list, list) and data_list:
            column_map = build_column_map(columns)
            order = columns_order(columns)
            rows = datalist_to_rows(data_list, column_map, order)
            return rows, "dataList", None
        
        # 回退到 partialResults 解析
        partial_results = inner_data.get("partialResults", "")
        if partial_results:
            rows = parse_partial_results_table(partial_results)
            return rows, "partialResults", None
        
        return [], "", "返回中无有效 dataList 且 partialResults 无法解析或为空"

def main():
    """命令行入口 """
    parser = argparse.ArgumentParser(description='通过自然语言查询进行智能选股（A股/港股/美股/板块/基金/ETF）')
    parser.add_argument('query', nargs='?', help='自然语言查询，如「股价大于10元的A股」')
    parser.add_argument('--query', dest='query_opt', help='自然语言查询（显式参数）')
    parser.add_argument('--output-dir', dest='output_dir', help='输出目录，默认 /root/.openclaw/workspace/mx_data/output/')
    args = parser.parse_args()
    
    # Resolve query
    query = args.query_opt or args.query
    if not query:
        parser.print_help()
        sys.exit(1)
    
    # Default output directory is fixed to /root/.openclaw/workspace/mx_data/output/
    default_output = Path("/root/.openclaw/workspace/mx_data/output")
    output_dir = Path(args.output_dir) if args.output_dir else default_output
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        mx = MXSelectStock()
        result = mx.search(query)
        rows, data_source, err = mx.extract_data(result)
        
        if err:
            print(f"错误: {err}")
            print(f"原始结果预览: {json.dumps(result, ensure_ascii=False)[:500]}")
            sys.exit(2)
        
        if not rows:
            print("未找到符合条件的数据")
            sys.exit(0)
        
        # 输出 CSV
        fieldnames = list(rows[0].keys())
        safe_name = safe_filename(query)
        csv_path = output_dir / f"mx_xuangu_{safe_name}.csv"
        desc_path = output_dir / f"mx_xuangu_{safe_name}_description.txt"
        
        with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
        
        # 写入描述文件
        description_lines = [
            "智能选股 结果说明",
            "=" * 40,
            f"查询内容: {query}",
            f"数据行数: {len(rows)}（来源: {data_source}）",
            f"列名（中文）: {', '.join(fieldnames)}",
            "",
            "说明: 数据来源于东方财富妙想智能选股；"
            + ("列名已按 columns 映射为中文。" if data_source == "dataList" else "表格来自 partialResults 解析。"),
        ]
        desc_path.write_text("\n".join(description_lines), encoding="utf-8")
        
        # 终端输出信息
        print(f"✅ CSV: {csv_path}")
        print(f"📄 描述: {desc_path}")
        print(f"📊 行数: {len(rows)}")
        
        # 保存原始 JSON
        json_path = output_dir / f"mx_xuangu_{safe_name}_raw.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"📄 原始JSON: {json_path}")
            
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
