from dotenv import load_dotenv
load_dotenv()
import re
import os
import json
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import NoteTool
from prompt import CHAPTER_PROMPT, CHAPTER_REVIEW_PROMPT, CHAPTER_START_PROMPT


def extract_note_id(output: str) -> str:
    """从 NoteTool 的输出文本中提取 note_id"""
    match = re.search(r"ID:\s*(note_[0-9_]+)", output)
    if not match:
        raise ValueError(f"无法从输出解析 note_id:\n{output}")
    return match.group(1)


class MemoryItem(BaseModel):
    """记忆项数据结构"""
    node_id: str
    novel_id: str
    title: str
    content: str
    summary: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}
    next_chapter_prediction: str = ""


class ChapterGenerateAgent:
    """具有上下文感知能力的 Agent"""

    def __init__(self, name: str, llm: HelloAgentsLLM = HelloAgentsLLM(), max_steps: int = 5, chapter_length: int = 3000, **kwargs):

        self.chapter_length = chapter_length
        self.max_steps = max_steps

        self.num_chapter_memories = kwargs.get("num_chapter_memories", 5)
        self.workspace = kwargs.get("workspace", "./outputs")
        self.note_tools: Dict[str, NoteTool] = {}
        
        self.generate_agent = SimpleAgent(name="章节生成助手", llm=llm, system_prompt='你是一位擅长长篇小说结构与文本细化的专业作者助理。')
        self.review_agent = SimpleAgent(name="章节审核助手", llm=llm, system_prompt='你是一位专业的小说审核助手，负责检查章节是否符合小说的结构和风格。')

        # 内存存储
        self.memories: Dict[str, List[MemoryItem]] = {}

    @staticmethod
    def extract_json_from_response(response: str) -> dict:
        """从模型输出中提取并解析 JSON"""
        # 尝试清理 Markdown 代码块标记
        clean_response = re.sub(r"```json\s*", "", response)
        clean_response = re.sub(r"```\s*$", "", clean_response)
        clean_response = clean_response.strip()
        
        try:
            return json.loads(clean_response)
        except json.JSONDecodeError as e:
            # 如果直接解析失败，尝试在文本中寻找第一个 { 和最后一个 }
            try:
                start = clean_response.find("{")
                end = clean_response.rfind("}")
                if start != -1 and end != -1:
                    json_str = clean_response[start : end + 1]
                    return json.loads(json_str)
            except Exception:
                pass
            raise ValueError(f"无法解析 JSON 响应: {response}") from e

    def _ensure_tool(self, novel_id: str, novel_title: str = None):
        if not self.note_tools.get(novel_id):
            if not novel_title:
                raise ValueError(f"Tool for novel_id {novel_id} not initialized and novel_title not provided.")
            self.note_tools[novel_id] = NoteTool(workspace=os.path.join(self.workspace, f"{novel_title}-{novel_id}", 'chapters'))

    def get_content_from_note(self, content: str) -> str:
        try:
            # 去除 YAML 前置元数据
            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if frontmatter_match:
                content = content[frontmatter_match.end():].strip()
            
            # 去除标题（第一行如果是标题）
            lines = content.split('\n')
            if lines and lines[0].startswith('# '):
                content = '\n'.join(lines[1:]).strip()
            
            return content
        except Exception:
            return content

    def get_memories(self, novel_id: str):
        """获取最近章节记忆"""
        if not hasattr(self.note_tools[novel_id], "notes_index"):
            self.note_tools[novel_id]._load_index()

        notes = self.note_tools[novel_id].notes_index.get("notes", [])

        # 筛选相关章节笔记
        chapter_notes = [
            n for n in notes
            if n.get("note_type") == "chapter" and str(novel_id) in n.get("title", "")
        ]

        # 获取最后 N 章
        recent_notes = chapter_notes[-self.num_chapter_memories:]

        for note in recent_notes:
            note_id = note.get("id")
            file_path = os.path.join(self.workspace, f"{note_id}.md")

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                content = self.get_content_from_note(content)
                self.memories[novel_id].append(MemoryItem(
                    node_id=str(note_id),
                    title=note.get("title", "未知章节").strip(),
                    content=content,
                    novel_id=str(novel_id),
                    summary=note['tags'][0]if note.get("tags") and note['tags'] else '',
                    timestamp=datetime.fromisoformat(note.get("created_at", datetime.now().isoformat()))
                ))

    def run(self, user_input: str, **kwargs) -> str:
        """运行 Agent"""
        # 小说id用来区分小说，命名可能会重复
        novel_id = kwargs.pop("novel_id", None)
        assert novel_id, "请提供小说ID"

        novel_title = kwargs.pop("novel_title", None)
        assert novel_title, "请提供小说标题"

        self._ensure_tool(novel_id, novel_title)

        if not self.memories.get(novel_id):
            self.memories[novel_id] = []
            self.get_memories(novel_id)

        # 1. 构建上下文
        outline = self.get_outline(novel_id)
        prev_chapter = self.get_prev_chapter(novel_id)
        prev_summaries = self.get_prev_summaries(novel_id)
        chapter_length = kwargs.get("chapter_length", self.chapter_length)
        context = self.get_prompt(outline, prev_chapter, prev_summaries, user_input, novel_id, chapter_length=chapter_length)
        
        # 2. 使用上下文调用 LLM
        steps = 0
        while steps < self.max_steps:
            steps += 1

            # 生成章节内容
            response = self.generate_agent.run(context)
            try:
                response_data = self.extract_json_from_response(response)
                # 检查是否包含必要字段
                if 'title' not in response_data or 'content' not in response_data or 'next_chapter_prediction' not in response_data or 'summary' not in response_data:
                    raise ValueError("JSON 响应缺少必要字段 'title' 或 'content' 或 'next_chapter_prediction' 或 'summary'")
            except ValueError as e:
                print(f"步骤 {steps} 生成的 JSON 解析错误：{e}")
                continue
            
            # 审核章节内容
            review_context = CHAPTER_REVIEW_PROMPT.format(
                outline=outline,
                prev_chapter=prev_chapter,
                prev_summaries=prev_summaries,
                chapter_content=response_data.get('content', '')
            )
            review_response = self.review_agent.run(review_context)

            # 检查审核结果
            if "【通过】" in review_response:
                break
            
            context = self.get_prompt(outline, prev_chapter, prev_summaries, user_input, novel_id, response_data, review_response, chapter_length=chapter_length)

        # 3. 保存章节到笔记
        create_output = self.note_tools[novel_id].run({
            "action": "create",
            "title": f"{response_data.get('title', '未知章节')}",
            "content": response_data.get('content', ''),
            "note_type": "chapter",
            "tags": [response_data.get('summary', '')]
        })

        # 获取章节笔记ID，保存记忆，并建立与小说ID的关联
        note_id = extract_note_id(create_output)

        self.memories[novel_id].append(MemoryItem(
            node_id=note_id,
            title=response_data.get('title', '未知章节'),
            content=response_data.get('content', ''),
            novel_id=novel_id,
            summary=response_data.get('summary', ''),
            timestamp=datetime.now().isoformat(),
            next_chapter_prediction=response_data.get('next_chapter_prediction', '')
        ))

        return response_data, note_id

    def get_prompt(self, outline: str, prev_chapter: str, prev_summaries: str, user_input: str, novel_id: str, response_data: dict = None, review_response: str = None, chapter_length: int = None) -> str:
        """获取章节生成提示"""
        if chapter_length is None:
            chapter_length = self.chapter_length
        is_first_chapter = (prev_chapter == '无' and prev_summaries == '无')

        if is_first_chapter:
            prompt_template = CHAPTER_START_PROMPT
            context = prompt_template.format(
                outline=outline,
                chapter_history='无' if response_data is None else response_data.get('content', '无'),
                evaluation=review_response or "无",
                user_input=user_input,
                chapter_length=chapter_length
            )
        else:
            prompt_template = CHAPTER_PROMPT
            context = prompt_template.format(
                outline=outline,
                prev_chapter=prev_chapter,
                prev_summaries=prev_summaries,
                chapter_history='无' if response_data is None else response_data.get('content', '无'),
                evaluation=review_response or "无",
                user_input=user_input or [self.memories[novel_id][-1].next_chapter_prediction if self.memories[novel_id] else "无"][0],
                chapter_length=chapter_length
            )
        return context

    def get_outline(self, novel_id: str) -> str:    
        """获取大纲"""
        dir_path = f"{os.path.dirname(self.note_tools[novel_id].workspace)}/outline"
        paths = os.listdir(dir_path)
        assert len(paths) >= 1, f"目录 {dir_path} 下应该有大纲文件"
        # 简单取第一个文件，实际可能需要更精确的逻辑
        path = f"{dir_path}/{paths[0]}"
        with open(path, "r", encoding='utf-8') as f:
            outline = f.read()
        return self.get_content_from_note(outline)

    def get_prev_chapter(self, novel_id: str):
        """获取前一章内容"""
        if self.memories.get(novel_id):
            last_mem = self.memories[novel_id][-1]
            return f"【{last_mem.metadata.get('title', '未知')}】\n...{last_mem.content[-800:]}"
        return "无"

    def get_prev_summaries(self, novel_id: str):
        if self.memories.get(novel_id):
            return "\n".join([f"【{mem.title}】\n{mem.summary}" for mem in self.memories[novel_id][-self.num_chapter_memories:]])
        return "无"
    
    def del_chapter(self, novel_id:str, note_id: str, novel_title: str = None):
        """删除章节"""
        if novel_title:
            self._ensure_tool(novel_id, novel_title)
        self.note_tools[novel_id].run({
            "action": "delete",
            "note_id": note_id
        })
        # 从记忆中删除该章节
        if self.memories.get(novel_id):
            self.memories[novel_id] = [mem for mem in self.memories[novel_id] if mem.node_id != note_id]

    def update_chapter(self, novel_id:str, note_id: str, novel_title: str = None, **kwargs):
        """更新章节"""
        if novel_title:
            self._ensure_tool(novel_id, novel_title)
        self.note_tools[novel_id].run({
            "action": "update",
            "note_id": note_id,
            **kwargs
        })
        # 更新记忆中的章节内容
        if self.memories.get(novel_id):
            for mem in self.memories[novel_id]:
                if mem.node_id == note_id:
                    mem.title = kwargs.get('title', mem.title)
                    mem.content = kwargs.get('content', mem.content)
                    mem.summary = kwargs.get('summary', mem.summary)
                    mem.next_chapter_prediction = kwargs.get('next_chapter_prediction', mem.next_chapter_prediction)
                    mem.timestamp = datetime.now().isoformat()
                    break

