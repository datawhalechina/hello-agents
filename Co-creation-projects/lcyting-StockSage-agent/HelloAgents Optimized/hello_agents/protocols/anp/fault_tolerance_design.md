# 智能体网络容错机制设计文档

## 1. 设计背景与问题定义

### 1.1 场景溯源

在"智能城市"系统中，多个智能体协作管理城市运行：

```
┌─────────────────────────────────────────────────────────────────┐
│                    智能城市系统架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │  交通管理  │    │  环境监测  │    │  能源调度  │         │
│  │  智能体   │    │  智能体   │    │  智能体   │         │
│  │ (关键)    │    │  (重要)   │    │  (重要)   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│         │                 │                 │                    │
│         └─────────────────┼─────────────────┘                    │
│                          ↓                                      │
│               ┌─────────────────────┐                          │
│               │    协调中心智能体    │                          │
│               └─────────────────────┘                          │
└─────────────────────────────────────────────────────────────────┘
```

在10.4.4节的案例中，交通管理智能体是关键服务，一旦故障会导致：
- 交通信号失控
- 交通事故无法预警
- 城市拥堵加剧

### 1.2 问题来源

原始ANP实现的故障处理缺失：

```python
# implementation.py 中缺少故障处理
class ANPNetwork:
    def route_message(self, from_node, to_node, message):
        # 直接发送，无故障检测
        if to_node in self._connections.get(from_node, []):
            return [from_node, to_node]
        return None  # 失败则返回None，无重试机制
```

**核心问题：**
| 问题 | 影响 |
|------|------|
| 无故障检测 | 不可用智能体仍被路由 |
| 无备份切换 | 故障后需人工干预 |
| 无状态恢复 | 故障智能体恢复后数据丢失 |
| 无告警机制 | 故障无法被感知 |

### 1.3 业务需求

| 需求 | 描述 | 优先级 |
|------|------|--------|
| 故障检测 | 实时监控智能体健康状态 | P0 |
| 自动切换 | 故障后自动切换到备份 | P0 |
| 状态恢复 | 支持故障后状态恢复 | P1 |
| 故障告警 | 通知管理员故障事件 | P1 |
| 降级服务 | 部分功能可用 | P2 |

---

## 2. 系统架构

