import io
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader

MAX_BYTES = 5 * 1024 * 1024
MAX_CHARS = 24000


def extract_text(name: str, content: bytes) -> str:
    suffix = Path(name).suffix.lower()
    if not content or len(content) > MAX_BYTES:
        raise ValueError("请上传非空且不超过 5 MB 的文件。")
    try:
        if suffix in (".txt", ".md"):
            text = content.decode("utf-8-sig")
        elif suffix == ".pdf":
            reader = PdfReader(io.BytesIO(content))
            if reader.is_encrypted:
                raise ValueError("请先解除 PDF 密码保护。")
            if len(reader.pages) > 30:
                raise ValueError("PDF 最多支持 30 页。")
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif suffix == ".docx":
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > 2 * 1024 * 1024:
                    raise ValueError("Word 文档正文过大，请精简后重试。")
                root = ElementTree.fromstring(archive.read(info))
                ns = {
                    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                }
                text = "\n".join(
                    "".join(node.itertext()) for node in root.findall(".//w:p", ns)
                )
        else:
            raise ValueError("支持文字版 PDF、DOCX、UTF-8 TXT 和 Markdown。")
    except ValueError:
        raise
    except Exception:
        raise ValueError("文件无法解析，请换用文字版 PDF 或直接粘贴文本。") from None
    text = text.strip()
    if len(text) < 10:
        raise ValueError(
            "未提取到足够文字。扫描图片暂不支持 OCR，请换用文字版或粘贴文本。"
        )
    if len(text) > MAX_CHARS:
        raise ValueError("正文超过 24,000 字符，请精简后上传；不会静默截断。")
    return text
