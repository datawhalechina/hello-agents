"""OCR Tool - 图片文字提取工具

当用户使用文本模型时，通过 OCR 提取图片中的文字，注入到上下文中。
使用本地 tesseract 作为 OCR 后端。

使用场景：
- 代码截图识别
- 报错截图提取
- 文档图片转文字
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import Tool, ToolParameter


class OCRTool(Tool):
    """OCR 工具 - 本地 tesseract 后端"""
    
    def __init__(self):
        """
        初始化 OCR 工具
        """
        super().__init__(
            name="ocr",
            description="图片文字提取工具 - 从图片中识别并提取文字内容"
        )
    
    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="image_path",
                type="string",
                description="图片文件路径",
                required=True,
            ),
        ]
    
    def run(self, parameters: Dict[str, Any]) -> str:
        """执行 OCR"""
        image_path = parameters.get("image_path", "")
        if not image_path:
            return "错误：未提供图片路径"
        
        path = Path(image_path).expanduser().resolve()
        if not path.exists():
            return f"错误：图片文件不存在: {path}"
        
        # 仅使用本地 tesseract
        result = self._ocr_via_tesseract(path)
        if result and not result.startswith("错误"):
            return result
        return "OCR 失败：请安装并配置 tesseract。"
    
    def _ocr_via_tesseract(self, image_path: Path) -> Optional[str]:
        """通过本地 tesseract 进行 OCR"""
        try:
            # 检查 tesseract 是否安装
            result = subprocess.run(
                ["tesseract", str(image_path), "stdout", "-l", "chi_sim+eng"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                text = result.stdout.strip()
                if text:
                    return text
                return "OCR 结果为空（图片中可能没有可识别的文字）"
            return f"tesseract 错误: {result.stderr}"
        except FileNotFoundError:
            return None  # tesseract 未安装，返回 None 让调用方知道
        except subprocess.TimeoutExpired:
            return "OCR 超时"
        except Exception as e:
            return f"本地 OCR 错误: {e}"


def extract_text_from_image(
    image_path: str | Path,
) -> str:
    """
    便捷函数：从图片提取文字
    
    Args:
        image_path: 图片路径
    Returns:
        提取的文字，或错误信息
    """
    tool = OCRTool()
    return tool.run({"image_path": str(image_path)})
