# 智能路由算法设计文档

## 1. 设计背景与问题定义

### 1.1 背景溯源

在 ANP（Agent Network Protocol）协议中，当网络规模扩展后，消息路由面临三个核心挑战：

**问题来源一：固定路由的局限性**

原始 ANP 实现（implementation.py:208-237）仅支持固定的直接路由或一跳中转：

```python
# 原始路由逻辑（简化版）
def route_message(self, from_node, to_node, message):
    # 方式1：直接路由
    if to_node in self._connections.get(from_node, []):
        return [from_node, to_node]
    # 方式2：一跳中转
    for intermediate in self._connections.get(from_node, []):
        if to_node in self._connections.get(intermediate, []):
            return [from_node, intermediate, to_node]
    return None
```

这种方案存在以下问题：
- **不考虑节点能力**：无法根据任务需求选择具备相应能力的智能体
- **不考虑运行时状态**：无法根据负载、延迟等动态选择最优路径
- **不考虑成本因素**：无法在预算约束下选择最优方案

**问题来源二：单维度选择的不足**

简单轮询或随机选择的方案：

```python
def simple_route(self, services):
    return random.choice(services)  # 随机选择，无依据
```

在多智能体协作场景中，这种选择方式会导致：
- **负载不均**：某些智能体过载，其他闲置
- **能力错配**：任务分配给不具备相应能力的智能体
- **响应延迟高**：未考虑网络延迟和响应时间

### 1.2 业务需求

基于 HelloAgents 框架的实际应用场景，需要支持以下需求：

1. **多能力匹配**：任务需要"文本分析"能力，但网络中有多个智能体提供该能力
2. **负载均衡**：避免单点过载，需根据实时负载分配请求
3. **延迟敏感**：实时任务需要选择响应最快的路径
4. **成本控制**：商业场景需考虑调用成本
5. **容错机制**：主节点故障时自动切换到备用节点

### 1.3 设计目标

| 目标 | 描述 | 优先级 |
|------|------|--------|
| 能力匹配 | 根据任务需求匹配具备相应能力的智能体 | P0 |
| 负载均衡 | 动态分配请求，避免单点过载 | P0 |
| 延迟优化 | 选择响应最快的路径 | P1 |
| 成本控制 | 在预算约束下选择最优方案 | P1 |
| 高可用 | 故障检测与自动转移 | P1 |

---

## 2. 系统架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Smart Router Architecture                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    2. Routing Policy                           │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │  Strategy: CAPABILITY_MATCH / LOAD_BALANCE /            │  │   │
│  │  │           LATENCY_MIN / COST_OPTIMAL / HYBRID           │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    3. Multi-Factor Scoring                      │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ ┌───────┐│   │
│  │  │Capabi-  │ │  Load   │ │ Latency │ │Success │ │ Cost  │ │...   │   │
│  │  │lity(35%)│ │Balance │ │  (20%) │ │ Rate  │ │(10%) │ │     │   │
│  │  │         │ │ (25%)  │ │         │ │ (10%) │ │       │ │     │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────┘ └───────┘│   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    4. Route Selection                           │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │  • Score Ranking  • Constraint Filter  • Fallback       │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              ↓                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    5. Best Route Output                         │   │
│  │  ┌─────────────────────────────────────────────────────────┐  │   │
│  │  │  Agent_A → Agent_B → ... (with confidence & reason)     │  │   │
│  │  └─────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心模块交互

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Task      │────▶│  RoutingContext  │────▶│  Router    │
│  Submitter  │     │    Builder     │     │  Engine   │
└──────────────┘     └──────────────────┘     └──────────────┘
                                                    │
                              ┌─────────────────────┼─────────────┐
                              ↓                     ↓             ↓
                    ┌──────────────┐     ┌──────────────┐
                    │ Agent Score │     │  Score     │
                    │ Calculator│     │  Aggregator│
                    └──────────────┘     └──────────────┘
                              ↓                     ↓
                    ┌──────────────────────────────────────┐
                    │              Route Result            │
                    │  • best_agent_id  • score  • reason  │
                    └──────────────────────────────────────┘
