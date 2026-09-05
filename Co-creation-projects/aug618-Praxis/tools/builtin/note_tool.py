"""NoteTool - 结构化笔记工具

为Agent提供结构化笔记能力，支持：
- 创建/读取/更新/删除笔记
- 按类型组织（任务状态、结论、阻塞项、行动计划等）
- 持久化存储（Markdown格式，带YAML前置元数据）
- 搜索与过滤
- 与MemoryTool集成（可选）

使用场景：
- 长时程任务的状态跟踪
- 关键结论与依赖记录
- 待办事项与行动计划
- 项目知识沉淀

笔记格式示例：
```markdown
---
id: note_20250118_120000_0
title: 项目进展
type: task_state
tags: [milestone, phase1]
created_at: 2025-01-18T12:00:00
updated_at: 2025-01-18T12:00:00
---

# 项目进展

已完成需求分析，下一步：设计方案

## 关键里程碑
- [x] 需求收集
- [ ] 方案设计
```
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json
import os
import re

from ..base import Tool, ToolParameter


class NoteTool(Tool):
    """笔记工具
    
    为Agent提供结构化笔记管理能力，支持多种笔记类型：
    - task_state: 任务状态
    - conclusion: 关键结论
    - blocker: 阻塞项
    - action: 行动计划
    - reference: 参考资料
    - general: 通用笔记
    
    用法示例：
    ```python
    note_tool = NoteTool(workspace="./project_notes")
    
    # 创建笔记
    note_tool.run({
        "action": "create",
        "title": "项目进展",
        "content": "已完成需求分析，下一步：设计方案",
        "note_type": "task_state",
        "tags": ["milestone", "phase1"]
    })
    
    # 读取笔记
    notes = note_tool.run({"action": "list", "note_type": "task_state"})
    ```
    """
    
    def __init__(
        self,
        workspace: str = "./notes",
        auto_backup: bool = True,
        max_notes: int = 1000
    ):
        super().__init__(
            name="note",
            description="笔记工具 - 创建、读取、更新、删除结构化笔记，支持任务状态、结论、阻塞项等类型"
        )
        
        self.workspace = Path(workspace)
        self.auto_backup = auto_backup
        self.max_notes = max_notes
        
        # 确保工作目录存在
        self.workspace.mkdir(parents=True, exist_ok=True)
        
        # 笔记索引文件
        self.index_file = self.workspace / "notes_index.json"
        self._load_index()
    
    def _load_index(self):
        """加载笔记索引"""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                self.notes_index = json.load(f)
        else:
            self.notes_index = {
                "notes": [],
                "metadata": {
                    "created_at": datetime.now().isoformat(),
                    "total_notes": 0
                }
            }
            self._save_index()
    
    def _save_index(self):
        """保存笔记索引"""
        with open(self.index_file, 'w', encoding='utf-8') as f:
            json.dump(self.notes_index, f, ensure_ascii=False, indent=2)
    
    def _generate_note_id(self) -> str:
        """生成笔记ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        count = len(self.notes_index["notes"])
        return f"note_{timestamp}_{count}"
    
    def _get_note_path(self, note_id: str) -> Path:
        """获取笔记文件路径"""
        return self.workspace / f"{note_id}.md"
    
    def _note_to_markdown(self, note: Dict[str, Any]) -> str:
        """将笔记对象转换为Markdown格式"""
        # YAML前置元数据
        frontmatter = "---\n"
        frontmatter += f"id: {note['id']}\n"
        frontmatter += f"title: {note['title']}\n"
        frontmatter += f"type: {note['type']}\n"
        if note.get('tags'):
            tags_str = json.dumps(note['tags'])
            frontmatter += f"tags: {tags_str}\n"
        frontmatter += f"created_at: {note['created_at']}\n"
        frontmatter += f"updated_at: {note['updated_at']}\n"
        frontmatter += "---\n\n"
        
        # Markdown内容
        content = f"# {note['title']}\n\n"
        content += note['content']
        
        return frontmatter + content
    
    def _markdown_to_note(self, markdown_text: str) -> Dict[str, Any]:
        """将Markdown文本解析为笔记对象"""
        # 提取YAML前置元数据
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', markdown_text, re.DOTALL)
        
        if not frontmatter_match:
            raise ValueError("无效的笔记格式：缺少YAML前置元数据")
        
        frontmatter_text = frontmatter_match.group(1)
        content_start = frontmatter_match.end()
        
        # 解析YAML（简化版）
        note = {}
        for line in frontmatter_text.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 处理特殊字段
                if key == 'tags':
                    try:
                        note[key] = json.loads(value)
                    except:
                        note[key] = []
                else:
                    note[key] = value
        
        # 提取内容（去掉标题行）
        markdown_content = markdown_text[content_start:].strip()
        # 移除第一行的 # 标题
        lines = markdown_content.split('\n')
        if lines and lines[0].startswith('# '):
            markdown_content = '\n'.join(lines[1:]).strip()
        
        note['content'] = markdown_content
        
        # 添加元数据
        note['metadata'] = {
            'word_count': len(markdown_content),
            'status': 'active'
        }
        
        return note
    
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行工具"""
        if not self.validate_parameters(parameters):
            return "❌ 参数验证失败"
        
        action = parameters.get("action")
        
        if action == "create":
            return self._create_note(parameters)
        elif action == "read":
            return self._read_note(parameters)
        elif action == "update":
            return self._update_note(parameters)
        elif action == "delete":
            return self._delete_note(parameters)
        elif action == "list":
            return self._list_notes(parameters)
        elif action == "search":
            return self._search_notes(parameters)
        elif action == "summary":
            return self._get_summary()
        else:
            return f"❌ 不支持的操作: {action}"
    
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="action",
                type="string",
                description=(
                    "操作类型: create(创建), read(读取), update(更新), "
                    "delete(删除), list(列表), search(搜索), summary(摘要)"
                ),
                required=True
            ),
            ToolParameter(
                name="title",
                type="string",
                description="笔记标题（create/update时必需）",
                required=False
            ),
            ToolParameter(
                name="content",
                type="string",
                description="笔记内容（create/update时必需）",
                required=False
            ),
            ToolParameter(
                name="note_type",
                type="string",
                description=(
                    "笔记类型: task_state(任务状态), conclusion(结论), "
                    "blocker(阻塞项), action(行动计划), reference(参考), general(通用)"
                ),
                required=False,
                default="general"
            ),
            ToolParameter(
                name="tags",
                type="array",
                description="标签列表（可选）",
                required=False
            ),
            ToolParameter(
                name="note_id",
                type="string",
                description="笔记ID（read/update/delete时必需）",
                required=False
            ),
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词（search时必需）",
                required=False
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回结果数量限制（默认10）",
                required=False,
                default=10
            ),
        ]
    
    def _create_note(self, params: Dict[str, Any]) -> str:
        """创建笔记"""
        title = params.get("title")
        content = params.get("content")
        note_type = params.get("note_type", "general")
        tags = params.get("tags", [])
        
        if not title or not content:
            return "❌ 创建笔记需要提供 title 和 content"
        
        # 检查笔记数量限制
        if len(self.notes_index["notes"]) >= self.max_notes:
            return f"❌ 笔记数量已达上限 ({self.max_notes})"
        
        # 生成笔记ID
        note_id = self._generate_note_id()
        
        # 创建笔记对象
        note = {
            "id": note_id,
            "title": title,
            "content": content,
            "type": note_type,
            "tags": tags if isinstance(tags, list) else [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": {
                "word_count": len(content),
                "status": "active"
            }
        }
        
        # 保存笔记文件（Markdown格式）
        note_path = self._get_note_path(note_id)
        markdown_content = self._note_to_markdown(note)
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # 更新索引
        self.notes_index["notes"].append({
            "id": note_id,
            "title": title,
            "type": note_type,
            "tags": tags if isinstance(tags, list) else [],
            "created_at": note["created_at"]
        })
        self.notes_index["metadata"]["total_notes"] = len(self.notes_index["notes"])
        self._save_index()
        
        return f"✅ 笔记创建成功\nID: {note_id}\n标题: {title}\n类型: {note_type}"
    
    def _read_note(self, params: Dict[str, Any]) -> str:
        """读取笔记"""
        note_id = params.get("note_id")
        
        if not note_id:
            return "❌ 读取笔记需要提供 note_id"
        
        note_path = self._get_note_path(note_id)
        if not note_path.exists():
            return f"❌ 笔记不存在: {note_id}"
        
        with open(note_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
        
        note = self._markdown_to_note(markdown_text)
        
        return self._format_note(note)
    
    def _update_note(self, params: Dict[str, Any]) -> str:
        """更新笔记"""
        note_id = params.get("note_id")
        
        if not note_id:
            return "❌ 更新笔记需要提供 note_id"
        
        note_path = self._get_note_path(note_id)
        if not note_path.exists():
            return f"❌ 笔记不存在: {note_id}"
        
        # 读取现有笔记
        with open(note_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()
        note = self._markdown_to_note(markdown_text)
        
        # 更新字段
        if "title" in params:
            note["title"] = params["title"]
        if "content" in params:
            note["content"] = params["content"]
            note["metadata"]["word_count"] = len(params["content"])
        if "note_type" in params:
            note["type"] = params["note_type"]
        if "tags" in params:
            note["tags"] = params["tags"] if isinstance(params["tags"], list) else []
        
        note["updated_at"] = datetime.now().isoformat()
        
        # 保存更新（Markdown格式）
        markdown_content = self._note_to_markdown(note)
        with open(note_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # 更新索引
        for idx_note in self.notes_index["notes"]:
            if idx_note["id"] == note_id:
                idx_note["title"] = note["title"]
                idx_note["type"] = note["type"]
                idx_note["tags"] = note["tags"]
                break
        self._save_index()
        
        return f"✅ 笔记更新成功: {note_id}"
    
    def _delete_note(self, params: Dict[str, Any]) -> str:
        """删除笔记"""
        note_id = params.get("note_id")
        
        if not note_id:
            return "❌ 删除笔记需要提供 note_id"
        
        note_path = self._get_note_path(note_id)
        if not note_path.exists():
            return f"❌ 笔记不存在: {note_id}"
        
        # 删除文件
        note_path.unlink()
        
        # 更新索引
        self.notes_index["notes"] = [
            n for n in self.notes_index["notes"] if n["id"] != note_id
        ]
        self.notes_index["metadata"]["total_notes"] = len(self.notes_index["notes"])
        self._save_index()
        
        return f"✅ 笔记已删除: {note_id}"
    
    def _list_notes(self, params: Dict[str, Any]) -> str:
        """列出笔记"""
        note_type = params.get("note_type")
        limit = params.get("limit", 10)
        
        # 过滤笔记
        filtered_notes = self.notes_index["notes"]
        if note_type:
            filtered_notes = [n for n in filtered_notes if n["type"] == note_type]
        
        # 限制数量
        filtered_notes = filtered_notes[:limit]
        
        if not filtered_notes:
            return "📝 暂无笔记"
        
        result = f"📝 笔记列表（共 {len(filtered_notes)} 条）\n\n"
        for note in filtered_notes:
            result += f"• [{note['type']}] {note['title']}\n"
            result += f"  ID: {note['id']}\n"
            if note.get('tags'):
                result += f"  标签: {', '.join(note['tags'])}\n"
            result += f"  创建时间: {note['created_at']}\n\n"
        
        return result
    
    def _search_notes(self, params: Dict[str, Any]) -> str:
        """搜索笔记"""
        query = params.get("query", "").lower()
        limit = params.get("limit", 10)
        
        if not query:
            return "❌ 搜索需要提供 query"
        
        # 搜索匹配的笔记
        matched_notes = []
        for idx_note in self.notes_index["notes"]:
            note_path = self._get_note_path(idx_note["id"])
            if note_path.exists():
                with open(note_path, 'r', encoding='utf-8') as f:
                    markdown_text = f.read()
                
                try:
                    note = self._markdown_to_note(markdown_text)
                except Exception as e:
                    print(f"⚠️ 解析笔记失败 {idx_note['id']}: {e}")
                    continue
                
                # 检查标题、内容、标签是否匹配
                if (query in note["title"].lower() or
                    query in note["content"].lower() or
                    any(query in tag.lower() for tag in note.get("tags", []))):
                    matched_notes.append(note)
        
        # 限制数量
        matched_notes = matched_notes[:limit]
        
        if not matched_notes:
            return f"📝 未找到匹配 '{query}' 的笔记"
        
        result = f"🔍 搜索结果（共 {len(matched_notes)} 条）\n\n"
        for note in matched_notes:
            result += self._format_note(note, compact=True) + "\n"
        
        return result
    
    def _get_summary(self) -> str:
        """获取笔记摘要"""
        total = len(self.notes_index["notes"])
        
        # 按类型统计
        type_counts = {}
        for note in self.notes_index["notes"]:
            note_type = note["type"]
            type_counts[note_type] = type_counts.get(note_type, 0) + 1
        
        result = f"📊 笔记摘要\n\n"
        result += f"总笔记数: {total}\n\n"
        result += "按类型统计:\n"
        for note_type, count in sorted(type_counts.items()):
            result += f"  • {note_type}: {count}\n"
        
        return result
    
    def _format_note(self, note: Dict[str, Any], compact: bool = False) -> str:
        """格式化笔记输出"""
        if compact:
            return (
                f"[{note['type']}] {note['title']}\n"
                f"ID: {note['id']}\n"
                f"内容: {note['content'][:100]}{'...' if len(note['content']) > 100 else ''}"
            )
        else:
            result = f"📝 笔记详情\n\n"
            result += f"ID: {note['id']}\n"
            result += f"标题: {note['title']}\n"
            result += f"类型: {note['type']}\n"
            if note.get('tags'):
                result += f"标签: {', '.join(note['tags'])}\n"
            result += f"创建时间: {note['created_at']}\n"
            result += f"更新时间: {note['updated_at']}\n"
            result += f"\n内容:\n{note['content']}\n"
            return result

