from io import StringIO

from src.tools.csv_import import CSVImportTool


def test_normalizes_chinese_columns_and_signed_amounts() -> None:
    source = StringIO("日期,商户,金额,备注\n2026/07/01 22:30,测试外卖,-35,夜宵\n2026/07/05,工资,7000,工资到账\n")
    transactions = CSVImportTool().load(source)
    assert len(transactions) == 2
    assert transactions[0].kind == "expense"
    assert transactions[0].amount == 35
    assert transactions[0].occurred_at == "2026-07-01T22:30"
    assert transactions[1].kind == "income"


def test_rejects_missing_required_columns() -> None:
    source = StringIO("金额,备注\n20,hello\n")
    try:
        CSVImportTool().load(source)
    except ValueError as exc:
        assert "日期和商户" in str(exc)
    else:
        raise AssertionError("expected CSV validation error")


def test_accepts_binary_gb18030_and_exposes_partial_row_warnings() -> None:
    raw = "日期,商户,金额,收支\n2026-07-01,工资,7000,收入\n坏日期,外卖,35,支出\n".encode("gb18030")
    tool = CSVImportTool()
    transactions = tool.load(__import__("io").BytesIO(raw))
    assert len(transactions) == 1
    assert transactions[0].kind == "income"
    assert tool.last_errors and "第 3 行" in tool.last_errors[0]