```

---

## 3. 数据结构设计

### 3.1 核心数据类

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum


class TaskType(Enum):
    """任务类型枚举"""
    TEXT_PROCESSING = "text_processing"
    IMAGE_PROCESSING = "image_processing"
    DATA_ANALYSIS = "data_analysis"
    REALTIME = "realtime"
    BATCH = "batch"


class RoutingStrategy(Enum):
    """路由策略枚举"""
    CAPABILITY_MATCH = "capability_match"   # 能力匹配优先
    LOAD_BALANCE = "load_balance"           # 负载均衡优先
    LATENCY_MIN = "latency_min"             # 延迟最小优先
    COST_OPTIMAL = "cost_optimal"           # 成本最优
    HYBRID = "hybrid"                       # 综合多因子


@dataclass
class AgentCapability:
    """智能体能力描述"""
    service_type: str
    algorithms: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    accuracy: float = 0.0
    specializations: List[str] = field(default_factory=list)


@dataclass
class AgentMetrics:
    """智能体运行时指标"""
    load: float = 0.0               # 负载率 0.0-1.0
    latency_ms: float = 0.0         # 平均延迟
    success_rate: float = 1.0       # 成功率
    throughput: float = 0.0         # 吞吐量
    cost_per_request: float = 0.0   # 单次请求成本


@dataclass
class AgentInfo:
    """智能体完整信息"""
    agent_id: str
    name: str
    endpoint: str
    capabilities: AgentCapability
    metrics: AgentMetrics
    status: str = "online"


@dataclass
class RoutingContext:
    """路由上下文"""
    task_type: TaskType
    requirements: Dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"
    budget: Optional[float] = None
    deadline_ms: Optional[int] = None


@dataclass
class RouteScore:
    """路由评分结果"""
    agent_id: str
    total_score: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)
    reason: str = ""
```

### 3.2 数据流转换

```
输入数据                    处理过程                    输出数据
─────────────────────────────────────────────────────────

Task Submitter            RoutingContext              RouteScore
  │                    Builder                  │
  ▼                    ▼                        ▼
{                     ┌─────────────────┐     ┌──────────────┐
task_type:            │ task_type:       │     │ agent_id:   │
"text_..."      ────▶│ TaskType        │────▶│ "agent_1"  │
requirements:         │ Requirements    │     │ total: 0.85│
["sentiment"]        │ Dict           │     │ factors:   │
priority:        │ Priority:       │     │ {cap: 0.9, │
"high"            │ "normal"        │     │  load: 0.7}│
                    │ Budget/Deadline │     │ reason:    │
                    └─────────────────┘     │ "Best..."  │
                                          └──────────────┘
```

---

## 4. 算法核心设计

### 4.1 多因子评分算法

```python
DEFAULT_WEIGHTS = {
    "capability_match": 0.35,  # 能力匹配
    "load_balance": 0.25,       # 负载均衡
    "latency": 0.20,           # 延迟
    "success_rate": 0.10,       # 成功率
    "cost": 0.10               # 成本
}


class SmartRouter:
    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.HYBRID):
        self.strategy = strategy
        self.agents: Dict[str, AgentInfo] = {}
        self.weights = DEFAULT_WEIGHTS.copy()

    def route(self, context: RoutingContext) -> Optional[RouteScore]:
        """
        主路由方法
        """
        # 步骤1：根据条件筛选候选智能体
        candidates = self._filter_candidates(context)

        # 步骤2：无候选时返回 None
        if not candidates:
            return None

        # 步骤3：计算每个候选的评分
        scores = [self._calculate_score(agent, context) for agent in candidates]

        # 步骤4：排序选择最优
        scores.sort(key=lambda x: x.total_score, reverse=True)

        # 步骤5：返回最佳结果
        return scores[0]
```

### 4.2 分项评分计算

#### 4.2.1 能力匹配评分

