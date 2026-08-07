"""
PDF 转 Markdown 工具

从 PDF 文件中提取文本并转换为结构化的 Markdown 格式。
支持本地文件和 URL，适用于学术论文 PDF 的读取。
"""
import os
import re
from typing import Dict, Any, List

from hello_agents.tools import Tool, ToolParameter, ToolResponse, ToolStatus


class PDFExtractTool(Tool):
    """PDF 转 Markdown 工具

    从 PDF 文件中提取文本内容，自动识别论文结构（标题、章节、段落），
    并转换为格式化的 Markdown 输出。支持本地文件路径和 URL。
    """

    # 常见论文章节标题模式
    SECTION_PATTERNS = [
        r'^(abstract|摘要|Abstract)$',
        r'^(introduction|引言|Introduction)$',
        r'^(related\s*work|相关工作|Related\s*Work)$',
        r'^(background|背景|Background)$',
        r'^(method|方法|Method(ology|s)?)$',
        r'^(experiment|实验|Experiment(s|al\s*setup)?)$',
        r'^(result|结果|Result(s)?(\s*and\s*analysis)?)$',
        r'^(discussion|讨论|Discussion)$',
        r'^(conclusion|结论|Conclusion(\s*and\s*future\s*work)?)$',
        r'^(reference|参考文献|Reference(s)?)$',
        r'^(appendix|附录|Appendix)$',
        r'^(evaluation|评估|Evaluation)$',
        r'^(implementation|实现|Implementation)$',
        r'^(limitation|局限|Limitation(s)?)$',
    ]

    def __init__(self):
        super().__init__(
            name="pdf_extract",
            description="从 PDF 文件中提取文本并转换为 Markdown 格式。"
                        "自动识别论文结构（标题、章节、段落），"
                        "清理 PDF 断行和页码等噪声。"
                        "支持本地 PDF 文件路径或 PDF URL。"
                        "适合将论文 PDF 转为 Markdown 后用于进一步分析。"
        )

    def _extract_raw_text(self, file_path: str, start_page: int = 1,
                           end_page: int = -1) -> str:
        """使用 PyPDF2 提取原始文本"""
        try:
            from PyPDF2 import PdfReader
        except ImportError:
            raise ImportError("请安装 PyPDF2: pip install PyPDF2")

        reader = PdfReader(file_path)
        total_pages = len(reader.pages)

        if end_page == -1 or end_page > total_pages:
            end_page = total_pages

        all_text = []
        for i in range(start_page - 1, min(end_page, total_pages)):
            page = reader.pages[i]
            text = page.extract_text()
            if text:
                all_text.append(text)

        if not all_text:
            return ""

        return "\n".join(all_text)

    def _clean_text(self, text: str) -> str:
        """清理 PDF 提取的噪声"""
        # 移除独立的页码行
        text = re.sub(r'^\d{1,4}$', '', text, flags=re.MULTILINE)
        # 移除页眉页脚常见模式（如 "作者名 / 期刊名" 跨页重复）
        text = re.sub(r'^\d+\s*\n', '\n', text, flags=re.MULTILINE)
        # 合并多余的连续空行
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        # 清理尾部空格
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
        # 移除零宽字符
        text = re.sub(r'[​‌‍﻿]', '', text)
        return text.strip()

    def _fix_broken_lines(self, text: str) -> str:
        """修复 PDF 提取中常见的断行问题。

        PDF 提取经常在段落中间产生不必要的换行。
        将不以标点/冒号结尾且下一行以小写字母开头的行合并。
        """
        lines = text.split('\n')
        fixed = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                fixed.append('')
                i += 1
                continue

            # 如果当前行不以句号/问号/感叹号/冒号/引号结尾，
            # 且下一行存在且不以大写字母、数字编号或空行开头 → 合并
            if (i + 1 < len(lines) and
                not re.search(r'[.!?:\"»)]$', line) and
                len(line) > 20 and  # 短行（标题）不合并
                lines[i + 1].strip() and
                not re.match(r'^[A-Z0-9#]', lines[i + 1].strip()) and
                not re.match(r'^\[', lines[i + 1].strip())):

                fixed.append(line + ' ' + lines[i + 1].strip())
                i += 2
            else:
                fixed.append(line)
                i += 1

        return '\n'.join(fixed)

    def _to_markdown(self, text: str) -> str:
        """将清理后的文本转换为 Markdown"""
        lines = text.split('\n')
        md_lines = []
        in_code_block = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                # 空行 = 段落分隔
                md_lines.append('')
                continue

            # 跳过纯页码和短数字行
            if re.match(r'^\d{1,4}$', stripped):
                continue

            # 检测编号章节标题：1. / 1.1 / 2.3.1 等
            numbered_heading = re.match(
                r'^(\d{1,2}(?:\.\d{1,2}){0,2})\s+(.+)', stripped
            )
            if numbered_heading and len(stripped) < 80:
                depth = numbered_heading.group(1).count('.') + 1
                prefix = '#' * min(depth + 1, 4)  # 最多 ####
                md_lines.append(f'\n{prefix} {stripped}')
                continue

            # 检测常见学术章节标题
            is_section = False
            for pattern in self.SECTION_PATTERNS:
                if re.match(pattern, stripped, re.IGNORECASE):
                    is_section = True
                    break
            if is_section and len(stripped) < 60:
                md_lines.append(f'\n## {stripped}')
                continue

            # 检测全大写短行 → 很可能是标题
            if (stripped.isupper() and len(stripped) < 60 and
                len(stripped.split()) >= 2):
                md_lines.append(f'\n### {stripped.title()}')
                continue

            # 检测列表项
            list_match = re.match(r'^[\-\•\*\d+]\s{1,3}', stripped)
            if list_match:
                md_lines.append(f'- {stripped[list_match.end():]}')
                continue

            # 普通段落
            md_lines.append(stripped)

        # 合并结果
        result = '\n'.join(md_lines)
        # 清理多余空行
        result = re.sub(r'\n{3,}', '\n\n', result)
        # 确保标题前后有空行
        result = re.sub(r'([^\n])\n(#{1,4}\s)', r'\1\n\n\2', result)
        return result.strip()

    def _download_pdf(self, url: str, save_dir: str = "outputs") -> str:
        """下载远程 PDF 文件"""
        import urllib.request

        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.join(save_dir, f"downloaded_{abs(hash(url))}.pdf")

        req = urllib.request.Request(url, headers={"User-Agent": "PaperAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(filename, "wb") as f:
                f.write(resp.read())

        return filename

    def run(self, parameters: Dict[str, Any]) -> ToolResponse:
        file_path = parameters.get("file_path", "")
        url = parameters.get("url", "")
        start_page = parameters.get("start_page", 1)
        end_page = parameters.get("end_page", -1)
        max_chars = parameters.get("max_chars", 0) or 0  # 0 = 不限制

        if not file_path and not url:
            return ToolResponse.error(
                code="INVALID_PARAM",
                message="请提供 file_path（本地文件路径）或 url（PDF 链接）"
            )

        try:
            if url:
                file_path = self._download_pdf(url)

            if not os.path.exists(file_path):
                return ToolResponse.error(
                    code="NOT_FOUND",
                    message=f"文件不存在: {file_path}"
                )

            # 1. 提取原始文本
            raw_text = self._extract_raw_text(file_path, start_page, end_page)

            if not raw_text:
                return ToolResponse.error(
                    code="INVALID_FORMAT",
                    message="未能从 PDF 中提取到文本。可能是扫描版 PDF（图片格式），建议使用 OCR 工具预处理。"
                )

            # 2. 清洗 → 3. 修复断行 → 4. 转 Markdown
            cleaned = self._clean_text(raw_text)
            fixed = self._fix_broken_lines(cleaned)
            markdown = self._to_markdown(fixed)

            # 可选截断（max_chars=0 时不限制）
            truncated = max_chars > 0 and len(markdown) > max_chars
            if truncated:
                markdown = markdown[:max_chars]
                last_break = max(markdown.rfind('\n\n'), markdown.rfind('\n'))
                if last_break > max_chars * 0.8:
                    markdown = markdown[:last_break]
                markdown += f"\n\n> *内容已截断（共显示前 {max_chars} 字符）。设为 0 可获取全文。*"

            stats = {
                "total_chars": len(markdown),
                "word_count": len(markdown.split()),
                "line_count": len(markdown.split("\n")),
                "pages": f"{start_page}-{end_page if end_page != -1 else '全部'}",
                "truncated": truncated,
                "format": "markdown"
            }

            return ToolResponse.success(text=markdown, data=stats)

        except ImportError as e:
            return ToolResponse.error(
                code="INTERNAL_ERROR",
                message=str(e)
            )
        except Exception as e:
            return ToolResponse.error(
                code="EXECUTION_ERROR",
                message=f"PDF 转 Markdown 失败: {str(e)}"
            )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="file_path", type="string",
                description="PDF 文件本地路径",
                required=False
            ),
            ToolParameter(
                name="url", type="string",
                description="PDF 文件 URL（如 arXiv 论文链接）",
                required=False
            ),
            ToolParameter(
                name="start_page", type="integer",
                description="起始页码（默认 1）",
                required=False
            ),
            ToolParameter(
                name="end_page", type="integer",
                description="结束页码（-1 表示全部）",
                required=False
            ),
            ToolParameter(
                name="max_chars", type="integer",
                description="最大返回字符数（0=不限制，默认 0）",
                required=False
            ),
        ]
