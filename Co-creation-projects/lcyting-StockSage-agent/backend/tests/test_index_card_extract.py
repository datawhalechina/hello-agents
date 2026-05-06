"""指数仪表盘 display_* 字段解析单元测试"""

import pytest

from app.services.market_service import _extract_index_card_from_tables, _extract_index_card_one_table


def test_wide_table_last_row_by_date():
    tables = [
        {
            "fieldnames": ["日期", "收盘点位", "涨跌幅"],
            "rows": [
                {"日期": "2024-01-01", "收盘点位": "3000", "涨跌幅": "1.2%"},
                {"日期": "2024-01-02", "收盘点位": "3050.12", "涨跌幅": "-0.35%"},
            ],
        }
    ]
    price, chg = _extract_index_card_from_tables(tables)
    assert price == "3050.12"
    assert chg == pytest.approx(-0.35)


def test_long_two_column_mx_shape():
    tables = [
        {
            "fieldnames": ["上证指数", "2025-05-05"],
            "rows": [
                {"上证指数": "最新点位", "2025-05-05": "3860.11"},
                {"上证指数": "涨跌幅", "2025-05-05": "+0.42%"},
            ],
        }
    ]
    price, chg = _extract_index_card_from_tables(tables)
    assert price == "3860.11"
    assert chg == pytest.approx(0.42)


def test_heuristic_when_headers_obscure():
    tables = [
        {
            "fieldnames": ["A", "B", "C"],
            "rows": [{"A": "上证", "B": "3842.31", "C": "-0.12%"}],
        }
    ]
    price, chg = _extract_index_card_from_tables(tables)
    assert price == "3842.31"
    assert chg == pytest.approx(-0.12)


def test_skip_empty_first_sheet_use_second():
    """妙想多表时首表无有效行，真正的行情在后续 sheet"""
    tables = [
        {"fieldnames": ["说明"], "rows": []},
        {
            "fieldnames": ["日期", "收盘点位", "涨跌幅"],
            "rows": [
                {"日期": "2024-01-01", "收盘点位": "3000", "涨跌幅": "1.2%"},
                {"日期": "2024-01-02", "收盘点位": "3999.88", "涨跌幅": "-0.88%"},
            ],
        },
    ]
    price, chg = _extract_index_card_from_tables(tables)
    assert price == "3999.88"
    assert chg == pytest.approx(-0.88)


def test_merge_price_and_change_across_two_tables():
    price_only = _extract_index_card_one_table(
        {"fieldnames": ["最新点位", "备注"], "rows": [{"最新点位": "2150.01", "备注": "-"}]}
    )
    change_only = _extract_index_card_one_table(
        {"fieldnames": ["指标", "数值"], "rows": [{"指标": "涨跌幅", "数值": "+1.02%"}]}
    )
    assert price_only[0] == "2150.01"
    assert price_only[1] is None
    assert change_only[1] == pytest.approx(1.02)
    merged = _extract_index_card_from_tables(
        [
            {"fieldnames": ["最新点位", "备注"], "rows": [{"最新点位": "2150.01", "备注": "-"}]},
            {"fieldnames": ["指标", "数值"], "rows": [{"指标": "涨跌幅", "数值": "+1.02%"}]},
        ]
    )
    assert merged[0] == "2150.01"
    assert merged[1] == pytest.approx(1.02)
