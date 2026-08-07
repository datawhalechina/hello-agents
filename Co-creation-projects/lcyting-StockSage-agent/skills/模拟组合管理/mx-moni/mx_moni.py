#!/usr/bin/env python3
# mx_moni - 妙想模拟组合管理技能

import os
import sys
import json
import re
import requests
from typing import Dict, Any, Optional, Tuple

# 加载环境变量
MX_APIKEY = os.environ.get('MX_APIKEY')
MX_API_URL = os.environ.get('MX_API_URL', 'https://mkapi2.dfcfs.com/finskillshub')
OUTPUT_DIR = '/root/.openclaw/workspace/mx_data/output'

os.makedirs(OUTPUT_DIR, exist_ok=True)

def check_apikey() -> None:
    """检查API密钥是否配置"""
    if not MX_APIKEY:
        print("错误: 未配置MX_APIKEY环境变量，请先配置API密钥")
        print("示例: export MX_APIKEY=your_api_key_here")
        sys.exit(1)

def make_request(endpoint: str, body: Dict[str, Any], output_prefix: str) -> None:
    """发送POST请求并保存结果"""
    check_apikey()
    full_url = f"{MX_API_URL}{endpoint}"
    headers = {
        'apikey': MX_APIKEY,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(full_url, headers=headers, json=body)
        response.raise_for_status()
        result = response.json()
        
        output_path = os.path.join(OUTPUT_DIR, f"{output_prefix}_raw.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"请求完成，结果保存在 {output_path}")
        
        # 打印结果摘要
        if result.get('success') or str(result.get('code')) == '200':
            print("\n操作结果: 成功")
            if 'message' in result:
                print(f"提示信息: {result['message']}")
            if 'data' in result and isinstance(result['data'], dict):
                data = result['data']
                if 'totalAssets' in data:
                    print(f"\n账户资金:")
                    print(f"  总资产: {data['totalAssets']:.2f} 元")
                    print(f"  可用资金: {data['availBalance']:.2f} 元")
                if 'orderId' in data:
                    print(f"\n委托成功:")
                    print(f"  委托编号: {data['orderId']}")
        else:
            print(f"\n操作结果: 失败")
            print(f"错误码: {result.get('code')}")
            print(f"错误信息: {result.get('message')}")
    except Exception as e:
        print(f"网络请求失败: {str(e)}")
        sys.exit(1)

def parse_buy_sell(query: str) -> Tuple[Optional[str], Optional[float], Optional[int], bool]:
    """解析买入卖出命令，返回(股票代码, 价格, 数量, 是否市价)"""
    # 提取6位股票代码
    code_match = re.search(r'(\d{6})', query)
    if not code_match:
        return None, None, None, False
    stock_code = code_match.group(1)
    
    # 提取数量（单位：股，必须是100倍数）
    quantity_match = re.search(r'(\d+)\s*(股|手)', query)
    quantity = None
    if quantity_match:
        qty = int(quantity_match.group(1))
        if quantity_match.group(2) == '手':
            qty = qty * 100
        quantity = qty
    
    # 检查是否市价委托
    is_market = any(word in query for word in ['市价', '市价买入', '市价卖出', '现价买入', '现价卖出'])
    
    # 提取价格
    price_match = re.search(r'(\d+\.?\d*)\s*元', query) if not is_market else None
    price = None
    if price_match and not is_market:
        price = float(price_match.group(1))
    elif not is_market and quantity:
        # 尝试找任意数字作为价格
        price_candidates = re.findall(r'\d+\.?\d*', query)
        for candidate in price_candidates:
            if len(candidate) != 6:  # 排除股票代码
                price = float(candidate)
                break
    
    return stock_code, price, quantity, is_market

def parse_cancel(query: str) -> Tuple[Optional[str], Optional[str], bool]:
    """解析撤单命令，返回(委托编号, 股票代码, 是否全部撤单)"""
    if any(word in query for word in ['全部', '所有', '一键撤单']):
        return None, None, True
    
    # 提取委托编号
    order_id_match = re.search(r'(\d{16,20})', query)
    order_id = order_id_match.group(1) if order_id_match else None
    
    # 提取股票代码
    code_match = re.search(r'(\d{6})', query)
    stock_code = code_match.group(1) if code_match else None
    
    return order_id, stock_code, False

def main():
    if len(sys.argv) < 2:
        print("请提供操作指令，例如：")
        print("  python mx_moni.py 我的持仓      # 查询持仓")
        print("  python mx_moni.py 我的资金      # 查询资金")
        print("  python mx_moni.py 我的委托      # 查询委托订单")
        print("  python mx_moni.py 买入 600519 价格 1700 数量 100 股")
        print("  python mx_moni.py 市价买入 600519 100 股")
        print("  python mx_moni.py 卖出 600519 价格 1750 数量 100 股")
        print("  python mx_moni.py 撤单 123456789012345678")
        print("  python mx_moni.py 一键撤单")
        sys.exit(1)
    
    query = ' '.join(sys.argv[1:])
    output_prefix = f"mx_moni_{query.replace(' ', '_')}"
    
    # 根据意图识别调用不同接口
    if any(word in query for word in ['持仓', '我的持仓', '持仓情况']):
        make_request('/api/claw/mockTrading/positions', {'moneyUnit': 1}, output_prefix)
    elif any(word in query for word in ['资金', '我的资金', '账户余额', '资金情况']):
        make_request('/api/claw/mockTrading/balance', {'moneyUnit': 1}, output_prefix)
    elif any(word in query for word in ['委托', '我的委托', '订单', '委托记录']):
        make_request('/api/claw/mockTrading/orders', {'fltOrderDrt': 0, 'fltOrderStatus': 0}, output_prefix)
    elif any(word in query for word in ['买入', '买进', '建仓']):
        stock_code, price, quantity, is_market = parse_buy_sell(query)
        if not stock_code or not quantity:
            print("错误: 无法解析买入指令，请确保包含股票代码(6位)和数量(100的整数倍)")
            print("示例: python mx_moni.py 买入 600519 价格 1700 数量 100 股")
            print("示例: python mx_moni.py 市价买入 600519 100 股")
            sys.exit(1)
        if not is_market and price is None:
            print("错误: 限价买入需要提供价格，或使用市价买入")
            sys.exit(1)
        if quantity % 100 != 0:
            print("错误: 委托数量必须为100的整数倍")
            sys.exit(1)
        
        body = {
            'type': 'buy',
            'stockCode': stock_code,
            'quantity': quantity,
            'useMarketPrice': is_market
        }
        if not is_market:
            body['price'] = price
        
        make_request('/api/claw/mockTrading/trade', body, output_prefix)
    elif any(word in query for word in ['卖出', '抛售', '减仓']):
        stock_code, price, quantity, is_market = parse_buy_sell(query)
        if not stock_code or not quantity:
            print("错误: 无法解析卖出指令，请确保包含股票代码(6位)和数量(100的整数倍)")
            print("示例: python mx_moni.py 卖出 600519 价格 1750 数量 100 股")
            print("示例: python mx_moni.py 市价卖出 600519 100 股")
            sys.exit(1)
        if not is_market and price is None:
            print("错误: 限价卖出需要提供价格，或使用市价卖出")
            sys.exit(1)
        if quantity % 100 != 0:
            print("错误: 委托数量必须为100的整数倍")
            sys.exit(1)
        
        body = {
            'type': 'sell',
            'stockCode': stock_code,
            'quantity': quantity,
            'useMarketPrice': is_market
        }
        if not is_market:
            body['price'] = price
        
        make_request('/api/claw/mockTrading/trade', body, output_prefix)
    elif any(word in query for word in ['撤单', '撤销', '撤单']):
        order_id, stock_code, is_all = parse_cancel(query)
        if is_all:
            body = {'type': 'all'}
            make_request('/api/claw/mockTrading/cancel', body, output_prefix)
        else:
            if not order_id:
                print("错误: 请提供委托编号，或使用一键撤单撤销所有未成交委托")
                print("示例: python mx_moni.py 撤单 260854300000078983")
                print("示例: python mx_moni.py 一键撤单")
                sys.exit(1)
            body = {
                'type': 'order',
                'orderId': order_id
            }
            if stock_code:
                body['stockCode'] = stock_code
            make_request('/api/claw/mockTrading/cancel', body, output_prefix)
    else:
        print("无法识别意图，请使用以下操作之一：")
        print("  持仓查询: 我的持仓 / 查询持仓")
        print("  资金查询: 我的资金 / 查询资金")
        print("  委托查询: 我的委托 / 查询委托")
        print("  买入操作: 买入 [股票代码] [价格] [数量] 股 / 市价买入 [股票代码] [数量] 股")
        print("  卖出操作: 卖出 [股票代码] [价格] [数量] 股 / 市价卖出 [股票代码] [数量] 股")
        print("  撤单操作: 撤单 [委托编号] / 一键撤单")
        sys.exit(1)

if __name__ == '__main__':
    main()
