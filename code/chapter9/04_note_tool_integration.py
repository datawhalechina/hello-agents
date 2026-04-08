"""
NoteTool 与 ContextBuilder 集成示例

展示如何将 NoteTool 与 ContextBuilder 集成，实现：
1. 长期项目追踪
2. 笔记检索与上下文注入
3. 基于历史笔记的连贯建议
"""
from dotenv import load_dotenv
load_dotenv()
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.context import ContextBuilder, ContextConfig, ContextPacket
from hello_agents.tools import MemoryTool, RAGTool, NoteTool
from hello_agents.core.message import Message
from datetime import datetime
from typing import List, Dict


class ProjectAssistant(SimpleAgent):
    """长期项目助手,集成 NoteTool 和 ContextBuilder"""

    def __init__(self, name: str, project_name: str, **kwargs):
        # 配置 LLM
        from hello_agents.core.llm import HelloAgentsLLM
        llm = HelloAgentsLLM()

        super().__init__(name=name, llm=llm, **kwargs)

        self.project_name = project_name

        # 初始化工具
        # self.memory_tool = MemoryTool(user_id=project_name)
        # self.rag_tool = RAGTool(knowledge_base_path=f"./{project_name}_kb")
        self.note_tool = NoteTool(workspace=f"./{project_name}_notes")

        # 初始化上下文构建器
        self.context_builder = ContextBuilder(
            # memory_tool=self.memory_tool,
            # rag_tool=self.rag_tool,
            config=ContextConfig(max_tokens=4000)
        )

        self.conversation_history = []

    def run(self, user_input: str, note_as_action: bool = False) -> str:
        """运行助手,自动集成笔记"""

        # 1. 从 NoteTool 检索相关笔记
        relevant_notes = self._retrieve_relevant_notes(user_input)

        # 2. 将笔记转换为 ContextPacket
        note_packets = self._notes_to_packets(relevant_notes)

        # 3. 构建优化的上下文
        optimized_context = self.context_builder.build(
            user_query=user_input,
            conversation_history=self.conversation_history,
            system_instructions=self._build_system_instructions(),
            additional_packets=note_packets
        )

        # 4. 调用 LLM (以 messages 数组形式传入)
        messages = [
            {"role": "system", "content": optimized_context},
            {"role": "user", "content": user_input}
        ]
        response = self.llm.invoke(messages)

        # 5. 如果需要,将交互记录为笔记
        if note_as_action:
            self._save_as_note(user_input, response)

        # 6. 更新对话历史
        self._update_history(user_input, response)

        return response

    def _retrieve_relevant_notes(self, query: str, limit: int = 3) -> List[Dict]:
        """检索相关笔记"""
        try:
            # 优先检索 blocker 和 action 类型的笔记
            blockers_raw = self.note_tool.run({
                "action": "list",
                "note_type": "blocker",
                "limit": 2
            })

            actions_raw = self.note_tool.run({
                "action": "list",
                "note_type": "action",
                "limit": 2
            })

            # 通用搜索
            search_results_raw = self.note_tool.run({
                "action": "search",
                "query": query,
                "limit": limit
            })

            blockers = self._ensure_list_of_dicts(blockers_raw)
            actions = self._ensure_list_of_dicts(actions_raw)
            search_results = self._ensure_list_of_dicts(search_results_raw)

            # 合并并去重
            all_notes = {}
            for note in blockers+ actions + search_results:
                if not isinstance(note, dict):
                    continue
                note_id = (
                    note.get("note_id")
                    or note.get("id")
                    or note.get("uuid")
                    or note.get("title")
                    or str(hash(str(note)))
                )
                all_notes[note_id] = note
            return list(all_notes.values())[:limit]

        except Exception as e:
            print(f"[WARNING] 笔记检索失败: {e}")
            return []

    def _ensure_list_of_dicts(self, data) -> List[Dict]:
        """将 NoteTool 返回规范化为字典列表"""
        import json
        if data is None:
            return []
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                return []
        if isinstance(data, dict):
            # 兼容 {"items": [...]} 或单条记录
            if "items" in data and isinstance(data["items"], list):
                return [item for item in data["items"] if isinstance(item, dict)]
            return [data]
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    def _notes_to_packets(self, notes: List[Dict]) -> List[ContextPacket]:
        """将笔记转换为上下文包"""
        packets = []

        for note in notes:
            title = note.get("title", "")
            body = note.get("content", "")
            content = f"[笔记:{title}]\n{body}"

            # 安全解析时间戳
            ts = None
            for key in ("updated_at", "updatedAt", "time", "timestamp"):
                if key in note:
                    ts = note.get(key)
                    break
            parsed_ts = None
            if isinstance(ts, (int, float)):
                try:
                    parsed_ts = datetime.fromtimestamp(ts)
                except Exception:
                    parsed_ts = None
            elif isinstance(ts, str):
                try:
                    parsed_ts = datetime.fromisoformat(ts)
                except Exception:
                    parsed_ts = None
            if parsed_ts is None:
                parsed_ts = datetime.now()

            note_type = note.get("type") or note.get("note_type") or "note"
            note_id = (
                note.get("note_id")
                or note.get("id")
                or note.get("uuid")
                or title
                or str(hash(str(note)))
            )

            packets.append(ContextPacket(
                content=content,
                timestamp=parsed_ts,
                token_count=len(content) // 4,  # 简单估算
                relevance_score=0.75,  # 笔记具有较高相关性
                metadata={
                    "type": "note",
                    "note_type": note_type,
                    "note_id": note_id
                }
            ))

        return packets

    def _save_as_note(self, user_input: str, response: str):
        """将交互保存为笔记"""
        try:
            # 判断应该保存为什么类型的笔记
            if "问题" in user_input or "阻塞" in user_input:
                note_type = "blocker"
            elif "计划" in user_input or "下一步" in user_input:
                note_type = "action"
            else:
                note_type = "conclusion"

            self.note_tool.run({
                "action": "create",
                "title": f"{user_input[:30]}...",
                "content": f"## 问题\n{user_input}\n\n## 分析\n{response}",
                "note_type": note_type,
                "tags": [self.project_name, "auto_generated"]
            })

        except Exception as e:
            print(f"[WARNING] 保存笔记失败: {e}")

    def _build_system_instructions(self) -> str:
        """构建系统指令"""
        return f"""你是 {self.project_name} 项目的长期助手。

你的职责:
1. 基于历史笔记提供连贯的建议
2. 追踪项目进展和待解决问题
3. 在回答时引用相关的历史笔记
4. 提供具体、可操作的下一步建议

注意:
- 优先关注标记为 blocker 的问题
- 在建议中说明依据来源(笔记、记忆或知识库)
- 保持对项目整体进度的认识"""

    def _update_history(self, user_input: str, response: str):
        """更新对话历史"""
        self.conversation_history.append(
            Message(content=user_input, role="user", timestamp=datetime.now())
        )
        self.conversation_history.append(
            Message(content=response, role="assistant", timestamp=datetime.now())
        )

        # 限制历史长度
        if len(self.conversation_history) > 10:
            self.conversation_history = self.conversation_history[-10:]


def main():
    print("=" * 80)
    print("NoteTool 与 ContextBuilder 集成示例")
    print("=" * 80 + "\n")

    # 使用示例
    assistant = ProjectAssistant(
        name="项目助手",
        project_name="data_pipeline_refactoring"
    )

    # 第一次交互:记录项目状态
    print("第一次交互:记录项目状态")
    response = assistant.run(
        "我们已经完成了数据模型层的重构,测试覆盖率达到85%。下一步计划重构业务逻辑层。",
        note_as_action=True
    )
    print(f"助手回答: {response}\n")

    # 第二次交互:提出问题
    print("第二次交互:提出问题")
    response = assistant.run(
        "在重构业务逻辑层时,我遇到了依赖版本冲突的问题,该如何解决?"
    )
    print(f"助手回答: {response}\n")

    # 查看笔记摘要
    print("查看笔记摘要:")
    summary = assistant.note_tool.run({"action": "summary"})
    import json
    print(json.dumps(summary, indent=2, ensure_ascii=False).replace("\\n", "\n"))

    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80)


if __name__ == "__main__":
    main()
