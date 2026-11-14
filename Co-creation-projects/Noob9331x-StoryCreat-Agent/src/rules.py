"""规则层审稿（FR-04）。

只使用确定性规则，不调用 LLM，可离线单测。每条问题与 LLM 审稿共用
:class:`~src.models.ReviewIssue` 结构，便于合并与展示。
"""

from __future__ import annotations

import difflib
import re

from .models import Genre, ReviewIssue, Severity, StoryRequest, sort_issues

META_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"作为(?:一个)?(?:AI|人工智能|语言模型|大模型)"),
    re.compile(r"我(?:无法|不能)(?:完成|满足|提供|创作|继续)"),
    re.compile(r"^\s*(?:好的|当然|没问题)[，,。!！].{0,30}(?:以下|下面|这是)", re.MULTILINE),
    re.compile(r"^\s*以下是.{0,40}(?:正文|内容|作品|故事)", re.MULTILINE),
    re.compile(r"^\s*(?:希望|祝)(?:你|您)(?:喜欢|满意)", re.MULTILINE),
    re.compile(r"^\s*(?:正文|作品|故事)[:：]\s*$", re.MULTILINE),
]

_SCENE_PATTERN = re.compile(
    r"^\s*(?:场景\s*[一二三四五六七八九十\d]+|第\s*[一二三四五六七八九十\d]+\s*场|"
    r"INT\.|EXT\.|内景|外景)",
    re.MULTILINE,
)
_DIALOGUE_PATTERN = re.compile(r"^\s*[^\s：:（(]{1,15}\s*[：:]\s*\S+", re.MULTILINE)
_MARKDOWN_HEADING = re.compile(r"^\s*#{1,6}\s+\S", re.MULTILINE)
_LIST_LINE = re.compile(r"^\s*(?:\d+[.、)]|[-*])\s+\S", re.MULTILINE)
_CODE_FENCE = re.compile(r"```")


def count_chars(text: str) -> int:
    """统计正文有效字符数（不含空白）。

    Args:
        text: 待统计文本。

    Returns:
        去除所有空白字符后的长度。
    """
    return len(re.sub(r"\s+", "", text or ""))


def _quote(text: str, start: int = 0, end: int | None = None) -> str:
    """截取原文片段作为问题引用，最长 80 字。"""
    snippet = (text or "")[start:end].strip()
    if not snippet:
        snippet = (text or "").strip()[:80]
    return snippet[:80]


def detect_meta_phrases(text: str) -> list[str]:
    """检测拒答语与元话语。

    Args:
        text: 待检测文本。

    Returns:
        命中的原文片段列表（每个模式最多一条）。
    """
    hits: list[str] = []
    for pattern in META_PATTERNS:
        match = pattern.search(text or "")
        if match:
            hits.append(match.group(0).strip())
    return hits


def looks_like_refusal(text: str) -> bool:
    """判断文本是否为空或只包含拒答/元话语。

    用于写作 Agent 生成后的自检：清洗后为空即视为失败并重试。
    """
    cleaned = (text or "").strip()
    if not cleaned:
        return True
    if count_chars(cleaned) < 10:
        return True
    return bool(detect_meta_phrases(cleaned[:200]))


def _length_issues(request: StoryRequest, text: str) -> list[ReviewIssue]:
    """检查最小长度与长度偏差。"""
    actual = count_chars(text)
    minimum = request.target_length * 0.6
    expected = request.target_length * 0.85
    if actual < minimum:
        return [
            ReviewIssue(
                severity=Severity.FATAL,
                category="length",
                quote=_quote(text, 0, 60),
                problem=(
                    f"正文仅 {actual} 字，低于目标长度 {request.target_length} 字的"
                    f" 60%（{int(minimum)} 字）。"
                ),
                suggestion="补写场景、人物行动或心理描写，使篇幅达到目标长度的 85% 以上。",
            )
        ]
    if actual < expected:
        return [
            ReviewIssue(
                severity=Severity.MAJOR,
                category="length",
                quote=_quote(text, 0, 60),
                problem=(
                    f"正文 {actual} 字，略低于目标长度 {request.target_length} 字的"
                    f" 85%（{int(expected)} 字）。"
                ),
                suggestion="适当扩写关键场景或结尾，使篇幅更接近目标长度。",
            )
        ]
    return []


def _keyword_issues(request: StoryRequest, text: str) -> list[ReviewIssue]:
    """检查必须元素与禁止元素。"""
    issues: list[ReviewIssue] = []
    for item in request.must_include:
        if item not in (text or ""):
            issues.append(
                ReviewIssue(
                    severity=Severity.FATAL,
                    category="keyword",
                    quote=item,
                    problem=f"缺少用户要求的必须元素「{item}」。",
                    suggestion=f"在正文中自然融入「{item}」，并确保其不是一笔带过。",
                )
            )
    for item in request.forbidden:
        if item and item in (text or ""):
            issues.append(
                ReviewIssue(
                    severity=Severity.FATAL,
                    category="keyword",
                    quote=item,
                    problem=f"出现了用户明确禁止的元素「{item}」。",
                    suggestion=f"删除所有与「{item}」相关的内容，并用符合设定的元素替代。",
                )
            )
    return issues


