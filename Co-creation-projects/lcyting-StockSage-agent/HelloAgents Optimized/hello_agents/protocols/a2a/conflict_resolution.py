"""
A2A 协议扩展 - 冲突解决机制

添加以下消息类型：
- negotiation: 协商消息，用于agent间讨论和达成共识
- voting: 投票消息，用于多agent投票决定
- task: 任务消息（已有）
- task_result: 任务结果消息（已有）

当多个agent对同一问题有不同意见时，可以使用：
1. 协商机制：通过交换观点达成共识
2. 投票机制：通过投票表决决定
"""

from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import threading


class MessageType(str, Enum):
    """A2A 扩展消息类型"""

    TASK = "task"
    TASK_RESULT = "task_result"
    NEGOTIATION = "negotiation"
    VOTING = "voting"
    VOTE_RESULT = "vote_result"


class ConflictStrategy(str, Enum):
    """冲突解决策略"""

    NEGOTIATION = "negotiation"
    VOTING = "voting"
    HIERARCHY = "hierarchy"
    RANDOM = "random"


@dataclass
class NegotiationMessage:
    """协商消息"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "negotiation"
    issue: str = ""
    position: str = ""
    rationale: str = ""
    participants: List[str] = field(default_factory=list)
    round: int = 1
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "issue": self.issue,
            "position": self.position,
            "rationale": self.rationale,
            "participants": self.participants,
            "round": self.round,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NegotiationMessage":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class Vote:
    """单张投票"""

    voter: str
    choice: str
    weight: float = 1.0
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "voter": self.voter,
            "choice": self.choice,
            "weight": self.weight,
            "rationale": self.rationale,
        }


@dataclass
class VotingMessage:
    """投票消息"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "voting"
    issue: str = ""
    options: List[str] = field(default_factory=list)
    votes: List[Dict[str, Any]] = field(default_factory=list)
    voters: List[str] = field(default_factory=list)
    deadline: Optional[str] = None
    status: str = "open"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def add_vote(
        self, voter: str, choice: str, weight: float = 1.0, rationale: str = ""
    ):
        self.votes.append(Vote(voter, choice, weight, rationale).to_dict())
        if voter not in self.voters:
            self.voters.append(voter)

    def get_results(self) -> Dict[str, float]:
        results = {}
        for vote in self.votes:
            choice = vote["choice"]
            weight = vote.get("weight", 1.0)
            results[choice] = results.get(choice, 0.0) + weight
        return results

    def get_winner(self) -> Optional[str]:
        results = self.get_results()
        if not results:
            return None
        return max(results, key=results.get)

    def is_complete(self) -> bool:
        return len(self.votes) >= len(self.voters) or self.status == "closed"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "issue": self.issue,
            "options": self.options,
            "votes": self.votes,
            "voters": self.voters,
            "deadline": self.deadline,
            "status": self.status,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VotingMessage":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class NegotiationManager:
    """协商管理器"""

    def __init__(self):
        self.active_negotiations: Dict[str, NegotiationMessage] = {}
        self.history: List[NegotiationMessage] = []
        self.lock = threading.Lock()

    def start_negotiation(
        self, issue: str, participants: List[str]
    ) -> NegotiationMessage:
        msg = NegotiationMessage(issue=issue, participants=participants, round=1)
        with self.lock:
            self.active_negotiations[msg.id] = msg
        return msg

    def add_position(
        self, negotiation_id: str, position: str, rationale: str = ""
    ) -> Optional[NegotiationMessage]:
        with self.lock:
            if negotiation_id not in self.active_negotiations:
                return None
            msg = self.active_negotiations[negotiation_id]
            msg.rationale = rationale
            msg.round += 1
            return msg

    def resolve(self, negotiation_id: str) -> Optional[str]:
        with self.lock:
            if negotiation_id not in self.active_negotiations:
                return None
            msg = self.active_negotiations.pop(negotiation_id)
            self.history.append(msg)
            return msg.position

    def get_consensus(self, positions: List[str]) -> Optional[str]:
        from collections import Counter

        counts = Counter(positions)
        most_common = counts.most_common(1)
        if most_common and most_common[0][1] > len(positions) / 2:
            return most_common[0][0]
        return None