```python
def _calculate_capability_score(
    self,
    agent: AgentInfo,
    context: RoutingContext
) -> float:
    """
    计算能力匹配分数

    评分依据：
    1. 服务类型匹配 (权重 0.4)
    2. 算法能力匹配 (权重 0.3)
    3. 语言支持匹配 (权重 0.2)
    4. 专业领域匹配 (权重 0.1)

    计算公式：
    score = Σ(匹配项数 / 要求项数 × 权重)

    注：各维度独立计算，满分为1.0（各维度相加的理论最大值）
    但实际评分可能小于1.0，取决于具体匹配情况
    """
    score = 0.0
    caps = agent.capabilities

    # 服务类型匹配 (0.4)
    if context.task_type.value == caps.service_type:
        score += 0.4

    # 算法匹配 (0.3)
    required = context.requirements.get("algorithms", [])
    if required:
        matched = len(set(required) & set(caps.algorithms))
        score += matched / len(required) * 0.3

    # 语言匹配 (0.2)
    languages = context.requirements.get("languages", [])
    if languages:
        matched = len(set(languages) & set(caps.languages))
        score += matched / len(languages) * 0.2

    # 专业领域匹配 (0.1)
    specs = context.requirements.get("specializations", [])
    if specs:
        matched = len(set(specs) & set(caps.specializations))
        score += matched / len(specs) * 0.1

    return min(score, 1.0)
```

**评分示例说明：**

假设智能体A具备以下能力：
```
Agent A:
  service_type: "text_processing"
  algorithms: ["sentiment", "ner"]
  languages: ["en", "zh"]
  specializations: ["finance"]
```

| 测试场景 | 要求 | 得分计算 | 结果 |
|---------|------|---------|------|
| 完美匹配 | task_type=text_processing<br>algorithms=[sentiment,ner]<br>languages=[en,zh]<br>specializations=[finance] | 0.4 + 0.3 + 0.2 + 0.1 | **1.0** |
| 部分匹配 | task_type=text_processing<br>algorithms=[sentiment,ner,translation]<br>languages=[en,zh,ja] | 0.4 + (2/3)×0.3 + (2/3)×0.2 | **0.83** |
| 不匹配 | task_type=image_processing<br>algorithms=[translation]<br>languages=[ja] | service_type不匹配得0，<br>(0/1)×0.3 + (0/1)×0.2 | **0.0** |

**测试用例映射：**

1. `test_capability_score_perfect_match`: 完美匹配场景，期望得分 1.0
2. `test_capability_score_partial_match`: 部分匹配，得分在 0.5-1.0 之间
3. `test_capability_score_no_match`: task_type不匹配时各项均不得分，总分 < 0.5

#### 4.2.2 负载均衡评分

```python
def _calculate_load_score(self, agent: AgentInfo) -> float:
    """
    计算负载均衡分数

    评分依据：负载越低分数越高

    评分公式：
    score = 1.0 - load  (当 load ∈ [0, 1])
    score = 0.0          (当 load > 1 或 load < 0 即异常)
    """
    load = agent.metrics.load
    if 0 <= load <= 1:
        return 1.0 - load
    return 0.0
```

#### 4.2.3 延迟评分

```python
def _calculate_latency_score(self, agent: AgentInfo) -> float:
    """
    计算延迟分数

    评分依据：延迟越低分数越高

    评分公式：
    score = 1.0                (当 latency <= 0)
    score = 1.0 - l/100*0.2   (当 0 < latency < 100)
    score = 0.8 - (l-100)/400*0.3  (当 100 <= latency < 500)
    score = max(0, 0.5 - (l-500)/1000*0.5)  (当 latency >= 500)

    阈值设定：
    - <= 0ms: 满分 1.0
    - < 100ms: 高分 (0.8-1.0)
    - 100-500ms: 中等 (0.5-0.8)
    - > 500ms: 低分 (0.0-0.5)
    """
    latency = agent.metrics.latency_ms

    if latency <= 0:
        return 1.0
    elif latency < 100:
        return 1.0 - (latency / 100) * 0.2
    elif latency < 500:
        return 0.8 - ((latency - 100) / 400) * 0.3
    else:
        return max(0.0, 0.5 - ((latency - 500) / 1000) * 0.5)
```

