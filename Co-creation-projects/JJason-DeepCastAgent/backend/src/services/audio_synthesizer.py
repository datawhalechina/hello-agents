"""将音频片段合成为单个播客文件的服务。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from pydub import AudioSegment

from config import Configuration

logger = logging.getLogger(__name__)


class PodcastSynthesisService:
    """将多个音频片段组合成最终的播客文件。"""

    def __init__(self, config: Configuration) -> None:
        """
        初始化音频合成服务。

        Args:
            config: 包含 ffmpeg 路径和输出路径的配置对象。
        """
        self._config = config
        self._output_dir = Path(config.audio_output_dir)
        
        # 如果提供了 ffmpeg 路径，则进行配置
        if config.ffmpeg_path:
            AudioSegment.converter = config.ffmpeg_path
            logger.info("Configured ffmpeg path: %s", config.ffmpeg_path)
        
        # 确保 pydub/ffmpeg 可用 - 假设 ffmpeg 已安装在系统中
        # 如果没有，pydub 可能会发出警告或失败，但我们会捕获异常。

    def synthesize_podcast(self, audio_files: list[str], task_id: str = "default", cancel_check: Callable[[], bool] | None = None) -> str | None:
        """
        将音频文件组合成单个播客 MP3。

        Args:
            audio_files: 按顺序排列的输入音频文件路径列表。
            task_id: 输出文件名的唯一标识符。
            cancel_check: 可选的取消检查回调，返回 True 表示已取消。

        Returns:
            最终播客文件的路径，如果失败则为 None。
        """
        if not audio_files:
            logger.warning("No audio files provided for synthesis.")
            return None

        try:
            combined = AudioSegment.empty()
            
            # 片段之间的静音（例如 500ms）
            silence = AudioSegment.silent(duration=500)

            valid_segments_count = 0
            for file_path in audio_files:
                # 检查是否已取消
                if cancel_check and cancel_check():
                    logger.info("Podcast synthesis cancelled.")
                    return None
                    
                path = Path(file_path)
                if not path.exists():
                    logger.warning("Audio file not found: %s", file_path)
                    continue
                
                try:
                    segment = AudioSegment.from_file(file_path, format="mp3")
                    if valid_segments_count > 0:
                        combined += silence
                    combined += segment
                    valid_segments_count += 1
                except Exception as e:
                    logger.error("Failed to load audio segment %s: %s", file_path, e)

            if valid_segments_count == 0:
                logger.error("No valid audio segments to combine.")
                return None

            output_filename = f"podcast_{task_id}.mp3"
            output_path = self._output_dir / output_filename
            
            # 导出
            logger.info("Exporting podcast to %s...", output_path)
            combined.export(output_path, format="mp3")
            
            return str(output_path)

        except Exception as e:
            logger.exception("Podcast synthesis failed: %s", e)
            return None
