"""妙想 fixture 路径与回放开关"""

from app.config import settings
from app.utils.mx_fixture import fixture_path, try_load_raw_fixture


def test_fixture_path_stable_per_query(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MX_FIXTURE_DIR", tmp_path)
    p1 = fixture_path("mx_data", "600519 最新价")
    p2 = fixture_path("mx_data", "600519 最新价")
    assert p1 == p2
    assert p1.name.startswith("mx_data_")
    assert p1.suffix == ".json"


def test_try_load_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "MX_REPLAY_FIXTURES", True)
    monkeypatch.setattr(settings, "MX_FIXTURE_DIR", tmp_path)
    assert try_load_raw_fixture("mx_data", "不存在的查询") is None
