"""快速验证：单独测试每个工具函数"""
from tools import get_realtime_quote, get_historical_data, get_financial_data, calc_indicators, get_news

if __name__ == "__main__":
    print("=" * 60)
    print("测试 1: 实时行情")
    print("=" * 60)
    print(get_realtime_quote("600519"))

    print("\n" + "=" * 60)
    print("测试 2: 历史K线")
    print("=" * 60)
    print(get_historical_data("600519|daily|10"))

    print("\n" + "=" * 60)
    print("测试 3: 技术指标")
    print("=" * 60)
    print(calc_indicators("600519|daily|60"))

    print("\n" + "=" * 60)
    print("测试 4: 财务数据")
    print("=" * 60)
    print(get_financial_data("600519"))

    print("\n" + "=" * 60)
    print("测试 5: 新闻")
    print("=" * 60)
    print(get_news("600519"))

    print("\n全部工具测试完成!")