### 2.1 完整系统架构图

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                           FAULT TOLERANCE SYSTEM ARCHITECTURE                                           │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐               │
│  │                              SYSTEM INPUT                                                          │               │
│  │                           (Task / Request)                                                          │               │
│  └─────────────────────────────────────────────────────────────────────────────────────┘               │
│                                              │                                                          │
│                                              ↓                                                          │
│  ┌─────────────────────────────────────────────────────────────────────────────────────┐               │
│  │                         ROUTER + SMART ROUTER                                                      │               │
│  │              (智能路由 + 容错感知)                                                                  │               │
│  └─────────────────────────────────────────────────────────────────────────────────────┘               │
│                                              │                                                          │
│                    ┌───────────────────────────┴───────────────────────────┐                            │
│                    ↓                                                   ↓                               │
│  ┌──────────────────────────┐                     ┌─────────────────────────────────┐                   │
│  │  HEALTH MONITOR         │                     │     FAULT DETECTOR               │                   │
│  │  (健康监控)             │                     │     (故障检测)                   │                   │
│  │                         │                     │                                  │                   │
│  │  ┌─────────────────┐    │                     │  检查项目:                        │                   │
│  │  │• 心跳检测        │    │                     │  ├─ 连续失败 ≥ 阈值?              │                   │
│  │  │• 指标采集        │    │                     │  ├─ 心跳超时 > 阈值?              │                   │
│  │  │• 日志分析        │    │                     │  └─ 失败率 > 50%?                │                   │
│  │  └─────────────────┘    │                     └─────────────────────────────────┘                   │
│  └──────────────────────────┘                           │                                               │
│                    │                                   ↓                                               │
│                    │         ┌──────────────────────────┐                                              │
│                    │         │   STATUS CHECK           │                                              │
│                    │         │  ┌────────────────┐     │                                              │
│                    │         │  │ HEALTHY        │──┘  │                                              │
│                    │         │  ├─DEGRADED       │     │                                              │
│                    │         │  ├─UNHEALTHY      │     │                                              │
│                    │         │  └─FAILED         │     │                                              │
│                    │         └───────────────────┘     │                                              │
│                    │                           │                                                      │
│                    │              ┌────────────┴────────────┐                                         │
│                    │              ↓                         ↓                                         │
│                    │   ┌──────────────────┐    ┌────────────────────┐                                 │
│                    ├─▶│  NORMAL ROUTE    │    │  FAILOVER MANAGER  │                                 │
│                    │   │  (正常路由)      │    │  (故障切换)        │                                 │
│                    │   │                  │    │                    │                                 │
│                    │   │  Agent A ──────▶│    │  ┌────────────┐    │                                 │
│                    │   │  (Primary)      │    │  │检查主状态  │    │                                 │
│                    │   └──────────────────┘    │  ├─健康      │    │                                 │
│                    │              ▲              │  ├─降级      │    │                                 │
│                    │              │              │  └─故障      │    │                                 │
│                    │              │              │  └────────────┘    │                                 │
│                    │              │              │        │           │                                 │
│                    │              │              │        ↓           │                                 │
│                    │              │    ┌─────────────────────────┘    │                                 │
│                    │              │    │                              │                                 │
│                    │              │    ↓                              │                                 │
│                    │    ┌─────────┴────────────────────┐              │                                 │
│                    │    │    SELECT BACKUP             │              │                                 │
│                    │    │  ┌────────────────────┐     │              │                                 │
│                    │    │  │ Backup_1 可用?     │────┼────┼─────────────────────────┤
│                    │    │  │ Backup_2 可用?     │     │                             │
│                    │    │  │ ...                │     │                             │
│                    │    │  └────────────────────┘     │                             │
│                    │    └───────────────────────────┘ │                             │
│                    │              │                 │                             │
│                    │              │                 │                             │
│                    │              ↓                 │                             │
│                    │    ┌──────────────────────────┐ │                             │
│                    │    │   STATE SYNC             │ │                             │
│                    │    │  (状态同步)              │ │                             │
│                    │    │                          │ │                             │
│                    │    │  checkpoint 保存 ────────▶│ │                             │
│                    │    │  实时/批量同步            │ │                             │
│                    │    └──────────────────────────┘ │                             │
│                    │              │                 │                             │
│                    │              └────────┬────────┘                             │
│                    │                     ▼                                        │
│                    │  ┌─────────────────────────────────────────┐                 │
│                    │  │           RECOVERY MANAGER              │                 │
│                    │  │           (状态恢复)                    │                 │
│                    │  │                                         │                 │
│                    │  │  ┌───────────────────────────────┐      │                 │
│                    │  │  │• 检查点保存                    │      │                 │
│                    │  │  │• 状态恢复                      │      │                 │
│                    │  │  │• 数据补偿                      │      │                 │
│                    │  │  └───────────────────────────────┘      │                 │
│                    │  └─────────────────────────────────────────┘                 │
│                    │                           │                                  │
│                    │                           ▼                                  │
│                    └───────────────────────────────────────────────────────▶ OUTPUT│
│                                                                          (Result) │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 组件交互时序图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TIMING DIAGRAM                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Time ──────────────────────────────────────────────────────────────────────▶│
│                                                                              │
│  T0      T1      T2      T3      T4      T5      T6      T7                │
│   │       │       │       │       │       │       │       │                 │
│   ▼       │       │       │       │       │       │       ▼                │
│ ┌────┐   │       │       │       │       │       │  ┌─────────┐           │
│ │Task│   │       │       │       │       │       │  │ 输出    │           │
│ │请求│───▶│       │       │       │       │       │  │ 结果   │           │
│ └────┘   │       │       │       │       │       │  └─────────┘           │
│   │      │       │       │       │       │       │       ▲                 │
│   │      ▼       │       │       │       │       │       │                 │
│   │  ┌───────┐   │       │       │       │       │       │                 │
│   │  │Router │   │       │       │       │       │       │                 │
│   │  └──┬───┘   │       │       │       │       │       │                 │
│   │     │       │       │       │       │       │       │                 │
│   │     ▼       │       │       │       │       │       │                 │
│   │  ┌───────┴──┐       │       │       │       │       │                 │
│   │  │检测主健康│       │       │       │       │       │                 │
│   │  └────┬───┘  │       │       │       │       │       │                 │
│   │     │ │      │       │       │       │       │       │                 │
│   │     │ └──┐   │       │       │       │       │       │                 │
│   │     │  ┌─┴─┐ │       │       │       │       │       │                 │
│   ▼     ▼  ▼  ▼ ▼       │       │       │       │       │                 │
│ ┌────┐  ┌────┐ ┌────┐┌────┐  │       │       │       │                 │
│ │成功│  │失败│ │降级││超时│  │       │       │       │                 │
│ │    │  │    │ │    ││    │  │       │       │       │                 │
│ └┬───┘  └┬───┘ └┬───┘└──┬─┘  │       │       │       │                 │
│  │       │     │   │    │   │       │       │       │                 │
│  │       └─────┼───┼────┼───┼───────┼───────┼───────┘                 │
│  │             │   │    │   │       │       │                           │
│  ▼             ▼   ▼    ▼   ▼       ▼       ▼                           │
│ ┌──────────────────────────────────────────────────────────────┐        │
│ │                    FAILOVER DECISION                          │        │
│ │  ┌───────────────────────────────────────────────────────┐  │        │
│ │  │  IF 主非健康 (DEGRADED / UNHEALTHY / FAILED) THEN:   │  │        │
│ │  │    1. 查找可用备份                                    │  │        │
│ │  │    2. 同步状态                                        │  │        │
│ │  │    3. 切换路由                                        │  │        │
│ │  │  ELSE (主健康):                                       │  │        │
│ │  │    保持原路由，返回 None                              │  │        │
│ │  └───────────────────────────────────────────────────────┘  │        │
│ └──────────────────────────────────┬──────────────────────┘        │
│                                    │                               │
│                                    ▼                               │
│                             ┌─────────────┐                       │
│                             │  ROUTE TO   │                       │
│                             │  Primary    │ ──▶ (正常)            │
│                             │  Backup     │ ──▶ (故障切换)        │
│                             └─────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 核心组件交互

