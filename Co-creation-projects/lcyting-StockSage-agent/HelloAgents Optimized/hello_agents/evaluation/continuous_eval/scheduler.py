"""调度器 - 定期触发不同层级的评估"""

import time
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Callable, List
from dataclasses import dataclass, field


@dataclass
class EvalSchedule:
    """评估调度配置"""

    name: str
    interval_hours: int
    eval_fn: Callable
    enabled: bool = True
    last_run: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)


class EvalScheduler:
    """定时评估调度器"""

    def __init__(self, db_path: str = "data/eval_data/continuous_eval.db"):
        self.schedules: List[EvalSchedule] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def add_schedule(self, schedule: EvalSchedule):
        self.schedules.append(schedule)

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print(f"[调度器] 已启动，共 {len(self.schedules)} 个任务")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _run_loop(self):
        while self._running:
            now = datetime.now()
            for sched in self.schedules:
                if not sched.enabled:
                    continue
                if sched.last_run is None or (now - sched.last_run) >= timedelta(
                    hours=sched.interval_hours
                ):
                    print(f"[调度器] 触发: {sched.name}")
                    try:
                        sched.eval_fn()
                        sched.last_run = datetime.now()
                        print(f"[调度器] ✅ {sched.name} 完成")
                    except Exception as e:
                        print(f"[调度器] ❌ {sched.name} 失败: {e}")
            time.sleep(60)