#### 4.2.4 成功率评分

```python
def _calculate_success_rate_score(self, agent: AgentInfo) -> float:
    """
    计算成功率分数

    评分依据：成功率越高分数越高

    评分公式：直接使用成功率值
    """
    return agent.metrics.success_rate
```

#### 4.2.5 成本评分

```python
def _calculate_cost_score(
    self,
    agent: AgentInfo,
    context: RoutingContext
) -> float:
    """
    计算成本分数

    评分依据：在预算内越便宜分数越高

    评分公式：
    score = 1.0                   (当 budget 为 None，无预算限制)
    score = (budget - cost) / budget  (当 cost < budget)
    score = 0.0                   (当 cost >= budget)
    """
    budget = context.budget
    cost = agent.metrics.cost_per_request

    if budget is None:
        return 1.0  # 无预算限制

    if cost <= budget:
        return (budget - cost) / budget
    return 0.0
```

### 4.3 综合评分聚合

```python
def _calculate_score(
    self,
    agent: AgentInfo,
    context: RoutingContext
) -> RouteScore:
    """
    计算综合评分

    计算公式：
    total_score = Σ(factor_score × factor_weight) / Σ(weights)

    其中 factor ∈ {
        capability_match,
        load_balance,
        latency,
        success_rate,
        cost
    }
    """
    weights = self._adjust_weights(context)
    factors = {}

    # 各因子评分
    factors["capability_match"] = self._calculate_capability_score(agent, context)
    factors["load_balance"] = self._calculate_load_score(agent)
    factors["latency"] = self._calculate_latency_score(agent)
    factors["success_rate"] = self._calculate_success_rate_score(agent)
    factors["cost"] = self._calculate_cost_score(agent, context)

    # 加权求和
    total = sum(
        factors[key] * weights.get(key, 0)
        for key in factors
    )

    # 归一化
    weight_sum = sum(weights.values())
    if weight_sum > 0:
        total /= weight_sum

    # 生成原因说明
    reason = (
        f"能力:{factors['capability_match']:.2f}, "
        f"负载:{factors['load_balance']:.2f}, "
        f"延迟:{factors['latency']:.2f}"
    )

    return RouteScore(
        agent_id=agent.agent_id,
        total_score=total,
        factors=factors,
        reason=reason
    )
```

---

## 5. 路由策略设计

### 5.1 策略模式

```python
def _adjust_weights(self, context: RoutingContext) -> Dict[str, float]:
    """
    根据策略调整权重

    不同策略下的权重配置：
    """
    weights = DEFAULT_WEIGHTS.copy()

    if self.strategy == RoutingStrategy.CAPABILITY_MATCH:
        weights = {"capability_match": 0.6, "load_balance": 0.2,
                 "latency": 0.1, "success_rate": 0.1, "cost": 0.0}

    elif self.strategy == RoutingStrategy.LOAD_BALANCE:
        weights = {"capability_match": 0.2, "load_balance": 0.5,
                 "latency": 0.15, "success_rate": 0.15, "cost": 0.0}

    elif self.strategy == RoutingStrategy.LATENCY_MIN:
        weights = {"capability_match": 0.2, "load_balance": 0.1,
                 "latency": 0.6, "success_rate": 0.1, "cost": 0.0}

    elif self.strategy == RoutingStrategy.COST_OPTIMAL:
        weights = {"capability_match": 0.25, "load_balance": 0.15,
                 "latency": 0.15, "success_rate": 0.15, "cost": 0.3}

    # HYBRID 使用默认权重
    return weights
```

### 5.2 约束过滤

```python
def _filter_candidates(
    self,
    context: RoutingContext
) -> List[AgentInfo]:
    """
    过滤候选智能体

    过滤规则：
    1. 在线状态过滤
    2. 能力匹配过滤（必需）
    3. 预算约束过滤
    """
    candidates = []

    for agent in self.agents.values():
        # 状态过滤
        if agent.status != "online":
            continue

        # 能力过滤（必需）
        if not self._has_required_capability(agent, context):
            continue

        # 预算过滤
        if context.budget and agent.metrics.cost_per_request > context.budget:
            continue

        candidates.append(agent)

    return candidates


def _has_required_capability(
    self,
    agent: AgentInfo,
    context: RoutingContext
) -> bool:
    """
    检查是否具备必需能力

    判定条件：task_type 与 service_type 匹配
    """
    if context.task_type.value == agent.capabilities.service_type:
        return True
    return False
```