```
Task ──▶ Router ──▶ FaultDetector ──▶ FailoverManager ──▶ Backup Agent
                         ↑                    │
                         │                    ↓
                    ┌────┴────┐        ┌────┴────┐
                    │  Agent  │        │ Recovery
                    │ Health  │        │ Manager
                    └─────────┘        └─────────┘
```

---

## 3. 数据结构设计

### 3.1 健康状态

```python
class HealthStatus(Enum):
    HEALTHY = "healthy"        # 健康
    DEGRADED = "degraded"      # 降级（部分功能可用）
    UNHEALTHY = "unhealthy"    # 不健康
    FAILED = "failed"          # 故障
```

### 3.2 故障类型

```python
class FaultType(Enum):
    NONE = "none"
    TIMEOUT = "timeout"                # 请求超时
    CONNECTION_ERROR = "conn"          # 连接错误
    HIGH_FAILURE_RATE = "high_fail"    # 高失败率
    RESOURCE_EXHAUSTED = "resources"   # 资源耗尽
    UNKNOWN = "unknown"                # 未知错误
```

### 3.3 智能体信息扩展

```python
@dataclass
class AgentHealth:
    """智能体健康信息"""
    agent_id: str
    status: HealthStatus = HealthStatus.HEALTHY
    fault_type: FaultType = FaultType.NONE
    failure_count: int = 0
    success_count: int = 0
    consecutive_failures: int = 0
    last_heartbeat: float = 0.0
    last_failure_time: float = 0.0


@dataclass
class BackupConfig:
    """备份配置"""
    primary_id: str
    backup_ids: List[str]              # 备用智能体ID列表
    sync_enabled: bool = True          # 状态同步
    sync_interval: int = 5             # 同步间隔(秒)
    failover_threshold: int = 3        # 故障切换阈值
```