class VotingManager:
    """投票管理器"""

    def __init__(self):
        self.active_polls: Dict[str, VotingMessage] = {}
        self.history: List[VotingMessage] = []
        self.lock = threading.Lock()

    def create_poll(
        self, issue: str, options: List[str], voters: List[str]
    ) -> VotingMessage:
        msg = VotingMessage(issue=issue, options=options, voters=voters)
        with self.lock:
            self.active_polls[msg.id] = msg
        return msg

    def vote(
        self,
        poll_id: str,
        voter: str,
        choice: str,
        weight: float = 1.0,
        rationale: str = "",
    ) -> bool:
        with self.lock:
            if poll_id not in self.active_polls:
                return False
            poll = self.active_polls[poll_id]
            if choice not in poll.options:
                return False
            poll.add_vote(voter, choice, weight, rationale)
            return True

    def close_poll(self, poll_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            if poll_id not in self.active_polls:
                return None
            poll = self.active_polls.pop(poll_id)
            poll.status = "closed"
            self.history.append(poll)
            return {
                "poll_id": poll.id,
                "issue": poll.issue,
                "results": poll.get_results(),
                "winner": poll.get_winner(),
                "total_votes": len(poll.votes),
            }


class ConflictResolver:
    """冲突解决器 - 统一接口"""

    def __init__(
        self,
        strategy: ConflictStrategy = ConflictStrategy.NEGOTIATION,
        threshold: float = 0.5,
    ):
        self.strategy = strategy
        self.threshold = threshold
        self.negotiation_manager = NegotiationManager()
        self.voting_manager = VotingManager()

    def resolve_by_negotiation(
        self, issue: str, participants: List[str], positions: Dict[str, str]
    ) -> Dict[str, Any]:
        """通过协商解决冲突"""
        neg = self.negotiation_manager.start_negotiation(issue, list(positions.keys()))
        for agent, pos in positions.items():
            neg.position = pos
        consensus = self.negotiation_manager.get_consensus(list(positions.values()))
        if consensus:
            return {
                "strategy": "negotiation",
                "resolved": True,
                "resolution": consensus,
                "negotiation_id": neg.id,
            }
        return {
            "strategy": "negotiation",
            "resolved": False,
            "positions": positions,
            "negotiation_id": neg.id,
            "message": "未能达成共识，建议使用投票",
        }

    def resolve_by_voting(
        self, issue: str, options: List[str], votes: Dict[str, str]
    ) -> Dict[str, Any]:
        """通过投票解决冲突"""
        voters = list(votes.keys())
        poll = self.voting_manager.create_poll(issue, options, voters)
        for voter, choice in votes.items():
            self.voting_manager.vote(poll.id, voter, choice)
        result = self.voting_manager.close_poll(poll.id)
        return {
            "strategy": "voting",
            "resolved": True,
            "resolution": result["winner"],
            "results": result["results"],
            "poll_id": poll.id,
        }

    def resolve(
        self, issue: str, positions: Dict[str, str], options: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """自动选择策略解决冲突"""
        if self.strategy == ConflictStrategy.NEGOTIATION:
            return self.resolve_by_negotiation(issue, list(positions.keys()), positions)
        elif self.strategy == ConflictStrategy.VOTING:
            if options is None:
                options = list(set(positions.values()))
            return self.resolve_by_voting(issue, options, positions)
        else:
            return {"error": f"Unknown strategy: {self.strategy}"}


class A2AExtendedServer:
    """扩展的 A2A 服务器 - 支持冲突解决"""

    def __init__(
        self,
        name: str,
        description: str,
        version: str = "1.0.0",
        conflict_strategy: ConflictStrategy = ConflictStrategy.VOTING,
    ):
        self.name = name
        self.description = description
        self.version = version
        self.skills = {}
        self.conflict_resolver = ConflictResolver(strategy=conflict_strategy)

    def add_skill(self, skill_name: str, func):
        self.skills[skill_name] = func
        return func

    def skill(self, skill_name: str):
        def decorator(func):
            self.add_skill(skill_name, func)
            return func

        return decorator

    def negotiate(
        self, issue: str, participants: List[str], positions: Dict[str, str]
    ) -> Dict[str, Any]:
        return self.conflict_resolver.resolve_by_negotiation(
            issue, participants, positions
        )

    def vote(
        self, issue: str, options: List[str], votes: Dict[str, str]
    ) -> Dict[str, Any]:
        return self.conflict_resolver.resolve_by_voting(issue, options, votes)

    def run(self, host: str = "0.0.0.0", port: int = 5000):
        try:
            from flask import Flask, request, jsonify
        except ImportError:
            raise ImportError("Requires Flask: pip install flask")

        app = Flask(self.name)

        @app.route("/negotiate", methods=["POST"])
        def negotiate():
            data = request.get_json() or {}
            issue = data.get("issue", "")
            participants = data.get("participants", [])
            positions = data.get("positions", {})
            result = self.negotiate(issue, participants, positions)
            return jsonify(result)

        @app.route("/vote", methods=["POST"])
        def do_vote():
            data = request.get_json() or {}
            issue = data.get("issue", "")
            options = data.get("options", [])
            votes = data.get("votes", {})
            result = self.vote(issue, options, votes)
            return jsonify(result)

        print(f"🚀 Extended A2A Server '{self.name}' starting on {host}:{port}")
        app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    print("=" * 50)
    print("A2A 冲突解决机制演示")
    print("=" * 50)

    resolver = ConflictResolver(strategy=ConflictStrategy.VOTING)

    print("\n【场景1】研究员和审稿人对论文评分有分歧")
    positions = {"researcher": "论文得分: 85", "reviewer": "论文得分: 72"}
    result = resolver.resolve(
        issue="论文评分", positions=positions, options=["85", "72", "78"]
    )
    print(f"冲突: {positions}")
    print(f"解决结果: {result}")

    print("\n【场景2】通过投票决定论文主题")
    votes = {
        "researcher": "人工智能医疗",
        "writer": "人工智能教育",
        "reviewer": "人工智能医疗",
    }
    result = resolver.resolve_by_voting(
        issue="论文主题选择",
        options=["人工智能医疗", "人工智能教育", "人工智能金融"],
        votes=votes,
    )
    print(f"投票: {votes}")
    print(f"解决结果: {result}")

    print("\n【场景3】通过协商达成共识")
    positions = {
        "researcher": "需要更多实验数据",
        "writer": "实验数据足够",
        "reviewer": "需要更多实验数据",
    }
    result = resolver.resolve_by_negotiation(
        issue="是否需要补充实验",
        participants=["researcher", "writer", "reviewer"],
        positions=positions,
    )
    print(f"各方观点: {positions}")
    print(f"解决结果: {result}")
