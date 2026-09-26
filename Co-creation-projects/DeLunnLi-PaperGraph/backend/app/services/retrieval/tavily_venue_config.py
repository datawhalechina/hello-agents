"""Tavily ``include_domains`` 与会场锚点主机列表：数据驱动（JSON），避免在业务代码里写死映射。

编辑 ``tavily_venue_domains.json`` 即可增删会场；或通过环境变量 / 配置指向自定义 JSON。
"""

from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.search.normalize import _venue_canonical_key

logger = logging.getLogger(__name__)

_DEFAULT_JSON = Path(__file__).resolve().with_name("tavily_venue_domains.json")

_RE_SAFE_DOMAIN = re.compile(
    r"^[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$",
    re.I,
)


def _sanitize_domains(raw: Any, *, limit: int = 3) -> List[str]:
    out: List[str] = []
    if not isinstance(raw, list):
        return out
    for x in raw:
        s = str(x).strip().lower().rstrip(".")
        if not s or "." not in s:
            continue
        if not _RE_SAFE_DOMAIN.match(s):
            logger.warning("tavily venue config: skip invalid domain %r", s)
            continue
        if s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _resolve_config_path() -> Path:
    env_p = (os.environ.get("PAPERGRAPH_TAVILY_VENUE_DOMAINS_JSON") or "").strip()
    if env_p:
        ep = Path(env_p).expanduser()
        if ep.is_file():
            return ep
        logger.warning("tavily venue config: env path not a file: %s", ep)
    try:
        from ...settings import get_settings

        cfg = (getattr(get_settings(), "tavily_venue_domains_config_path", None) or "").strip()
        if cfg:
            cp = Path(cfg).expanduser()
            if cp.is_file():
                return cp
            logger.warning("tavily venue config: settings path not a file: %s", cp)
    except Exception:
        pass
    return _DEFAULT_JSON


@lru_cache(maxsize=4)
def _load_config_for_path(resolved_path: str) -> Dict[str, Any]:
    try:
        p = Path(resolved_path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        logger.error("tavily venue config missing: %s", resolved_path)
    except json.JSONDecodeError as e:
        logger.error("tavily venue config JSON invalid (%s): %s", resolved_path, e)
    except OSError as e:
        logger.error("tavily venue config read failed (%s): %s", resolved_path, e)
    return {}


def _get_config_data() -> Dict[str, Any]:
    return _load_config_for_path(str(_resolve_config_path().resolve()))


def clear_tavily_venue_config_cache() -> None:
    """测试或替换 JSON 后调用以失效缓存。"""
    _load_config_for_path.cache_clear()


def get_official_proceedings_hosts() -> tuple[str, ...]:
    """用于锚点标题 / 关键词排序加权的官方 proceedings 主机列表。"""
    raw = _get_config_data().get("official_proceedings_hosts") or []
    hosts = _sanitize_domains(raw, limit=32)
    if hosts:
        return tuple(hosts)
    return tuple(_DEFAULT_BUILTIN_HOSTS)


_DEFAULT_BUILTIN_HOSTS = (
    "proceedings.neurips.cc",
    "proceedings.mlr.press",
    "openaccess.thecvf.com",
    "aclanthology.org",
    "aaai.org",
    "ijcai.org",
)


def _canonical_include_map() -> Dict[str, List[str]]:
    data = _get_config_data().get("include_domains_by_canonical") or {}
    out: Dict[str, List[str]] = {}
    if not isinstance(data, dict):
        return out
    for k, v in data.items():
        key = str(k).strip().lower()
        if not key:
            continue
        doms = _sanitize_domains(v)
        if doms:
            out[key] = doms
    return out


def _condition_matches(vl: str, cond: Any) -> bool:
    if not isinstance(cond, dict):
        return False
    if "substring" in cond:
        sub = str(cond.get("substring") or "").lower()
        return bool(sub) and sub in vl
    if "regex" in cond:
        pat = str(cond.get("regex") or "")
        if not pat:
            return False
        try:
            return bool(re.search(pat, vl))
        except re.error as e:
            logger.warning("tavily venue config: bad regex %r: %s", pat, e)
            return False
    return False


def _first_domains_from_substring_rules(vl: str) -> Optional[List[str]]:
    rules = _get_config_data().get("substring_rules") or []
    if not isinstance(rules, list):
        return None
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        doms = _sanitize_domains(rule.get("domains"))
        if not doms:
            continue
        any_conds = rule.get("any")
        if not isinstance(any_conds, list):
            continue
        ok = False
        for c in any_conds:
            if _condition_matches(vl, c):
                ok = True
                break
        if ok:
            return doms
    return None


def tavily_include_domains_for_venue(venue: Optional[str]) -> Optional[List[str]]:
    """根据会场字符串返回 Tavily ``include_domains``（数据来自 JSON）。

    返回 ``None`` 表示不限制域名。ICLR / 泛 ACM DL 等仍建议仅在 JSON 中不配规则。
    """
    raw = (venue or "").strip()
    if not raw:
        return None
    key = _venue_canonical_key(raw)
    if key:
        m = _canonical_include_map().get(key)
        if m:
            return list(m)
    vl = raw.lower()
    return _first_domains_from_substring_rules(vl)
