"""评估基线数据库 - SQLite存储、趋势检测、告警"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class AlertRule:
    name: str
    metric_key: str
    operator: str
    threshold: float
    window_days: int
    severity: str


@dataclass
class Alert:
    rule_name: str
    metric_key: str
    current_value: float
    baseline_value: float
    severity: str
    message: str
    timestamp: str


class EvalDB:
    """评估结果数据库"""

    def __init__(self, db_path: str = "data/eval_data/continuous_eval.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS eval_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    timestamp TEXT,
                    agent_version TEXT,
                    metrics TEXT,
                    details TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_name TEXT,
                    metric_key TEXT,
                    current_value REAL,
                    baseline_value REAL,
                    severity TEXT,
                    message TEXT,
                    timestamp TEXT
                )
            """)
            conn.commit()

    def save_snapshot(self, results: Dict) -> int:
        metrics_json = json.dumps(results.get("metrics", {}), ensure_ascii=False)
        details_json = json.dumps(
            {
                k: v
                for k, v in results.items()
                if k not in ("metrics", "level", "timestamp")
            },
            ensure_ascii=False,
        )
        with sqlite3.connect(str(self.db_path)) as conn:
            cur = conn.execute(
                "INSERT INTO eval_snapshots (level, timestamp, metrics, details) VALUES (?, ?, ?, ?)",
                (results["level"], results["timestamp"], metrics_json, details_json),
            )
            conn.commit()
            return cur.lastrowid

    def get_recent_snapshots(self, level: str = None, days: int = 30) -> List[Dict]:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            if level:
                rows = conn.execute(
                    "SELECT * FROM eval_snapshots WHERE level=? AND timestamp>=? ORDER BY timestamp",
                    (level, since),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM eval_snapshots WHERE timestamp>=? ORDER BY timestamp",
                    (since,),
                ).fetchall()
        result = []
        for row in rows:
            result.append(
                {
                    "id": row[0],
                    "level": row[1],
                    "timestamp": row[2],
                    "agent_version": row[3],
                    "metrics": json.loads(row[4]),
                    "details": json.loads(row[5]) if row[5] else {},
                }
            )
        return result

    def get_baseline(
        self, metric_key: str, level: str = None, days: int = 7
    ) -> Optional[float]:
        snapshots = self.get_recent_snapshots(level=level, days=days)
        values = [
            s["metrics"].get(metric_key)
            for s in snapshots
            if s["metrics"].get(metric_key) is not None
        ]
        if not values:
            return None
        return sum(values) / len(values)

    def save_alert(self, alert: Alert):
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(
                "INSERT INTO alerts (rule_name, metric_key, current_value, baseline_value, severity, message, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    alert.rule_name,
                    alert.metric_key,
                    alert.current_value,
                    alert.baseline_value,
                    alert.severity,
                    alert.message,
                    alert.timestamp,
                ),
            )
            conn.commit()

    def get_recent_alerts(self, days: int = 7, severity: str = None) -> List[Dict]:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        with sqlite3.connect(str(self.db_path)) as conn:
            if severity:
                rows = conn.execute(
                    "SELECT * FROM alerts WHERE severity=? AND timestamp>=? ORDER BY timestamp DESC",
                    (severity, since),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM alerts WHERE timestamp>=? ORDER BY timestamp DESC",
                    (since,),
                ).fetchall()
        return [
            {
                "id": r[0],
                "rule_name": r[1],
                "metric_key": r[2],
                "current_value": r[3],
                "baseline_value": r[4],
                "severity": r[5],
                "message": r[6],
                "timestamp": r[7],
            }
            for r in rows
        ]

    def get_trend(
        self, metric_key: str, level: str = None, days: int = 30
    ) -> List[Tuple[str, float]]:
        snapshots = self.get_recent_snapshots(level=level, days=days)
        return [
            (s["timestamp"], s["metrics"].get(metric_key, 0))
            for s in snapshots
            if metric_key in s["metrics"]
        ]