---

## 4. 核心算法设计

### 4.1 故障检测器

```python
class FaultDetector:
    """故障检测器"""

    def __init__(
        self,
        failure_threshold: int = 3,         # 连续失败次数阈值
        timeout_threshold: float = 5.0,     # 超时阈值(秒)
        heartbeat_interval: float = 10.0    # 心跳间隔(秒)
    ):
        self.failure_threshold = failure_threshold
        self.timeout_threshold = timeout_threshold
        self.heartbeat_interval = heartbeat_interval

    def check_health(
        self,
        health: AgentHealth,
        current_time: float
    ) -> HealthStatus:
        """检查健康状态"""

        # 检测优先级：连续失败 > 心跳超时 > 高失败率

        # 1. 连续失败检测
        if health.consecutive_failures >= self.failure_threshold:
            return HealthStatus.FAILED

        # 2. 心跳超时检测
        if current_time - health.last_heartbeat > self.heartbeat_interval:
            return HealthStatus.UNHEALTHY

        # 3. 高失败率检测
        total = health.failure_count + health.success_count
        if total > 0:
            failure_rate = health.failure_count / total
            if failure_rate > 0.5:  # 失败率超过50%
                return HealthStatus.DEGRADED

        return HealthStatus.HEALTHY
```

### 4.2 故障检测流程

```
┌─────────────────────────────────────────────────────────────┐
│                  Fault Detection Flow                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  check_health(health, current_time)                         │
│       │                                                     │
│       ├── consecutive_failures ≥ threshold?                 │
│       │       └── Yes ──▶ FAILED                            │
│       │                                                     │
│       ├── 心跳超时?                                         │
│       │       └── Yes ──▶ UNHEALTHY                         │
│       │                                                     │
│       ├── 失败率 > 50%?                                     │
│       │       └── Yes ──▶ DEGRADED                          │
│       │                                                     │
│       └── 全部通过 ──▶ HEALTHY                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 故障切换器

```python
class FailoverManager:
    """故障切换管理器"""

    def __init__(self, detector: FaultDetector):
        self.detector = detector
        self.backups: Dict[str, BackupConfig] = {}
        self.health: Dict[str, AgentHealth] = {}

    def register_primary_with_backup(
        self,
        primary_id: str,
        backup_ids: List[str]
    ):
        """注册主备关系"""
        self.backups[primary_id] = BackupConfig(
            primary_id=primary_id,
            backup_ids=backup_ids
        )
        self.health[primary_id] = AgentHealth(agent_id=primary_id)

    def record_request(
        self,
        agent_id: str,
        success: bool,
        current_time: float
    ):
        """记录请求结果"""
        if agent_id not in self.health:
            self.health[agent_id] = AgentHealth(agent_id=agent_id)

        health = self.health[agent_id]
        health.last_heartbeat = current_time

        if success:
            health.success_count += 1
            health.consecutive_failures = 0
        else:
            health.failure_count += 1
            health.consecutive_failures += 1
            health.last_failure_time = current_time

    def get_failover_target(
        self,
        primary_id: str,
        current_time: float
    ) -> Optional[str]:
        """
        获取故障切换目标

        判定逻辑：
        - 若主智能体健康 (HEALTHY)：不切换，返回 None
        - 若主非健康（DEGRADED / UNHEALTHY / FAILED）：遍历备份列表，
          返回第一个健康的备份；若全部不可用则返回 None
        """
        if primary_id not in self.backups:
            return None

        health = self.health.get(primary_id)
        if not health:
            return None

        # 检查主智能体状态：仅当主非健康时才切换
        status = self.detector.check_health(health, current_time)
        if status == HealthStatus.HEALTHY:
            return None

        config = self.backups[primary_id]

        # 遍历检查所有备用
        for backup_id in config.backup_ids:
            backup_health = self.health.get(backup_id)
            if not backup_health:
                # 未监控的备用默认可用
                return backup_id

            status = self.detector.check_health(backup_health, current_time)
            if status == HealthStatus.HEALTHY:
                return backup_id

        return None