def main():
    print("=" * 80)
    print("Novel ChapterGenerateAgent 示例")
    print("=" * 80 + "\n")

    # llm = HelloAgentsLLM(model="qwen3:0.6b", api_key="ollama", base_url="http://127.0.0.1:11434/v1", provider='ollama')
    llm = HelloAgentsLLM(provider='qwen')
    novel_id = "demo_novel_001"
    novel_title = "记忆之城"

    # 1. 模拟大纲文件存在
    # 因为 ChapterGenerateAgent.get_outline 依赖于文件系统查找大纲
    # 我们手动创建一个假的大纲文件用于测试
    workspace_root = "./outputs"
    # 注意：这里模拟 OutlineAgent 的输出路径结构
    outline_dir = os.path.join(workspace_root, f"{novel_title}-{novel_id}", "outline")
    if not os.path.exists(outline_dir):
        os.makedirs(outline_dir)
    
    # 清理旧文件以确保测试环境干净
    for f in os.listdir(outline_dir):
        try:
            os.remove(os.path.join(outline_dir, f))
        except Exception:
            pass
        
    dummy_outline_content = """---
tags: [outline]
created_at: 2025-01-27T10:00:00
---
# 记忆之城-大纲

## 核心梗概
一位能与城市记忆对话的年轻人，在拆迁浪潮中发现一段被刻意抹去的历史。

## 主要人物
- 李寻：主角，拥有"读取"物体记忆的能力。
- 陈叔：古董店老板，似乎知道李寻身世的秘密。

## 故事走向
1. 觉醒能力，卷入拆迁冲突。
2. 发现神秘物品，引出旧事。
3. ...
"""
    dummy_outline_path = os.path.join(outline_dir, f"{novel_id}-outline.md")
    with open(dummy_outline_path, "w", encoding="utf-8") as f:
        f.write(dummy_outline_content)

    print(f"已创建模拟大纲文件: {dummy_outline_path}")
    
    # 2. 初始化章节生成 Agent
    chapter_agent = ChapterGenerateAgent(
        name="小说章节助手",
        llm=llm,
        workspace=workspace_root,  # 使用与 OutlineAgent 一致的根目录
        chapter_length=1000 # 演示用，设短一点
    )

    # 3. 生成第一章
    print(f"\n正在生成第一章...")
    try:
        # run 方法需要 novel_title 来定位目录
        chapter_data_1, note_id_1 = chapter_agent.run(
            user_input="第一章需要通过一个具体的拆迁冲突场景，引出主角的能力。主角李寻在试图保护一家老店不被强拆时，无意中听到了推土机的'心声'。",
            novel_id=novel_id,
            novel_title=novel_title 
        )
        print(f"第一章生成完成，Note ID: {note_id_1}")
        print(f"标题: {chapter_data_1.get('title')}")
        print(f"摘要: {chapter_data_1.get('summary')}")
        print(f"下一章预测: {chapter_data_1.get('next_chapter_prediction')}")

        # 4. 生成第二章（会自动读取第一章作为上下文）
        print(f"\n正在生成第二章...")
        chapter_data_2, note_id_2 = chapter_agent.run(
            user_input="主角在废墟中发现了一个奇怪的物品，触发了回忆。那个物品似乎在呼唤他。",
            novel_id=novel_id,
            novel_title=novel_title
        )
        print(f"第二章生成完成，Note ID: {note_id_2}")
        print(f"标题: {chapter_data_2.get('title')}")
        print(f"摘要: {chapter_data_2.get('summary')}")
        
    except Exception as e:
        print(f"生成过程中出错: {e}")
        import traceback
        traceback.print_exc()



if __name__ == "__main__":
    main()