def _structure_issues(request: StoryRequest, text: str) -> list[ReviewIssue]:
    """检查体裁结构：剧本场次/对白、诗歌行数。"""
    issues: list[ReviewIssue] = []
    content = text or ""
    if request.genre is Genre.SCRIPT:
        scenes = _SCENE_PATTERN.findall(content)
        if len(scenes) < 3:
            issues.append(
                ReviewIssue(
                    severity=Severity.MAJOR,
                    category="structure",
                    quote=_quote(content, 0, 60),
                    problem=f"剧本仅有 {len(scenes)} 个可识别的场次标记，至少需要 3 个。",
                    suggestion="补充场次标题，例如「场景一：深夜便利店」「场景二：雨中的公交站」。",
                )
            )
        dialogues = _DIALOGUE_PATTERN.findall(content)
        if not dialogues:
            issues.append(
                ReviewIssue(
                    severity=Severity.MAJOR,
                    category="structure",
                    quote=_quote(content, 0, 60),
                    problem="剧本中未识别到「人物名：台词」形式的对白。",
                    suggestion="以人物对白推动情节，格式为「人物名：台词」。",
                )
            )
    elif request.genre is Genre.POEM:
        lines = [line for line in content.splitlines() if line.strip()]
        if len(lines) < 8:
            issues.append(
                ReviewIssue(
                    severity=Severity.MAJOR,
                    category="structure",
                    quote=_quote(content, 0, 60),
                    problem=f"诗歌仅 {len(lines)} 行，少于要求的 8 行。",
                    suggestion="增加意象与分行，使诗歌至少达到 8 行且节奏完整。",
                )
            )
    return issues



def _repetition_issues(text: str) -> list[ReviewIssue]:
    """检查相邻段落高度相似或整段重复。"""
    paragraphs = [
        item.strip()
        for item in re.split(r"\n\s*\n", text or "")
        if len(item.strip()) >= 20
    ]
    if len(paragraphs) < 2:
        return []

    duplicate_pairs = 0
    for index in range(len(paragraphs) - 1):
        left = re.sub(r"\s+", "", paragraphs[index])
        right = re.sub(r"\s+", "", paragraphs[index + 1])
        if not left or not right:
            continue
        if left == right:
            duplicate_pairs += 1
            continue
        ratio = difflib.SequenceMatcher(None, left, right).ratio()
        if ratio > 0.9:
            duplicate_pairs += 1

    if duplicate_pairs >= 2:
        return [
            ReviewIssue(
                severity=Severity.MAJOR,
                category="repetition",
                quote=_quote(paragraphs[1], 0, 60),
                problem=f"检测到 {duplicate_pairs} 处相邻段落高度相似或重复，存在复读风险。",
                suggestion="删除重复段落，用新的情节推进或细节描写替换。",
            )
        ]
    return []


def _format_issues(request: StoryRequest, text: str) -> list[ReviewIssue]:
    """检查 Markdown 围栏、标题符号与列表化写法。"""
    issues: list[ReviewIssue] = []
    content = text or ""
    fence = _CODE_FENCE.search(content)
    if fence:
        issues.append(
            ReviewIssue(
                severity=Severity.MINOR,
                category="format",
                quote="```",
                problem="正文残留 Markdown 代码围栏。",
                suggestion="删除所有 ``` 标记，只保留纯正文。",
            )
        )
    if request.genre in (Genre.NOVEL, Genre.POEM):
        heading = _MARKDOWN_HEADING.search(content)
        if heading:
            issues.append(
                ReviewIssue(
                    severity=Severity.MINOR,
                    category="format",
                    quote=heading.group(0).strip(),
                    problem="小说/诗歌正文中出现 Markdown 标题符号，破坏正文排版。",
                    suggestion="去掉 # 标题符号，改为自然段落或单行标题。",
                )
            )
        list_lines = _LIST_LINE.findall(content)
        if len(list_lines) >= 3:
            issues.append(
                ReviewIssue(
                    severity=Severity.MINOR,
                    category="format",
                    quote="；".join(line.strip() for line in list_lines[:3]),
                    problem="正文呈现为编号/项目符号列表，不符合叙事体裁。",
                    suggestion="改写为连贯的叙述段落，避免分点罗列。",
                )
            )
    return issues


def run_rule_review(request: StoryRequest, text: str) -> list[ReviewIssue]:
    """执行全部规则层检查。

    Args:
        request: 创作请求（提供长度、关键词、体裁等约束）。
        text: 待审稿件全文。

    Returns:
        按 fatal → major → minor 排序的问题列表；完全合规时返回空列表。
    """
    issues: list[ReviewIssue] = []
    issues.extend(_length_issues(request, text))
    issues.extend(_keyword_issues(request, text))

    for hit in detect_meta_phrases(text):
        issues.append(
            ReviewIssue(
                severity=Severity.MAJOR,
                category="meta",
                quote=hit,
                problem="正文中出现拒答语或创作元话语，不符合“只输出正文”的要求。",
                suggestion="删除该句，直接从故事正文开始。",
            )
        )

    issues.extend(_structure_issues(request, text))
    issues.extend(_repetition_issues(text))
    issues.extend(_format_issues(request, text))
    return sort_issues(issues)

