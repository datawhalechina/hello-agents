import re
import math
import random
from typing import Optional, List, Dict, Tuple, Iterator
from ..core.agent import Agent
from ..core.llm import HelloAgentsLLM
from ..core.config import Config
from ..core.stream import StreamEvent
from ..tools.registry import ToolRegistry


DEFAULT_GENERATE_PROMPT = """你是一个擅长多路径推理的AI助手。给定一个问题和当前推理进度，请生成{num_branches}个不同且合理的下一步思考方向。

每个思考方向应该是独立的、有区别的推理路径，覆盖不同的可能性或角度。

## 原始问题
{question}

## 当前推理进度
{history}

请严格按照以下格式输出{num_branches}个思考方向：
```
Thought 1: <第一个思考方向>
Thought 2: <第二个思考方向>
Thought 3: <第三个思考方向>
...
```
"""

DEFAULT_EVALUATE_PROMPT = """你是一个思维评估专家。请评估以下思考方向对解决问题的价值。

## 原始问题
{question}

## 可用的思考方向
{thoughts}

请分析每个方向的潜力，从以下维度评估（1-10分）：
1. 相关性：是否直接有助于解决问题
2. 可行性：该方向是否切实可行
3. 新颖性：是否提供了新的视角

请严格按照以下格式输出评估结果：
```
Evaluation 1: <分数> - <简要理由>
Evaluation 2: <分数> - <简要理由>
Evaluation 3: <分数> - <简要理由>
...
```
如果某个方向明显不可行，也可以给出0分。
"""

DEFAULT_SOLVE_PROMPT = """根据以下多个推理路径的结果，综合得出最终答案。

## 原始问题
{question}

## 推理路径及结果
{paths}

请综合所有推理路径，给出最终答案。
"""

DEFAULT_REFINE_PROMPT = """你是一个思维精炼专家。给定一个问题和一条初步的推理路径，请评估这条路径是否需要改进，如果有漏洞或不足，请给出改进版本。

## 原始问题
{question}

## 推理路径
{path}

## 初步结论
{solution}

请仔细检查推理链中是否存在逻辑漏洞、事实错误或遗漏的关键因素。
如果存在，请在下面输出改进后的推理和结论。
如果不需要改进，请直接输出"无需改进"。
"""


class ThoughtNode:
    """思维节点 - 表示树中的一个思考节点"""

    def __init__(
        self,
        content: str,
        depth: int = 0,
        score: float = 0.0,
        parent: Optional["ThoughtNode"] = None,
    ):
        self.content = content
        self.depth = depth
        self.score = score
        self.parent = parent
        self.children: List["ThoughtNode"] = []
        self.solution: Optional[str] = None
        self.visits: int = 0
        self.value: float = 0.0

    def add_child(self, child: "ThoughtNode") -> "ThoughtNode":
        self.children.append(child)
        child.parent = self
        return child

    def get_path(self) -> List[str]:
        path = []
        node = self
        while node:
            path.append(node.content)
            node = node.parent
        return list(reversed(path))

    def path_str(self, separator: str = " -> ") -> str:
        return separator.join(self.get_path())

    def get_ancestor(self, depth: int) -> Optional["ThoughtNode"]:
        if depth > self.depth:
            return None
        node = self
        while node and node.depth > depth:
            node = node.parent
        return node

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def best_child(self, exploration_weight: float = 1.0) -> Optional["ThoughtNode"]:
        if not self.children:
            return None

        def ucb(child: ThoughtNode) -> float:
            if child.visits == 0:
                return float("inf")
            exploitation = child.value / child.visits
            exploration = exploration_weight * math.sqrt(
                math.log(self.visits) / child.visits
            )
            return exploitation + exploration

        return max(self.children, key=ucb)

    def __repr__(self) -> str:
        return (
            f"ThoughtNode(content={self.content[:50]}, "
            f"depth={self.depth}, score={self.score}, "
            f"visits={self.visits}, value={self.value:.2f})"
        )


