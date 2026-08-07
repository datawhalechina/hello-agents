from __future__ import annotations

import importlib
import io
import sys
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from backend.agents.base import BaseAgent
from backend.config import settings
from backend.events import event_logger
from backend.maintenance import cleanup_rss_artifacts
from backend.memory.base import memory_store
from backend.models import AgentRequest, AgentResponse


class RSSDigestAdapter(BaseAgent):
    """Expose rss_digest as one information/news platform agent."""

    def run(self, request: AgentRequest) -> AgentResponse:
        event_logger.emit("agent_started", agent_id=self.agent_id, task_id=request.task_id)
        try:
            output, artifacts = self._run_with_artifacts(request)
        except Exception as exc:
            output = f"资讯员运行失败：{type(exc).__name__}: {exc}"
            artifacts = {"error": str(exc), "error_type": type(exc).__name__}
            print(f"[rss_digest][error] {output}")

        memory_store.add(self.agent_id, f"input={request.input} output={output}")
        event = event_logger.emit(
            "agent_completed",
            agent_id=self.agent_id,
            task_id=request.task_id,
            payload={
                "output_preview": output[:200],
                "artifact_keys": sorted(artifacts.keys()),
            },
        )
        return AgentResponse(
            agent_id=self.agent_id,
            output=output,
            artifacts=artifacts,
            events=[event],
        )

    def _run(self, request: AgentRequest) -> str:
        output, _ = self._run_with_artifacts(request)
        return output

    def _run_with_artifacts(self, request: AgentRequest) -> tuple[str, dict[str, Any]]:
        root_dir = Path(settings.rss_digest_root).resolve()
        data_root = Path(settings.rss_digest_data_root).resolve()
        cleanup_stats = cleanup_rss_artifacts()
        print(f"[rss_digest] start {datetime.now().isoformat(timespec='seconds')} input={request.input[:80]}")

        if not root_dir.exists():
            message = f"rss_digest 项目路径不存在，无法运行资讯员：{root_dir}"
            print(f"[rss_digest][error] {message}")
            return message, {
                "ready": False,
                "rss_digest_root": str(root_dir),
                "rss_digest_data_root": str(data_root),
                "cleanup": cleanup_stats,
            }

        if request.context.get("mode") == "group_chat":
            digest_path = self._latest_digest_path(data_root)
            print("[rss_digest] skipped: group_chat guard")
            if digest_path:
                return (
                    f"资讯员已就绪。最新 RSS 简报：{digest_path}",
                    {
                        "skipped": True,
                        "reason": "batch_guard",
                        "digest_path": str(digest_path),
                        "rss_digest_data_root": str(data_root),
                        "cleanup": cleanup_stats,
                    },
                )
            return (
                "资讯员是较长耗时流程。请单独使用 @rss_digest 生成或更新 RSS 中文简报。",
                {"skipped": True, "reason": "batch_guard", "cleanup": cleanup_stats},
            )

        if request.context.get("dry_run"):
            print("[rss_digest] dry_run ok")
            return (
                "资讯员已接入 rss_digest，真实运行会拉取 RSS、生成中文摘要并输出 HTML 简报。",
                {
                    "ready": True,
                    "rss_digest_root": str(root_dir),
                    "rss_digest_data_root": str(data_root),
                    "cleanup": cleanup_stats,
                },
            )

        modules = self._load_rss_modules(root_dir)
        force_refresh = bool(request.context.get("force_refresh")) or self._is_force_refresh(request.input)
        today_digest_path = self._today_digest_path(data_root)
        if today_digest_path and not force_refresh:
            print("[rss_digest] skipped: today digest exists")
            recent_articles = self._recent_articles(root_dir, data_root, modules, limit=8)
            digest_url = self._digest_url(today_digest_path)
            run_stats = {
                "skipped": True,
                "reason": "today_digest_exists",
                "digest_article_count": len(recent_articles),
                "llm_enabled": True,
            }
            return self._format_output(today_digest_path, digest_url, recent_articles, run_stats), {
                "skipped": True,
                "reason": "today_digest_exists",
                "rss_digest_root": str(root_dir),
                "rss_digest_data_root": str(data_root),
                "digest_path": str(today_digest_path),
                "digest_url": digest_url,
                "recent_articles": recent_articles,
                "run_stats": run_stats,
                "cleanup": cleanup_stats,
            }

        stdout_buffer = io.StringIO()
        print("[rss_digest] running pipeline")
        started = perf_counter()
        with redirect_stdout(stdout_buffer):
            run_stats = modules["pipeline"].run_pipeline(root_dir, data_root)
        run_stats["adapter_total_seconds"] = round(perf_counter() - started, 3)
        print(
            "[rss_digest] complete "
            f"discovered={run_stats.get('discovered', 0)} "
            f"extracted={run_stats.get('extracted', 0)} "
            f"summarized={run_stats.get('summarized', 0)} "
            f"digest_articles={run_stats.get('digest_article_count', 0)} "
            f"seconds={run_stats.get('adapter_total_seconds')}"
        )

        digest_path = self._latest_digest_path(data_root)
        digest_url = self._digest_url(digest_path)
        recent_articles = self._recent_articles(root_dir, data_root, modules, limit=8)

        output = self._format_output(digest_path, digest_url, recent_articles, run_stats)
        artifacts = {
            "rss_digest_root": str(root_dir),
            "rss_digest_data_root": str(data_root),
            "digest_path": str(digest_path) if digest_path else None,
            "digest_url": digest_url,
            "recent_articles": recent_articles,
            "run_stats": run_stats,
            "stdout": stdout_buffer.getvalue().strip(),
            "cleanup": cleanup_stats,
        }
        return output, artifacts

    @staticmethod
    def _load_rss_modules(root_dir: Path) -> dict[str, Any]:
        src_dir = root_dir / "src"
        src_text = str(src_dir)
        if src_text not in sys.path:
            sys.path.insert(0, src_text)

        return {
            "pipeline": importlib.import_module("rss_digest.pipeline"),
            "config": importlib.import_module("rss_digest.config"),
            "db": importlib.import_module("rss_digest.db"),
        }

    @staticmethod
    def _latest_digest_path(data_root: Path) -> Path | None:
        digest_dir = data_root / "runs" / "digests"
        files = sorted(digest_dir.glob("digest_*.html"), key=lambda path: path.stat().st_mtime, reverse=True)
        return files[0] if files else None

    @staticmethod
    def _today_digest_path(data_root: Path) -> Path | None:
        digest_path = data_root / "runs" / "digests" / f"digest_{datetime.now().strftime('%Y-%m-%d')}.html"
        return digest_path if digest_path.exists() else None

    @staticmethod
    def _is_force_refresh(text: str) -> bool:
        normalized = text.lower()
        return any(token in normalized for token in ("强制", "重新生成", "刷新", "force", "refresh"))

    @staticmethod
    def _digest_url(digest_path: Path | None) -> str | None:
        if not digest_path:
            return None
        return f"/rss-digests/{digest_path.name}"

    @staticmethod
    def _recent_articles(root_dir: Path, data_root: Path, modules: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        cfg = modules["config"].build_config(root_dir, data_root)
        conn = modules["db"].connect(cfg.db_path)
        modules["db"].init_db(conn)
        rows = modules["db"].get_recent_articles(conn, limit=limit)
        return [
            {
                "title": row.get("title", ""),
                "source_name": row.get("source_name", ""),
                "category": row.get("category", ""),
                "published_at": row.get("published_at", ""),
                "link": row.get("link", ""),
                "article_score": row.get("article_score"),
                "one_line": row.get("one_line"),
                "worth_reading": row.get("worth_reading"),
            }
            for row in rows
        ]

    @staticmethod
    def _format_output(
        digest_path: Path | None,
        digest_url: str | None,
        articles: list[dict[str, Any]],
        run_stats: dict[str, Any] | None,
    ) -> str:
        lines = ["资讯员已完成 RSS 更新和中文摘要生成。"]
        if run_stats:
            lines.append(
                "本轮统计："
                f"RSS新增 {run_stats.get('discovered', 0)}，"
                f"正文抽取 {run_stats.get('extracted', 0)}，"
                f"LLM摘要 {run_stats.get('summarized', 0)}，"
                f"本次简报文章 {run_stats.get('digest_article_count', 0)}，"
                f"LLM启用 {run_stats.get('llm_enabled', False)}。"
            )
            if run_stats.get("no_new_articles"):
                lines.append("提示：本次没有新的未读文章进入简报，已避免重复展示今天看过的内容。")
            if run_stats.get("llm_enabled") and run_stats.get("summarized", 0) == 0:
                lines.append("提示：LLM 已配置，但本轮没有成功摘要新文章，可查看任务 artifacts 中的 stdout 和 run_stats。")
            if not run_stats.get("llm_enabled"):
                lines.append("提示：LLM 未启用，请检查 .env 中的 LLM_MODEL_ID、LLM_API_KEY、LLM_BASE_URL。")
        if digest_path:
            lines.append(f"最新 HTML 简报：{digest_path}")
        if digest_url:
            lines.append(f"点击打开：{digest_url}")
        if articles:
            lines.append("")
            lines.append("最新文章：")
            for index, article in enumerate(articles[:5], start=1):
                title = article.get("title") or "未命名文章"
                source = article.get("source_name") or "未知来源"
                score = article.get("article_score")
                score_text = f"，评分 {score}" if score is not None else ""
                lines.append(f"{index}. {title}，{source}{score_text}")
                one_line = article.get("one_line")
                if one_line:
                    lines.append(f"   {one_line}")
        return "\n".join(lines)