class TrendDetector:
    """趋势检测器 - 检测性能退化"""

    def __init__(self, db: EvalDB):
        self.db = db
        self.rules = [
            AlertRule(
                "准确率骤降", "bfcl_simple_accuracy", "drop>", 0.10, 7, "critical"
            ),
            AlertRule(
                "准确率退化", "bfcl_simple_accuracy", "trend_down", 3, 14, "warning"
            ),
            # BFCL各分类
            AlertRule(
                "分类准确率骤降", "bfcl_multiple_accuracy", "drop>", 0.10, 7, "critical"
            ),
            AlertRule(
                "分类准确率退化",
                "bfcl_multiple_accuracy",
                "trend_down",
                3,
                14,
                "warning",
            ),
        ]

    def check(self, latest_snapshot: Dict) -> List[Alert]:
        alerts = []
        for rule in self.rules:
            current = latest_snapshot.get("metrics", {}).get(rule.metric_key)
            if current is None:
                continue
            if rule.operator == "drop>":
                baseline = self.db.get_baseline(rule.metric_key, days=rule.window_days)
                if baseline and baseline - current > rule.threshold:
                    alerts.append(
                        Alert(
                            rule_name=rule.name,
                            metric_key=rule.metric_key,
                            current_value=current,
                            baseline_value=baseline,
                            severity=rule.severity,
                            message=f"[{rule.severity.upper()}] {rule.name}: {current:.1%} vs 基线 {baseline:.1%} (下降 {baseline - current:.1%})",
                            timestamp=datetime.now().isoformat(),
                        )
                    )
            elif rule.operator == "trend_down":
                trend = self.db.get_trend(rule.metric_key, days=rule.window_days)
                if len(trend) >= rule.threshold:
                    recent = trend[-int(rule.threshold) :]
                    drops = sum(
                        1
                        for i in range(len(recent) - 1)
                        if recent[i + 1][1] < recent[i][1]
                    )
                    if drops == len(recent) - 1:
                        alerts.append(
                            Alert(
                                rule_name=rule.name,
                                metric_key=rule.metric_key,
                                current_value=current,
                                baseline_value=recent[0][1],
                                severity=rule.severity,
                                message=f"[{rule.severity.upper()}] {rule.name}: 连续{int(rule.threshold)}次下降 ({recent[0][1]:.1%} -> {current:.1%})",
                                timestamp=datetime.now().isoformat(),
                            )
                        )
        for alert in alerts:
            self.db.save_alert(alert)
        return alerts


class AlertNotifier:
    """告警通知器"""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url

    def notify(self, alerts: List[Alert]):
        if not alerts:
            return
        critical = [a for a in alerts if a.severity == "critical"]
        warnings = [a for a in alerts if a.severity == "warning"]

        if critical:
            print("\n" + "=" * 50)
            try:
                print("\U0001f534 CRITICAL \u544a\u8b66")
            except UnicodeEncodeError:
                print("[CRITICAL]")
            print("=" * 50)
            for a in critical:
                print(f"  {a.message}")
            print("=" * 50)

        if warnings:
            print("\n" + "=" * 50)
            try:
                print("\U0001f7e1 WARNING \u544a\u8b66")
            except UnicodeEncodeError:
                print("[WARNING]")
            print("=" * 50)
            for a in critical:
                print(f"  {a.message}")
            print("=" * 50)

        if warnings:
            print("\n" + "=" * 50)
            print("🟡 WARNING 告警")
            print("=" * 50)
            for a in warnings:
                print(f"  {a.message}")
            print("=" * 50)

        if self.webhook_url:
            import urllib.request

            payload = json.dumps(
                {
                    "critical": [a.message for a in critical],
                    "warning": [a.message for a in warnings],
                }
            )
            try:
                urllib.request.urlopen(
                    self.webhook_url, data=payload.encode(), timeout=5
                )
            except Exception as e:
                print(f"  Webhook 通知失败: {e}")
