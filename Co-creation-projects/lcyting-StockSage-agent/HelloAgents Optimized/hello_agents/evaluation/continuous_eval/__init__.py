"""持续评估系统

提供三层评估策略 + 定时调度 + 趋势检测 + 告警通知。

使用示例:
    from hello_agents.evaluation.continuous_eval import ContinuousEvalSystem

    system = ContinuousEvalSystem(agent=my_agent)
    system.start()  # 启动自动调度
    # ...
    system.stop()
"""

from .scheduler import EvalScheduler, EvalSchedule
from .evaluator import run_quick_eval, run_standard_eval, run_full_eval
from .db import EvalDB, TrendDetector, AlertNotifier, Alert, AlertRule


class ContinuousEvalSystem:
    """持续评估系统 - 集调度、评估、监控、告警于一体"""

    def __init__(
        self,
        agent,
        bfcl_data_dir: str = "./temp_gorilla/berkeley-function-call-leaderboard/bfcl_eval/data",
    ):
        self.agent = agent
        self.bfcl_data_dir = bfcl_data_dir
        self.db = EvalDB()
        self.detector = TrendDetector(self.db)
        self.notifier = AlertNotifier()
        self.scheduler = EvalScheduler()
        self._setup_schedules()

    def _setup_schedules(self):
        def quick():
            r = run_quick_eval(self.agent, self.db, self.bfcl_data_dir)
            alerts = self.detector.check(r)
            self.notifier.notify(alerts)

        def standard():
            r = run_standard_eval(self.agent, self.db, self.bfcl_data_dir)
            alerts = self.detector.check(r)
            self.notifier.notify(alerts)

        def full():
            r = run_full_eval(self.agent, self.db, self.bfcl_data_dir)
            alerts = self.detector.check(r)
            self.notifier.notify(alerts)

        self.scheduler.add_schedule(
            EvalSchedule(name="quick", interval_hours=24, eval_fn=quick, tags=["daily"])
        )
        self.scheduler.add_schedule(
            EvalSchedule(
                name="standard", interval_hours=168, eval_fn=standard, tags=["weekly"]
            )
        )
        self.scheduler.add_schedule(
            EvalSchedule(
                name="full", interval_hours=720, eval_fn=full, tags=["monthly"]
            )
        )

    def start(self):
        self.scheduler.start()
        print("[持续评估] ✅ 系统已启动")

    def stop(self):
        self.scheduler.stop()
        print("[持续评估] 系统已停止")

    def run_once(self, level: str = "quick"):
        levels = {
            "quick": run_quick_eval,
            "standard": run_standard_eval,
            "full": run_full_eval,
        }
        fn = levels[level]
        r = fn(self.agent, self.db, self.bfcl_data_dir)
        alerts = self.detector.check(r)
        self.notifier.notify(alerts)
        return r

    def get_report_data(self):
        return {
            "quick": self.db.get_recent_snapshots(level="quick", days=7),
            "standard": self.db.get_recent_snapshots(level="standard", days=30),
            "full": self.db.get_recent_snapshots(level="full", days=90),
            "alerts": self.db.get_recent_alerts(days=7),
        }


__all__ = [
    "ContinuousEvalSystem",
    "EvalScheduler",
    "EvalSchedule",
    "run_quick_eval",
    "run_standard_eval",
    "run_full_eval",
    "EvalDB",
    "TrendDetector",
    "AlertNotifier",
    "Alert",
    "AlertRule",
]
