"""Step 6: 股票分析记忆系统
持久化存储: 关注列表、分析历史、用户偏好
"""
import json
import os
from datetime import datetime
from typing import Optional


class StockMemory:
    """股票分析记忆 — JSON 文件持久化"""

    def __init__(self, path: str = "memory/stock_memory.json"):
        import threading
        self.path = path
        self.data = self._load()
        self._lock = threading.Lock()

    def _load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {"watchlist": {}, "history": [], "preferences": {}}

    def _save(self):
        import tempfile

        with self._lock:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(self.path))
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                os.replace(temp_path, self.path)
            except Exception:
                os.remove(temp_path)
                raise

    # ===== 关注列表 =====
    def add_watchlist(self, code: str, name: str = "", notes: str = "") -> str:
        self.data["watchlist"][code] = {
            "name": name or code,
            "notes": notes,
            "added": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        self._save()
        return f"已添加 {name or code}({code}) 到关注列表"

    def remove_watchlist(self, code: str) -> str:
        if code in self.data["watchlist"]:
            name = self.data["watchlist"][code]["name"]
            del self.data["watchlist"][code]
            self._save()
            return f"已从关注列表移除 {name}({code})"
        return f"关注列表中未找到 {code}"

    def get_watchlist(self, query: str = "") -> str:
        wl = self.data["watchlist"]
        if not wl:
            return "关注列表为空。说'关注 600519'来添加。"
        lines = [f"关注列表 ({len(wl)} 只):"]
        for code, info in wl.items():
            lines.append(f"  {info['name']}({code})  [{info['added']}]")
            if info.get("notes"):
                lines.append(f"    备注: {info['notes']}")
        return "\n".join(lines)

    # ===== 分析历史 =====
    def save_analysis(self, code: str, question: str, summary: str) -> str:
        record = {
            "code": code,
            "question": question,
            "summary": summary[:500],  # 截取前500字作为摘要
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.data["history"].append(record)
        # 只保留最近100条
        if len(self.data["history"]) > 100:
            self.data["history"] = self.data["history"][-100:]
        self._save()
        return f"分析记录已保存 ({len(self.data['history'])} 条历史)"

    def get_history(self, query: str = "") -> str:
        code = query.strip() if query else ""
        records = self.data["history"]
        if code:
            records = [r for r in records if r["code"] == code]
        if not records:
            return f"暂无{' ' + code + ' 的' if code else ''}分析历史"
        lines = [f"分析历史 (最近{len(records)}条):"]
        for r in records[-10:]:  # 最近10条
            lines.append(f"  [{r['timestamp']}] {r['code']}: {r['question'][:60]}")
        return "\n".join(lines)

    def get_last_analysis(self, code: str = "") -> Optional[str]:
        records = self.data["history"]
        if code:
            records = [r for r in records if r["code"] == code]
        if records:
            return records[-1].get("summary", "")
        return None

    # ===== 用户偏好 =====
    def set_preference(self, key: str, value: str) -> str:
        self.data["preferences"][key] = value
        self._save()
        return f"偏好已设置: {key} = {value}"

    def get_preferences(self, query: str = "") -> str:
        prefs = self.data["preferences"]
        if not prefs:
            return "暂无保存的偏好。可以设置如: '偏好 分析风格=深度价值投资'"
        lines = ["用户偏好:"]
        for k, v in prefs.items():
            lines.append(f"  {k}: {v}")
        return "\n".join(lines)

    def clear(self) -> str:
        self.data = {"watchlist": {}, "history": [], "preferences": {}}
        self._save()
        return "记忆已清空"


# 全局单例
_memory_instance = None


def get_memory() -> StockMemory:
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = StockMemory()
    return _memory_instance


# ===== 工具函数（可直接注册到 ToolRegistry）=====

def memory_add_watchlist(query: str) -> str:
    """添加股票到关注列表。输入: '代码|名称' 如 '600519|贵州茅台'"""
    parts = query.strip().split("|")
    code = parts[0].strip()
    name = parts[1].strip() if len(parts) > 1 else ""
    return get_memory().add_watchlist(code, name)


def memory_remove_watchlist(code: str) -> str:
    """从关注列表移除股票。输入: 股票代码"""
    return get_memory().remove_watchlist(code.strip())


def memory_get_watchlist(query: str = "") -> str:
    """查看关注列表"""
    return get_memory().get_watchlist(query)


def memory_save_analysis(query: str) -> str:
    """保存分析结果。输入: '代码|问题|摘要' """
    parts = query.strip().split("|")
    code = parts[0].strip() if len(parts) > 0 else ""
    question = parts[1].strip() if len(parts) > 1 else ""
    summary = parts[2].strip() if len(parts) > 2 else ""
    return get_memory().save_analysis(code, question, summary)


def memory_get_history(query: str = "") -> str:
    """查看分析历史。输入: 股票代码(可选，留空看全部)"""
    return get_memory().get_history(query)


def memory_set_preference(query: str) -> str:
    """设置用户偏好。输入: 'key=value' 如 '风格=技术分析为主'"""
    if "=" in query:
        k, v = query.split("=", 1)
        return get_memory().set_preference(k.strip(), v.strip())
    return "格式: key=value"


def memory_get_preferences(query: str = "") -> str:
    """查看用户偏好"""
    return get_memory().get_preferences()