---

## 6. 测试验证

### 6.1 测试覆盖

| 测试用例 | 覆盖内容 |
|---------|---------|
| test_register_agent | 智能体注册 |
| test_capability_filter | 能力过滤 |
| test_capability_score_perfect_match | 能力评分-完美匹配 |
| test_capability_score_partial_match | 能力评分-部分匹配 |
| test_capability_score_no_match | 能力评分-不匹配 |
| test_load_score | 负载评分 |
| test_latency_score | 延迟评分 |
| test_success_rate_score | 成功率评分 |
| test_cost_score_with_budget | 成本评分-有预算 |
| test_cost_score_no_budget | 成本评分-无预算 |
| test_route_basic | 基础路由 |
| test_route_with_requirements | 带需求路由 |
| test_route_with_budget | 带预算路由 |
| test_strategy_capability_match | 能力匹配策略 |
| test_strategy_load_balance | 负载均衡策略 |
| test_strategy_latency_min | 延迟最小策略 |
| test_strategy_cost_optimal | 成本最优策略 |
| test_offline_agent_filter | 离线智能体过滤 |
| test_no_candidates | 无候选智能体 |
| test_weight_adjustment | 权重调整 |
| test_zero_load | 边界-零负载 |
| test_negative_load | 边界-负负载 |
| test_zero_latency | 边界-零延迟 |
| test_very_high_latency | 边界-极高延迟 |

---

## 7. 演进路径

### 7.1 规模演进

| 阶段 | 规模 | 路由策略 | 实现方式 |
|------|------|---------|---------|
| 初始 | 10 | 简单轮询 | 内存路由表 |
| 成长 | 50 | 加权轮询 | 本地缓存 |
| 扩展 | 100 | 智能多因子 | 分布式发现 |
| 大规模 | 1000 | 分层路由 | 层级协调 |

### 7.2 算法演进

```
阶段1: 随机/轮询
  route = random.choice(agents)

阶段2: 能力过滤 + 随机
  qualified = [a for a in agents if a.has_capability(required)]
  route = random.choice(qualified)

阶段3: 多因子评分 (当前设计)
  score = 0.35×cap + 0.25×load + 0.20×lat + ...
  route = max(scores)

阶段4: 实时学习
  score = f(cap, load, lat, history_feedback)
  route = model.predict(route)
```

---

## 8. 性能考量

### 8.1 时间复杂度

| 操作 | 时间复杂度 | 说明 |
|------|---------|------|
| 路由选择 | O(n) | n = 候选智能体数 |
| 能力过滤 | O(n×m) | m = 能力维度数 |
| 综合评分 | O(n×k) | k = 评分因子数 |

### 8.2 空间复杂度

| 数据 | 空间复杂度 | 说明 |
|------|---------|-------|
| 智能体缓存 | O(n) | n = 智能体数 |
| 评分缓存 | O(n) | 每个智能体一份 |
| 历史记录 | O(h) | h = 历史记录数 |

---

## 9. 设计总结

### 9.1 设计优势

1. **灵活性**：支持多种路由策略，可根据场景选择
2. **可扩展性**：易于添加新的评分因子
3. **可观测性**：每个评分都有详细的 reason 说明

### 9.2 潜在改进方向

1. **容错机制**：添加 FaultDetector 故障检测器和 get_fallback_routes 备用路由机制
2. **机器学习增强**：基于历史数据学习最优权重
3. **实时指标采集**：集成监控系统获取实时数据
4. **A/B测试支持**：支持路由策略对比实验
5. **分层路由**：支持大规模网络的层级路由
6. **截止时间过滤**：在 _filter_candidates 中增加 deadline_ms 约束过滤