```

### 4.4 状态恢复器

```python
class RecoveryManager:
    """状态恢复管理器"""

    def __init__(self):
        self.state_snapshots: Dict[str, Any] = {}
        self.checkpoints: Dict[str, List[float]] = {}

    def save_checkpoint(self, agent_id: str, state: Any):
        """保存检查点（覆盖保存，保留最新状态）"""
        self.state_snapshots[agent_id] = state
        if agent_id not in self.checkpoints:
            self.checkpoints[agent_id] = []
        self.checkpoints[agent_id].append(time.time())

    def get_latest_checkpoint(self, agent_id: str) -> Optional[Any]:
        """获取最新检查点"""
        return self.state_snapshots.get(agent_id)

    def recover_state(
        self,
        from_agent_id: str,
        to_agent_id: str
    ) -> bool:
        """
        恢复状态到目标智能体

        from_agent_id: 源智能体（从中读取检查点）
        to_agent_id:   目标智能体（写入检查点）

        Returns:
            恢复成功返回 True，无检查点返回 False
        """
        checkpoint = self.get_latest_checkpoint(from_agent_id)
        if not checkpoint:
            return False

        self.save_checkpoint(to_agent_id, checkpoint)
        return True
```

---

## 5. 容错流程设计

### 5.1 完整容错流程

```
┌─────────────────────────────────────────────────────────────────┐
│                   Fault Tolerance Flow                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Task ──▶ Router ──▶ 是否需要容错？                              │
│                     │                                            │
│                    No                                            │
│                     │                                            │
│                     ↓                                           │
│              直接路由到目标                                      │
│                     │                                            │
│                    Yes                                           │
│                     │                                            │
│                     ↓                                           │
│         检查主智能体健康状态                                     │
│                     │                                            │
│           ┌───────┴───────┐                                      │
│           │               │                                      │
│         健康           非健康                                    │
│           │             │                                        │
│           ↓             ↓                                       │
│     直接路由      检查是否有备份                                │
│           │          │                                           │
│           │    ┌─────┴─────┐                                    │
│           │    │           │                                    │
│           │  有备份      无备份                                 │
│           │    │           │                                    │
│           │    ↓           ↓                                   │
│           │  切换到备份   返回 None                             │
│           │    │                                                │
│           │    ↓                                                │
│           │  状态同步到备份                                     │
│           │    │                                                │
│           │    ↓                                                │
│           │  返回路由结果                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. 智能城市场景应用

### 6.1 场景描述

```
智能城市系统中的关键智能体及备份：

| 智能体 | 角色 | 备份 | 关键程度 |
|-------|------|------|---------|
| 交通管理 | 主 | 交通备份1, 交通备份2 | 关键 |
| 环境监测 | 主 | 环境备份1 | 重要 |
| 能源调度 | 主 | 能源备份1 | 重要 |
```

### 6.2 配置示例

