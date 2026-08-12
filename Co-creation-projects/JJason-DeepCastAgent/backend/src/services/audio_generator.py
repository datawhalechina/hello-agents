"""使用 TTS API 从文本生成音频的服务。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from threading import Event

import requests

from config import Configuration

logger = logging.getLogger(__name__)


class AudioGenerationService:
    """处理与 TTS 服务的交互以生成音频文件。"""

    def __init__(self, config: Configuration) -> None:
        """
        初始化音频生成服务。

        Args:
            config: 包含 TTS 配置和输出路径的配置对象。
        """
        self._config = config
        self._output_dir = Path(config.audio_output_dir)
        self._ensure_output_dir()

    def _ensure_output_dir(self) -> None:
        """
        如果输出目录不存在，则创建它。
        
        同时处理创建目录时的潜在权限错误。
        """
        if not self._output_dir.exists():
            try:
                self._output_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Created audio output directory: %s", self._output_dir)
            except Exception as e:
                logger.error("Failed to create audio output directory: %s", e)

    def generate_audio(
        self, 
        script: list[dict[str, str]], 
        task_id: str = "default",
        progress_callback: Callable[[int, int, str, str], bool | None] | None = None,
        cancel_event: Event | None = None,
    ) -> list[str]:
        """
        为给定的脚本生成音频文件。
        
        Args:
            script: 对话回合列表，例如 [{"role": "Host", "content": "..."}, ...]
            task_id: 当前任务/会话的唯一标识符
            progress_callback: 可选的进度回调函数，签名为 (current, total, role, content_preview) -> Optional[bool]
                              返回 False 表示应该停止生成，返回 True 或 None 表示继续
            cancel_event: 可选的取消事件，set 时立即停止生成
            
        Returns:
            生成的音频文件的路径列表
        """
        # 检查FFmpeg路径是否配置
        if not self._config.ffmpeg_path:
            logger.error("FFmpeg path not configured. Audio generation will fail.")
            return []
        if not self._config.tts_api_key:
            logger.warning("TTS API key not configured. Skipping audio generation.")
            return []

        generated_files = []
        total = len(script)
        
        for index, turn in enumerate(script):
            role = turn.get("role", "")
            content = turn.get("content", "")
            
            if not role or not content:
                continue

            # 直接检查取消事件（最可靠的方式）
            if cancel_event and cancel_event.is_set():
                logger.info("Audio generation cancelled before TTS %d/%d (cancel_event)", index + 1, total)
                break
                
            voice_id = self._get_voice_for_role(role)
            if not voice_id:
                logger.warning("Unknown role: %s. Using default voice.", role)
                voice_id = "xiayu" # Fallback
            
            file_name = f"{task_id}_{index:03d}_{role}.mp3"
            file_path = self._output_dir / file_name
            
            logger.info("[TTS %d/%d] 正在为 %s 生成语音: %s...", index + 1, total, role, content[:20])
            
            if self._call_tts_api(content, voice_id, file_path):
                generated_files.append(str(file_path))
                logger.info("[TTS %d/%d] ✓ %s 语音生成成功", index + 1, total, role)
                
                # TTS 完成后再次检查取消
                if cancel_event and cancel_event.is_set():
                    logger.info("Audio generation cancelled after TTS %d/%d (cancel_event)", index + 1, total)
                    break
                
                # 在 TTS 成功之后才调用进度回调，通知上层该片段已完成
                if progress_callback:
                    content_preview = content[:30] + "..." if len(content) > 30 else content
                    should_continue = progress_callback(index + 1, total, role, content_preview)
                    if should_continue is False:
                        logger.info("Audio generation cancelled by callback after TTS %d/%d", index + 1, total)
                        break
            else:
                logger.error("[TTS %d/%d] ✗ %s 语音生成失败", index + 1, total, role)
                
        logger.info("Generated %d audio files for task %s", len(generated_files), task_id)
        return generated_files

    def _get_voice_for_role(self, role: str) -> str:
        """
        将角色名称映射到语音 ID。
        
        Args:
            role: 角色名称（如 Host, Guest）。
            
        Returns:
            对应的语音 ID（xiayu 或 liwa）。
        """
        role_lower = role.lower()
        if "host" in role_lower or "xiayu" in role_lower:
            return "xiayu"
        elif "guest" in role_lower or "liwa" in role_lower:
            return "liwa"
        return "xiayu"

    def _call_tts_api(self, text: str, voice: str, output_path: Path) -> bool:
        """
        调用 TTS API 并保存音频文件。
        
        Args:
            text: 要转换的文本。
            voice: 语音 ID。
            output_path: 输出文件路径。
            
        Returns:
            如果成功生成并保存，返回 True；否则返回 False。
        """
        if output_path.exists():
            logger.debug("Audio file already exists: %s", output_path)
            return True

        headers = {
            "Authorization": f"Bearer {self._config.tts_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self._config.tts_model,
            "input": text,
            "voice": voice,
            "speed": 1.0
        }
        
        try:
            logger.debug("Calling TTS API for voice %s: %s...", voice, text[:20])
            # Use configurable timeout if available; default to 300 seconds for robustness.
            timeout = self._config.tts_timeout
            response = requests.post(
                self._config.tts_base_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
            else:
                logger.error(
                    "TTS API failed with status %d: %s", 
                    response.status_code, 
                    response.text
                )
                return False
                
        except Exception as e:
            logger.exception("Exception during TTS API call: %s", e)
            return False