class TreeOfThoughtAgent(Agent):
    """
    Tree-of-Thought (ToT) Agent - 多路径推理与评估的智能体

    支持三种搜索策略：
    - BFS（广度优先）：保留每层评分最高的 k 个节点，继续扩展
    - DFS（深度优先）：每次只选评分最高的节点深入，回溯时尝试其他分支
    - MCTS（蒙特卡洛树搜索）：平衡探索与利用，通过多次模拟选择最优路径

    适合数学推理、逻辑谜题、复杂规划等需要探索多种可能性的任务。
    """

    def __init__(
        self,
        name: str,
        llm: HelloAgentsLLM,
        tool_registry: Optional[ToolRegistry] = None,
        system_prompt: Optional[str] = None,
        config: Optional[Config] = None,
        max_depth: int = 3,
        num_branches: int = 3,
        top_k: int = 2,
        strategy: str = "bfs",
        max_iterations: int = 50,
        custom_prompts: Optional[Dict[str, str]] = None,
    ):
        super().__init__(name, llm, system_prompt, config)

        self.tool_registry = tool_registry or ToolRegistry()
        self.max_depth = max_depth
        self.num_branches = num_branches
        self.top_k = top_k
        self.strategy = strategy.lower()
        self.max_iterations = max_iterations

        if self.strategy not in ("bfs", "dfs", "mcts"):
            raise ValueError(
                f"Unsupported strategy: {strategy}, use 'bfs', 'dfs', or 'mcts'"
            )

        self.prompts = custom_prompts or {}
        self._generate_prompt = self.prompts.get("generate", DEFAULT_GENERATE_PROMPT)
        self._evaluate_prompt = self.prompts.get("evaluate", DEFAULT_EVALUATE_PROMPT)
        self._solve_prompt = self.prompts.get("solve", DEFAULT_SOLVE_PROMPT)
        self._refine_prompt = self.prompts.get("refine", DEFAULT_REFINE_PROMPT)

        self.root = ThoughtNode(content="ROOT", depth=0)

    def run(self, input_text: str, **kwargs) -> str:
        conversation_id = kwargs.pop("conversation_id", None)

        print(f"\n{'=' * 60}")
        print(f"  Tree-of-Thought Agent: {self.name}")
        print(f"  问题: {input_text}")
        print(
            f"  策略: {self.strategy.upper()}, 最大深度: {self.max_depth}, "
            f"每层分支: {self.num_branches}"
        )
        print(f"{'=' * 60}")

        self.root = ThoughtNode(content="ROOT", depth=0)

        if self.strategy == "bfs":
            solution = self._bfs_search(input_text, **kwargs)
        elif self.strategy == "dfs":
            solution = self._dfs_search(input_text, **kwargs)
        else:
            solution = self._mcts_search(input_text, **kwargs)

        final_answer = (
            solution
            or "Sorry, I cannot solve this problem within the given reasoning depth."
        )

        self._save_conversation_messages(input_text, final_answer, conversation_id)

        print(f"\n{'=' * 60}")
        print("  最终答案:")
        print(f"  {final_answer}")
        print(f"{'=' * 60}")
        return final_answer

    def stream_run(self, input_text: str, **kwargs) -> Iterator[StreamEvent]:
        """
        流式运行Tree-of-Thought Agent，输出树搜索过程和最终答案

        Args:
            input_text: 用户问题
            **kwargs: 支持 conversation_id 参数

        Yields:
            StreamEvent: 流式事件
        """
        conversation_id = kwargs.pop("conversation_id", None)
        yield StreamEvent.status(
            f"Tree-of-Thought 开始搜索 | 策略: {self.strategy.upper()}, "
            f"深度: {self.max_depth}, 分支: {self.num_branches}"
        )

        yield StreamEvent.thought(f"问题: {input_text}")
        yield StreamEvent.thought(
            f"策略: {self.strategy.upper()} | 最大深度: {self.max_depth}"
        )

        self.root = ThoughtNode(content="ROOT", depth=0)

        if self.strategy == "bfs":
            solution = yield from self._stream_bfs_search(input_text, **kwargs)
        elif self.strategy == "dfs":
            solution = yield from self._stream_dfs_search(input_text, **kwargs)
        else:
            solution = yield from self._stream_mcts_search(input_text, **kwargs)

        final_answer = solution or "抱歉，无法在给定推理深度内解决此问题。"
        yield StreamEvent.text(final_answer)

        self._save_conversation_messages(input_text, final_answer, conversation_id)
        yield StreamEvent.done(final_answer)

    def _stream_bfs_search(self, question: str, **kwargs) -> Iterator[StreamEvent]:
        """流式BFS搜索"""
        current_level = [self.root]
        final_answer = None

        for depth in range(1, self.max_depth + 1):
            yield StreamEvent.status(f"BFS 深度 {depth}/{self.max_depth}")

            all_candidates: List[ThoughtNode] = []
            for node in current_level:
                history = self._build_history(node)
                candidates = self._generate_thoughts(
                    question, history, self.num_branches, depth, **kwargs
                )
                for cand_content in candidates:
                    child = ThoughtNode(content=cand_content, depth=depth, parent=node)
                    node.add_child(child)
                    all_candidates.append(child)

            if not all_candidates:
                yield StreamEvent.status("无法生成更多思考方向，搜索终止")
                break

            evaluated = self._evaluate_thoughts(question, all_candidates, **kwargs)

            scored_nodes = sorted(
                zip(all_candidates, evaluated), key=lambda x: x[1], reverse=True
            )

            yield StreamEvent.status(
                f"生成了 {len(scored_nodes)} 个分支，保留 top-{self.top_k}"
            )
            for i, (node, score) in enumerate(scored_nodes[: self.top_k]):
                node.score = score
                yield StreamEvent.thought(
                    f"分支 {i + 1}: 评分={score:.1f} | {node.content[:80]}"
                )

            current_level = [node for node, _ in scored_nodes[: self.top_k]]

            for node in current_level:
                solution = self._try_solve(question, node, **kwargs)
                if solution:
                    yield StreamEvent.status("找到可行解")
                    yield StreamEvent.thought(f"解路径: {node.path_str()}")
                    refined = self._refine_if_needed(question, node, solution, **kwargs)
                    final_answer = refined or solution
                    yield StreamEvent.text(final_answer)
                    return final_answer

        if not final_answer:
            aggregated = self._aggregate_solutions(question, self.root, **kwargs)
            if aggregated:
                final_answer = aggregated

        return final_answer

    def _stream_dfs_search(self, question: str, **kwargs) -> Iterator[StreamEvent]:
        """流式DFS搜索"""
        yield StreamEvent.status("DFS 搜索开始")
        stack: List[Tuple[ThoughtNode, int]] = [(self.root, 0)]
        visited_paths: List[str] = []
        best_solution = None
        best_score = -1.0

        while stack:
            node, depth = stack.pop()

            if depth >= self.max_depth:
                solution = self._try_solve(question, node, **kwargs)
                if solution:
                    sol_score = len(solution)
                    if sol_score > best_score:
                        best_score = sol_score
                        best_solution = solution
                        refined = self._refine_if_needed(
                            question, node, solution, **kwargs
                        )
                        if refined:
                            best_solution = refined
                            yield StreamEvent.thought(f"改进解: {node.path_str()}")
                continue

            history = self._build_history(node)
            candidates = self._generate_thoughts(
                question, history, self.num_branches, depth + 1, **kwargs
            )

            if not candidates:
                continue

            for cand_content in candidates:
                child = ThoughtNode(content=cand_content, depth=depth + 1, parent=node)
                node.add_child(child)

            evaluated = self._evaluate_thoughts(question, node.children, **kwargs)

            scored_children = sorted(
                zip(node.children, evaluated), key=lambda x: x[1], reverse=True
            )

            for child, score in scored_children:
                child.score = score

            yield StreamEvent.thought(
                f"深度 {depth + 1}: {len(scored_children)} 分支, "
                f"最佳评分={scored_children[0][1]:.1f}"
            )

            for child, score in scored_children:
                path_str = child.path_str()
                if path_str not in visited_paths:
                    visited_paths.append(path_str)
                    stack.append((child, depth + 1))

        return best_solution

    def _stream_mcts_search(self, question: str, **kwargs) -> Iterator[StreamEvent]:
        """流式MCTS搜索"""
        yield StreamEvent.status(f"MCTS 搜索开始 (最大迭代: {self.max_iterations})")

        for iteration in range(1, self.max_iterations + 1):
            node = self._mcts_select(self.root)
            depth = node.depth

            if depth < self.max_depth and not self._can_conclude(
                node, question, **kwargs
            ):
                child = self._mcts_expand(node, question, depth + 1, **kwargs)
                if child:
                    reward = self._mcts_simulate(child, question, **kwargs)
                    self._mcts_backpropagate(child, reward)
            else:
                self._mcts_backpropagate(node, 0.0)

            if iteration % 10 == 0 or iteration == 1:
                best = self._mcts_best_child(self.root)
                if best:
                    visit_str = f"访问={best.visits}"
                    val_str = (
                        f"价值={best.value / best.visits:.2f}" if best.visits else ""
                    )
                    yield StreamEvent.thought(
                        f"迭代 {iteration:3d}: '{best.content[:50]}' ({visit_str}, {val_str})"
                    )

        best_node = self._mcts_best_child(self.root)
        if best_node:
            yield StreamEvent.thought(f"MCTS 选择的最优路径: {best_node.path_str()}")
            solution = self._try_solve(question, best_node, **kwargs)
            if solution:
                refined = self._refine_if_needed(
                    question, best_node, solution, **kwargs
                )
                final = refined or solution
                yield StreamEvent.text(final)
                return final

        aggregated = self._aggregate_solutions(question, self.root, **kwargs)
        return aggregated

    # ── BFS Strategy ──────────────────────────────────────────────

    def _bfs_search(self, question: str, **kwargs) -> Optional[str]:
        current_level = [self.root]

        for depth in range(1, self.max_depth + 1):
            print(f"\n--- BFS 深度 {depth}/{self.max_depth} ---")

            all_candidates: List[ThoughtNode] = []
            for node in current_level:
                history = self._build_history(node)
                candidates = self._generate_thoughts(
                    question, history, self.num_branches, depth, **kwargs
                )
                for cand_content in candidates:
                    child = ThoughtNode(content=cand_content, depth=depth, parent=node)
                    node.add_child(child)
                    all_candidates.append(child)

            if not all_candidates:
                print("  ⚠️ 无法生成更多思考方向，搜索终止。")
                break

            evaluated = self._evaluate_thoughts(question, all_candidates, **kwargs)

            scored_nodes = sorted(
                zip(all_candidates, evaluated), key=lambda x: x[1], reverse=True
            )

            print(f"  生成了 {len(scored_nodes)} 个分支，保留 top-{self.top_k}")
            for i, (node, score) in enumerate(scored_nodes[: self.top_k]):
                node.score = score
                print(f"  🌿 分支 {i + 1}: 评分={score:.1f} | {node.content[:60]}")

            current_level = [node for node, _ in scored_nodes[: self.top_k]]

            for node in current_level:
                solution = self._try_solve(question, node, **kwargs)
                if solution:
                    refined = self._refine_if_needed(question, node, solution, **kwargs)
                    return refined or solution

        return self._aggregate_solutions(question, self.root, **kwargs)

    # ── DFS Strategy ──────────────────────────────────────────────

    def _dfs_search(self, question: str, **kwargs) -> Optional[str]:
        stack: List[Tuple[ThoughtNode, int]] = [(self.root, 0)]
        visited_paths: List[str] = []
        best_solution = None
        best_score = -1.0

        while stack:
            node, depth = stack.pop()

            if depth >= self.max_depth:
                solution = self._try_solve(question, node, **kwargs)
                if solution:
                    sol_score = len(solution)
                    if sol_score > best_score:
                        best_score = sol_score
                        best_solution = solution
                        refined = self._refine_if_needed(
                            question, node, solution, **kwargs
                        )
                        if refined:
                            best_solution = refined
                continue

            history = self._build_history(node)
            candidates = self._generate_thoughts(
                question, history, self.num_branches, depth + 1, **kwargs
            )

            if not candidates:
                continue

            for cand_content in candidates:
                child = ThoughtNode(content=cand_content, depth=depth + 1, parent=node)
                node.add_child(child)

            evaluated = self._evaluate_thoughts(question, node.children, **kwargs)

            scored_children = sorted(
                zip(node.children, evaluated), key=lambda x: x[1], reverse=True
            )

            for child, score in scored_children:
                child.score = score

            print(
                f"  🔍 深度 {depth + 1}: 分支数={len(scored_children)}, "
                f"最佳评分={scored_children[0][1]:.1f}"
            )

            for child, score in scored_children:
                path_str = child.path_str()
                if path_str not in visited_paths:
                    visited_paths.append(path_str)
                    stack.append((child, depth + 1))

        return best_solution

    # ── MCTS Strategy ─────────────────────────────────────────────

    def _mcts_search(self, question: str, **kwargs) -> Optional[str]:
        print(f"\n--- MCTS 搜索 (最大迭代: {self.max_iterations}) ---")

        for iteration in range(1, self.max_iterations + 1):
            node = self._mcts_select(self.root)
            depth = node.depth

            if depth < self.max_depth and not self._can_conclude(
                node, question, **kwargs
            ):
                child = self._mcts_expand(node, question, depth + 1, **kwargs)
                if child:
                    reward = self._mcts_simulate(child, question, **kwargs)
                    self._mcts_backpropagate(child, reward)
            else:
                self._mcts_backpropagate(node, 0.0)

            if iteration % 10 == 0 or iteration == 1:
                best = self._mcts_best_child(self.root)
                if best:
                    print(
                        f"  迭代 {iteration:3d}: 最佳分支='{best.content[:40]}...' "
                        f"(访问={best.visits}, 价值={best.value / best.visits if best.visits else 0:.2f})"
                    )

        best_node = self._mcts_best_child(self.root)
        if best_node:
            print(f"\n  MCTS 选择的最优路径: {best_node.path_str()}")
            solution = self._try_solve(question, best_node, **kwargs)
            if solution:
                refined = self._refine_if_needed(
                    question, best_node, solution, **kwargs
                )
                return refined or solution

        return self._aggregate_solutions(question, self.root, **kwargs)

    def _mcts_select(self, node: ThoughtNode) -> ThoughtNode:
        while node.children and node.depth < self.max_depth:
            if any(child.visits == 0 for child in node.children):
                return next(child for child in node.children if child.visits == 0)
            node = node.best_child()
        return node

    def _mcts_expand(
        self, node: ThoughtNode, question: str, depth: int, **kwargs
    ) -> Optional[ThoughtNode]:
        history = self._build_history(node)
        candidates = self._generate_thoughts(
            question, history, self.num_branches, depth, **kwargs
        )
        if not candidates:
            return None

        evaluated = [5.0] * len(candidates)
        try:
            dummy_nodes = [ThoughtNode(c, depth=depth) for c in candidates]
            evaluated = self._evaluate_thoughts(question, dummy_nodes, **kwargs)
        except Exception:
            pass

        for content, score in zip(candidates, evaluated):
            child = ThoughtNode(content=content, depth=depth, score=score, parent=node)
            node.add_child(child)

        scored = sorted(
            zip(node.children[-len(candidates) :], evaluated),
            key=lambda x: x[1],
            reverse=True,
        )
        return scored[0][0] if scored else node.children[-1]

    def _mcts_simulate(self, node: ThoughtNode, question: str, **kwargs) -> float:
        current = node
        depth = current.depth
        reward = current.score / 10.0

        sim_depth = 0
        while depth < self.max_depth and sim_depth < 2:
            history = self._build_history(current)
            candidates = self._generate_thoughts(
                question, history, 2, depth + 1, **kwargs
            )
            if not candidates:
                break
            chosen = random.choice(candidates)
            child = ThoughtNode(
                content=chosen, depth=depth + 1, score=5.0, parent=current
            )
            current.add_child(child)
            current = child
            depth += 1
            sim_depth += 1

            if depth >= self.max_depth - 1:
                sol = self._try_solve(question, current, **kwargs)
                if sol:
                    reward = min(1.0, reward + 0.3)
                    current.solution = sol

        return reward

    def _mcts_backpropagate(self, node: ThoughtNode, reward: float):
        while node:
            node.visits += 1
            node.value += reward
            node = node.parent
            reward *= 0.9

    def _mcts_best_child(self, node: ThoughtNode) -> Optional[ThoughtNode]:
        if not node.children:
            return None
        return max(node.children, key=lambda c: c.visits)

    def _can_conclude(self, node: ThoughtNode, question: str, **kwargs) -> bool:
        if node.solution:
            return True
        if node.depth >= 1 and node.score >= 9.0:
            return True
        return False

    # ── Core LLM Operations ───────────────────────────────────────

    def _generate_thoughts(
        self, question: str, history: str, num_branches: int, depth: int, **kwargs
    ) -> List[str]:
        prompt = self._generate_prompt.format(
            question=question,
            history=history if history else "尚无进展，请从初始思考开始。",
            num_branches=num_branches,
        )
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages, **kwargs) or ""

        thoughts = self._parse_thoughts(response)

        if len(thoughts) < num_branches:
            fallback = [
                f"思考路径 {i + 1}: 深入分析问题的第{i + 1}个方面，{question[:40]}"
                for i in range(num_branches - len(thoughts))
            ]
            thoughts.extend(fallback)

        return thoughts[:num_branches]

    def _evaluate_thoughts(
        self, question: str, nodes: List[ThoughtNode], **kwargs
    ) -> List[float]:
        thoughts_text = "\n".join(
            f"Thought {i + 1}: {node.content}" for i, node in enumerate(nodes)
        )
        prompt = self._evaluate_prompt.format(question=question, thoughts=thoughts_text)
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages, **kwargs) or ""

        scores = self._parse_evaluations(response, len(nodes))

        if len(scores) < len(nodes):
            scores.extend([5.0] * (len(nodes) - len(scores)))

        return scores[: len(nodes)]

    def _try_solve(self, question: str, node: ThoughtNode, **kwargs) -> Optional[str]:
        path = node.get_path()
        path_text = " -> ".join(path[1:])

        prompt = (
            f"基于以下推理路径，你能得出最终答案吗？如果可以，请直接给出答案。"
            f"如果还不能，请回答'无法确定'。\n\n"
            f"问题: {question}\n\n推理路径: {path_text}"
        )
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages, **kwargs) or ""

        if "无法确定" not in response and len(response) > 10:
            node.solution = response
            return response

        return None

    def _refine_if_needed(
        self, question: str, node: ThoughtNode, solution: str, **kwargs
    ) -> Optional[str]:
        path = node.get_path()
        path_text = " -> ".join(path[1:])

        prompt = self._refine_prompt.format(
            question=question, path=path_text, solution=solution
        )
        messages = [{"role": "user", "content": prompt}]
        response = self.llm.invoke(messages, **kwargs) or ""

        if "无需改进" in response:
            return solution

        return response if len(response) > len(solution) * 0.5 else solution

    def _aggregate_solutions(
        self, question: str, root: ThoughtNode, **kwargs
    ) -> Optional[str]:
        leaf_solutions = self._collect_leaf_solutions(root)

        if len(leaf_solutions) == 1:
            return leaf_solutions[0]

        if len(leaf_solutions) > 1:
            paths_text = "\n\n".join(
                f"路径 {i + 1}: {path}\n结果: {sol}"
                for i, (path, sol) in enumerate(leaf_solutions)
            )
            prompt = self._solve_prompt.format(question=question, paths=paths_text)
            messages = [{"role": "user", "content": prompt}]
            return self.llm.invoke(messages, **kwargs) or leaf_solutions[0][1]

        return self._fallback_answer(question, **kwargs)

    def _fallback_answer(self, question: str, **kwargs) -> str:
        all_paths = self._collect_all_paths(self.root)
        if all_paths:
            paths_text = "\n".join(
                f"路径 {i + 1}: {path}" for i, path in enumerate(all_paths)
            )
            prompt = self._solve_prompt.format(question=question, paths=paths_text)
        else:
            prompt = f"请回答以下问题：{question}"

        messages = [{"role": "user", "content": prompt}]
        return self.llm.invoke(messages, **kwargs) or ""

    # ── Helpers ───────────────────────────────────────────────────

    def _build_history(self, node: ThoughtNode) -> str:
        path = node.get_path()
        if len(path) <= 1:
            return ""
        return " -> ".join(f"Step {i}: {p}" for i, p in enumerate(path[1:], 1))

    def _collect_leaf_solutions(self, root: ThoughtNode) -> List[str]:
        solutions = []
        stack = [root]
        while stack:
            node = stack.pop()
            if not node.children and node.solution:
                solutions.append(node.solution)
            stack.extend(node.children)
        return solutions

    def _collect_all_paths(self, root: ThoughtNode) -> List[str]:
        paths = []
        stack = [(root, [])]
        while stack:
            node, path = stack.pop()
            current_path = path + [node.content]
            if not node.children:
                paths.append(" -> ".join(current_path[1:]))
            for child in node.children:
                stack.append((child, current_path))
        return paths

    def _parse_thoughts(self, text: str) -> List[str]:
        thoughts = []
        pattern = r"Thought\s*\d+\s*:\s*(.*)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            thoughts.append(match.strip())
        return thoughts

    def _parse_evaluations(self, text: str, expected_count: int) -> List[float]:
        scores = []
        pattern = r"Evaluation\s*\d+\s*:\s*(\d+(?:\.\d+)?)"
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                score = float(match)
                scores.append(max(0.0, min(10.0, score)))
            except ValueError:
                scores.append(5.0)
        return scores

    def add_tool(self, tool):
        if hasattr(tool, "auto_expand") and tool.auto_expand:
            expanded = tool.get_expanded_tools()
            if expanded:
                for t in expanded:
                    self.tool_registry.register_tool(t)
                print(f"✅ 工具 '{tool.name}' 已展开为 {len(expanded)} 个独立工具")
                return
        self.tool_registry.register_tool(tool)