```python
# 创建容错组件
detector = FaultDetector(
    failure_threshold=3,
    timeout_threshold=5.0,
    heartbeat_interval=10.0
)
failover = FailoverManager(detector)
recovery = RecoveryManager()

# 注册主备关系
failover.register_primary_with_backup(
    primary_id="traffic_manager",
    backup_ids=["traffic_backup_1", "traffic_backup_2"]
)

failover.register_primary_with_backup(
    primary_id="env_monitor",
    backup_ids=["env_backup_1"]
)

# 完整容错流程示例
# 1. 保存状态检查点
recovery.save_checkpoint("traffic_manager", {"mode": "auto"})

# 2. 模拟三次失败
for i in range(3):
    failover.record_request("traffic_manager", False, current_time)

# 3. 获取故障切换目标
target = failover.get_failover_target("traffic_manager", current_time)
# target == "traffic_backup_1"

# 4. 恢复状态到备份
recovery.recover_state("traffic_manager", target)
# 备份的检查点为 {"mode": "auto"}
```

### 6.3 故障处理示例

```
时间线：交通管理智能体故障

T0: 交通管理正常运行，监控正常
    │
T1: 交通管理连续3次请求失败
    │
T2: FaultDetector标记为FAILED
    │
T3: FailoverManager检测到故障
    │
T4: 自动切换到traffic_backup_1
    │
T5: 状态同步完成（RecoveryManager恢复检查点）
    │
T6: 路由任务到备份智能体
    │
T7: 管理员收到告警
    │
T8: 人工介入或自动恢复
```

---

## 7. 测试用例设计

### 7.1 故障检测测试

| 测试用例 | 场景 | 期望结果 |
|---------|------|---------|
| test_detect_consecutive_failures | 连续失败3次 | 标记为FAILED |
| test_detect_heartbeat_timeout | 心跳超时 | 标记为UNHEALTHY |
| test_detect_high_failure_rate | 失败率>50% | 标记为DEGRADED |
| test_healthy_status | 正常请求 | 保持HEALTHY |
| test_boundary_consecutive_failures_2 | 连续失败2次（边界） | 保持HEALTHY |
| test_boundary_consecutive_failures_3 | 连续失败3次（边界） | 标记为FAILED |

### 7.2 故障切换测试

| 测试用例 | 场景 | 期望结果 |
|---------|------|---------|
| test_failover_to_backup | 主故障有备份 | 切换到备份 |
| test_failover_no_backup | 主故障无备份 | 返回None |
| test_failover_all_failed | 备份也故障 | 返回None |
| test_failover_healthy_primary | 主智能体健康 | 不切换，返回None |
| test_failover_unhealthy_primary | 主降级（非健康） | 切换到备份 |
| test_record_request_success | 记录成功请求 | success_count+1，连续失败清零 |
| test_record_request_failure | 记录失败请求 | failure_count+1，连续失败+1 |

### 7.3 状态恢复测试

| 测试用例 | 场景 | 期望结果 |
|---------|------|---------|
| test_save_checkpoint | 保存检查点 | 保存成功 |
| test_recover_state | 恢复状态 | 恢复成功，目标智能体获得检查点 |
| test_recover_no_checkpoint | 无检查点 | 返回False |
| test_multiple_checkpoints | 多次检查点 | 只保留最新状态 |

### 7.4 集成测试

| 测试用例 | 场景 | 期望结果 |
|---------|------|---------|
| test_full_fault_tolerance_flow | 完整容错流程 | 检测故障→切换备份→状态恢复 |

---

## 8. 设计总结

### 8.1 设计优势

1. **多层次检测**：连续失败、心跳超时、高失败率三重检测，优先级递进
2. **自动切换**：主非健康时自动转移到第一个健康的备份智能体
3. **状态恢复**：支持检查点保存和恢复
4. **可配置**：失败阈值、超时时间、心跳间隔可配置

### 8.2 潜在改进方向

1. **分布式协调**：使用Raft/Paxos实现分布式一致性
2. **智能预测**：基于历史数据预测故障
3. **自动修复**：自动重启失败的智能体
4. **蓝绿部署**：支持无感知版本切换
5. **StateSync状态同步机制**：支持实时/批量状态同步到备份
6. **与SmartRouter集成**：将FailoverManager注册到SmartRouter实现路由时自动容错
