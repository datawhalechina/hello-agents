"""Skills tool - load and query installed agent skills.

This integrates "skills" (SOP / playbooks / procedural knowledge) into the agent
as *progressively disclosed* context: the model can list/search skills, then
load the full SKILL.md only when needed.

Expected directory layout (Claude-style):
  .agents/skills/<skill-id>/SKILL.md
Where SKILL.md may contain YAML front matter with fields like:
  ---
  name: find-skills
  description: ...
  ---
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import Tool, ToolParameter
from utils.env import env_stripped


@dataclass(frozen=True)
class SkillMeta:
    skill_id: str
    path: Path
    name: str
    description: str


def _parse_front_matter(md: str) -> tuple[dict[str, str], str]:
    """Parse a very small YAML front matter subset (key: value)."""
    text = md or ""
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}, text
    # find closing ---
    end = None
    for i in range(1, min(len(lines), 80)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}, text
    meta_lines = lines[1:end]
    meta: dict[str, str] = {}
    for line in meta_lines:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            meta[k] = v
    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return meta, body


class SkillsTool(Tool):
    """Manage and load installed skills from standard locations.

    OpenCode / Claude-style common locations (project-level first, then global):
    - .agents/skills/<id>/SKILL.md
    - .opencode/skills/<id>/SKILL.md
    - .claude/skills/<id>/SKILL.md
    - ~/.config/opencode/skills/<id>/SKILL.md
    - ~/.claude/skills/<id>/SKILL.md

    You may override with CODE_AGENT_SKILLS_DIR to point to a single root.
    """

    def __init__(self, repo_root: str, skills_root: Optional[str] = None):
        super().__init__(
            name="skills",
            description=(
                "Skills 工具：列出/搜索/加载已安装的技能（SOP/工作流）。"
                "用于渐进式披露：先 list/search，再 show 具体 SKILL.md。"
            ),
        )
        self.repo_root = Path(repo_root).expanduser().resolve()
        env_skills_dir = env_stripped("CODE_AGENT_SKILLS_DIR", "")
        override = (skills_root or "").strip() or (Path(env_skills_dir).as_posix() if env_skills_dir else "")
        self.skills_roots: list[Path] = []
        if override:
            self.skills_roots = [Path(override).expanduser().resolve()]
        else:
            home = Path.home()
            self.skills_roots = [
                (self.repo_root / ".agents" / "skills").resolve(),
                (self.repo_root / ".opencode" / "skills").resolve(),
                (self.repo_root / ".claude" / "skills").resolve(),
                (home / ".config" / "opencode" / "skills").resolve(),
                (home / ".claude" / "skills").resolve(),
            ]

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="action",
                type="string",
                description="list | search | show",
                required=True,
            ),
            ToolParameter(
                name="id",
                type="string",
                description="技能 id（show 时必填），即 `.agents/skills/<id>/` 目录名",
                required=False,
            ),
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词（search 时必填）",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="integer",
                description="返回数量（list/search，默认 20）",
                required=False,
                default=20,
            ),
            ToolParameter(
                name="roots",
                type="boolean",
                description="list 时是否同时输出扫描 roots（默认 false）",
                required=False,
                default=False,
            ),
        ]

    def run(self, parameters: Dict[str, Any]) -> str:
        action = (parameters.get("action") or "").strip().lower()
        if action == "list":
            limit = int(parameters.get("limit") or 20)
            show_roots = bool(parameters.get("roots") or False)
            return self._list(limit=limit, show_roots=show_roots)
        if action == "search":
            query = (parameters.get("query") or "").strip()
            if not query:
                return "错误：search 需要 query"
            limit = int(parameters.get("limit") or 20)
            return self._search(query=query, limit=limit)
        if action == "show":
            sid = (parameters.get("id") or "").strip()
            if not sid:
                return "错误：show 需要 id"
            return self._show(skill_id=sid)
        return "错误：action 必须是 list | search | show"

    def _iter_skill_files(self) -> list[Path]:
        seen: set[str] = set()
        paths: list[Path] = []
        for root in self.skills_roots:
            if not root.exists() or not root.is_dir():
                continue
            try:
                for d in sorted(root.iterdir(), key=lambda p: p.name.lower()):
                    if not d.is_dir():
                        continue
                    sid = d.name
                    if sid in seen:
                        continue
                    p = d / "SKILL.md"
                    if p.exists() and p.is_file():
                        seen.add(sid)
                        paths.append(p)
            except Exception:
                continue
        return paths

    def _load_meta(self, skill_file: Path) -> SkillMeta:
        raw = skill_file.read_text(encoding="utf-8", errors="ignore")
        meta, _body = _parse_front_matter(raw)
        sid = skill_file.parent.name
        name = meta.get("name") or sid
        desc = meta.get("description") or ""
        return SkillMeta(skill_id=sid, path=skill_file, name=name, description=desc)

    def _list(self, limit: int = 20, show_roots: bool = False) -> str:
        files = self._iter_skill_files()
        if not files:
            return "未找到 skills（检查目录：\n- " + "\n- ".join([p.as_posix() for p in self.skills_roots]) + "\n）"
        metas = [self._load_meta(p) for p in files][: max(1, limit)]
        lines = [f"找到 {len(metas)} 个 skills："]
        if show_roots:
            lines.append("roots:")
            for r in self.skills_roots:
                lines.append(f"- {r.as_posix()}")
        for m in metas:
            lines.append(f"- {m.skill_id}  ({m.name})")
            if m.description:
                lines.append(f"  {m.description}")
        return "\n".join(lines)

    def _search(self, query: str, limit: int = 20) -> str:
        q = query.lower()
        files = self._iter_skill_files()
        if not files:
            return "未找到 skills（检查目录：\n- " + "\n- ".join([p.as_posix() for p in self.skills_roots]) + "\n）"
        hits: list[SkillMeta] = []
        for p in files:
            m = self._load_meta(p)
            if q in m.skill_id.lower() or q in m.name.lower() or q in (m.description or "").lower():
                hits.append(m)
                continue
            # fallback: light content scan (first 2000 chars)
            try:
                raw = p.read_text(encoding="utf-8", errors="ignore")[:2000].lower()
                if q in raw:
                    hits.append(m)
            except Exception:
                pass
            if len(hits) >= limit:
                break
        if not hits:
            return f"未找到匹配 '{query}' 的 skills。"
        lines = [f"匹配 '{query}' 的 skills（{len(hits)} 个）："]
        for m in hits:
            lines.append(f"- {m.skill_id}  ({m.name})")
            if m.description:
                lines.append(f"  {m.description}")
        return "\n".join(lines)

    def _show(self, skill_id: str) -> str:
        # find in roots (project-first)
        p: Optional[Path] = None
        for root in self.skills_roots:
            candidate = (root / skill_id / "SKILL.md").expanduser().resolve()
            if candidate.exists():
                p = candidate
                break
        if p is None:
            return f"未找到 skill: {skill_id}"

        raw = p.read_text(encoding="utf-8", errors="ignore")
        meta, body = _parse_front_matter(raw)
        header = f"[skill] {skill_id}"
        if meta.get("name"):
            header += f" ({meta['name']})"
        out = [header]
        if meta.get("description"):
            out.append(meta["description"])
        out.append("")
        out.append(body.strip())
        return "\n".join(out).strip()

