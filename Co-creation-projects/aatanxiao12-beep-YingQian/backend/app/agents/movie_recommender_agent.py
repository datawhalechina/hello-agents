"""多智能体电影推荐编排（串行流水线）。

范式：Pipeline + Tool-use
  ① 画像 Agent（无工具）→ TasteProfile
  ② 检索 Agent（挂 MovieTool）→ 真片候选
  ③ 推荐 Agent（无工具）→ 仅在候选 id 内产出 RecommendResult

本模块只提供编排器；HTTP 路由后续再接。
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime
from typing import Any, List, Optional, Tuple

from hello_agents import Config, SimpleAgent

from ..config import get_settings
from ..models.schemas import (
    CandidateMovie,
    MovieCard,
    RecommendRequest,
    RecommendResult,
    TasteProfile,
)
from ..services.llm_service import get_llm
from ..services.movie_service import get_movie_service, normalize_tmdb_language
from ..tools.movie_tool import get_movie_tool
from ..utils.logger import get_logger

logger = get_logger("app.agents")

# ============ Prompts ============

PROFILE_AGENT_PROMPT = """你是观影口味画像专家。根据用户偏好输出结构化 JSON，不要推荐具体片名。

只返回如下 JSON（不要 Markdown 代码块外的解释）:
{
  "summary": "一句话口味摘要",
  "genre_hints": ["类型1", "类型2"],
  "language_hints": ["仅填 ISO 码：zh / en / ja / ko，可空；禁止写好莱坞、英语等中文"],
  "avoid": ["需规避的内容"],
  "discover_notes": "给 TMDB discover 用的简短检索说明"
}
"""

SEARCH_AGENT_PROMPT = """你是电影检索专家。必须调用工具从 TMDB 取真实影片，禁止编造片名。

可用工具:
- movies_discover: 主路径，按类型/年份/时长/语言发现（本轮只允许调用 1 次）
- movies_search: 仅当需要解析「已看片名」时再用（可选，最多 1~2 次）

硬规则:
1. movies_discover 只调用一次：用建议参数一次取够候选，禁止换参反复 discover
2. with_original_language 只能是 zh/en/ja/ko；不要传「好莱坞」「英语」等中文
3. 拿到工具结果后立即输出最终 JSON，不要再调工具「精炼」
4. 最终 movies 必须从工具结果原样抄写关键字段（含 poster_url）

取数后，最终回复必须是 JSON（不要多余解释）:
{
  "movies": [
    {
      "id": 123,
      "title": "...",
      "year": 2020,
      "genres": [],
      "rating": 7.5,
      "poster_url": "https://...",
      "overview": "..."
    }
  ]
}

要求:
1. 尽量返回 15~25 部
2. id / title / poster_url 等必须来自工具结果，禁止省略 poster_url
3. 排除用户已给出的 exclude_ids
"""

RECOMMEND_AGENT_PROMPT = """你是电影推荐专家。你没有外部工具，只能从「候选列表」中挑选 3~5 部。

硬约束:
1. 每部电影的 id 必须出现在候选列表中
2. 禁止编造候选之外的片名或 id
3. 遵守 spoilers_ok：若为 false，overview_safe 不要写结局剧透
4. why 要贴合用户心情与人群
5. title / year / genres / rating / poster_url 尽量原样沿用候选列表（勿改写为空）

只返回 JSON:
{
  "playlist_name": "片单主题名",
  "profile_summary": "对用户口味的一句话总结",
  "movies": [
    {
      "id": 123,
      "title": "...",
      "year": 2020,
      "genres": ["..."],
      "runtime": null,
      "rating": 7.5,
      "poster_url": "https://image.tmdb.org/t/p/w500/...",
      "why": "推荐理由",
      "vibe_tags": ["标签"],
      "caution": null,
      "overview_safe": "安全简介"
    }
  ],
  "is_fallback": false
}
"""


REGION_LANGUAGE = {
    "华语": "zh",
    "好莱坞": "en",
    "日韩": "ja",  # 简化：先按日语；韩语可由画像 language_hints 覆盖
    "欧洲": "",
    "不限": "",
}


class MultiAgentMovieRecommender:
    """串行三 Agent 推荐编排器（画像 → 检索 → 推荐 + 白名单校验）。"""

    def __init__(self) -> None:
        """初始化共享 LLM / MovieTool，并创建三个 SimpleAgent。"""
        self.llm = get_llm()
        self.movie_tool = get_movie_tool()
        settings = get_settings()
        # Trace 开关来自 .env：TRACE_ENABLED / TRACE_DIR
        agent_config = Config(
            trace_enabled=settings.trace_enabled,
            trace_dir=settings.trace_dir,
        )

        # 画像：只做偏好结构化，禁止挂工具（避免这步就去搜片/编片名）
        self.profile_agent = SimpleAgent(
            name="画像专家",
            llm=self.llm,
            system_prompt=PROFILE_AGENT_PROMPT,
            config=agent_config,
            enable_tool_calling=False,
        )
        # 检索：唯一允许碰 TMDB 的 Agent；工具展开为 discover / search
        # max_tool_iterations=2：1 轮工具 + 1 轮收尾文本；再高容易反复换参 discover
        self.search_agent = SimpleAgent(
            name="检索专家",
            llm=self.llm,
            system_prompt=SEARCH_AGENT_PROMPT,
            config=agent_config,
            max_tool_iterations=2,
        )
        self.search_agent.add_tool(self.movie_tool)

        # 推荐：无工具，只能在上游候选里选择与说理（防幻觉核心）
        self.recommend_agent = SimpleAgent(
            name="推荐专家",
            llm=self.llm,
            system_prompt=RECOMMEND_AGENT_PROMPT,
            config=agent_config,
            enable_tool_calling=False,
        )
        logger.info(
            "MultiAgentMovieRecommender 就绪: tools=%s trace=%s",
            self.search_agent.list_tools(),
            settings.trace_enabled,
        )

    def recommend(self, request: RecommendRequest) -> Tuple[RecommendResult, str]:
        """跑完整推荐流水线。

        Returns:
            (RecommendResult, message)：业务结果 + 给人看的状态说明（含降级提示）。
        """
        pipeline_t0 = time.perf_counter()
        try:
            logger.info("推荐开始 mood=%s party=%s", request.mood, request.party_type)

            # ① 偏好 → TasteProfile；换一批可携带 taste_profile 跳过画像 LLM
            t0 = time.perf_counter()
            profile, profile_reused = self._resolve_profile(request)
            logger.info(
                "阶段完成 stage=profile elapsed=%.2fs reused=%s summary=%s",
                time.perf_counter() - t0,
                profile_reused,
                profile.summary,
            )

            # ② 真片候选；失败则降级，避免在空列表上瞎荐
            t0 = time.perf_counter()
            candidates = self._run_search(request, profile)
            logger.info(
                "阶段完成 stage=search elapsed=%.2fs candidates=%d",
                time.perf_counter() - t0,
                len(candidates),
            )
            if not candidates:
                result = self._fallback_result(request, profile, [], "未取得候选片")
                return result, "检索无结果，已返回降级片单"

            # ③ 候选内推荐 + 代码层 id 白名单（不信任模型自觉）
            t0 = time.perf_counter()
            result = self._run_recommend(request, profile, candidates)
            logger.info(
                "阶段完成 stage=recommend_llm elapsed=%.2fs",
                time.perf_counter() - t0,
            )
            t0 = time.perf_counter()
            result = self._enforce_candidate_ids(result, candidates, profile)
            result = self._attach_taste_profile(result, profile)
            logger.info(
                "阶段完成 stage=enforce elapsed=%.2fs movies=%d fallback=%s total=%.2fs",
                time.perf_counter() - t0,
                len(result.movies),
                result.is_fallback,
                time.perf_counter() - pipeline_t0,
            )
            msg = "推荐生成成功" if not result.is_fallback else "推荐已做 id 校正/降级"
            if profile_reused:
                msg = f"{msg}（已跳过画像）"
            return result, msg

        except Exception as e:
            # 未捕获异常也返回完整结构，前端不白屏
            logger.exception("推荐流水线异常")
            result = self._fallback_result(request, None, [], str(e))
            return result, f"推荐异常，已降级: {e}"

    # ----- stages -----

    def _resolve_profile(self, request: RecommendRequest) -> Tuple[TasteProfile, bool]:
        """解析画像：请求携带可用 taste_profile 则复用，否则跑画像 Agent。"""
        reused = request.taste_profile
        if reused is not None and (
            (reused.summary or "").strip()
            or reused.genre_hints
            or (reused.discover_notes or "").strip()
        ):
            logger.info("跳过画像 Agent，复用请求中的 taste_profile")
            return self._sanitize_profile(reused, request), True
        return self._sanitize_profile(self._run_profile(request), request), False

    def _sanitize_profile(
        self,
        profile: TasteProfile,
        request: RecommendRequest,
    ) -> TasteProfile:
        """规范化 language_hints 为 ISO 码；非法项丢弃。"""
        cleaned: List[str] = []
        for hint in profile.language_hints or []:
            code = normalize_tmdb_language(hint)
            if code and code not in cleaned:
                cleaned.append(code)
        if not cleaned:
            fallback = normalize_tmdb_language(
                REGION_LANGUAGE.get(request.region_preference, "")
            )
            if fallback:
                cleaned = [fallback]
        if cleaned != list(profile.language_hints or []):
            logger.info(
                "画像 language_hints 已归一化: %s -> %s",
                profile.language_hints,
                cleaned,
            )
        profile.language_hints = cleaned
        return profile

    def _resolve_language(
        self,
        request: RecommendRequest,
        profile: TasteProfile,
    ) -> Optional[str]:
        """解析最终用于 discover 的语言码。"""
        if profile.language_hints:
            code = normalize_tmdb_language(profile.language_hints[0])
            if code:
                return code
        return normalize_tmdb_language(
            REGION_LANGUAGE.get(request.region_preference, "")
        )

    def _attach_taste_profile(
        self,
        result: RecommendResult,
        profile: TasteProfile,
    ) -> RecommendResult:
        """把本次画像挂到结果上，供换一批回传。"""
        result.taste_profile = profile
        if not result.profile_summary:
            result.profile_summary = profile.summary
        return result

    def _run_profile(self, request: RecommendRequest) -> TasteProfile:
        """阶段①：调用画像 Agent，解析为 TasteProfile；失败则用表单字段兜底。"""
        self.profile_agent.clear_history()
        raw = self.profile_agent.run(self._build_profile_query(request))
        data = self._extract_json(raw) or {}
        try:
            return TasteProfile(**data)
        except Exception:
            # 画像 JSON 坏了：用表单字段拼可用 profile，保证后续检索能继续
            return TasteProfile(
                summary=f"{request.mood}/{request.party_type} 观影",
                genre_hints=list(request.genres),
                language_hints=[REGION_LANGUAGE.get(request.region_preference, "")],
                avoid=[],
                discover_notes=request.free_text or "",
            )

    def _run_search(
        self,
        request: RecommendRequest,
        profile: TasteProfile,
    ) -> List[CandidateMovie]:
        """阶段②：检索 Agent 调工具取真片；解析失败则 MovieService 规则 discover 兜底。"""
        self.search_agent.clear_history()
        self.movie_tool.begin_search_run(discover_limit=1)
        t0 = time.perf_counter()
        try:
            raw = self.search_agent.run(self._build_search_query(request, profile))
        finally:
            self.movie_tool.end_search_run()
        logger.info(
            "检索 Agent run 结束 elapsed=%.2fs raw_len=%d",
            time.perf_counter() - t0,
            len(raw or ""),
        )
        movies = self._parse_candidates(raw, request.exclude_ids)
        if movies:
            missing_poster = sum(1 for m in movies if not m.poster_url)
            logger.info(
                "检索 Agent 解析成功 count=%d missing_poster=%d",
                len(movies),
                missing_poster,
            )
            return movies

        # Agent 未给出可用 JSON 时，用 profile 规则直连 MovieService（仍是真数据）
        logger.warning("检索 Agent 未解析出候选，改用 MovieService 规则兜底")
        t0 = time.perf_counter()
        fallback = self._discover_by_profile(request, profile)
        logger.info(
            "阶段完成 stage=search_fallback_discover elapsed=%.2fs count=%d",
            time.perf_counter() - t0,
            len(fallback),
        )
        return fallback

    def _run_recommend(
        self,
        request: RecommendRequest,
        profile: TasteProfile,
        candidates: List[CandidateMovie],
    ) -> RecommendResult:
        """阶段③：推荐 Agent 仅在候选内产出 RecommendResult；JSON 坏则降级。"""
        self.recommend_agent.clear_history()
        raw = self.recommend_agent.run(
            self._build_recommend_query(request, profile, candidates)
        )
        data = self._extract_json(raw)
        if not data:
            return self._fallback_result(request, profile, candidates, "推荐 JSON 解析失败")
        try:
            data.setdefault("is_fallback", False)
            # 画像由编排器挂载，不采信模型自带的 taste_profile 字段
            data.pop("taste_profile", None)
            return RecommendResult(**data)
        except Exception:
            return self._fallback_result(request, profile, candidates, "推荐结构校验失败")

    # ----- queries -----

    def _build_profile_query(self, request: RecommendRequest) -> str:
        """把 RecommendRequest 拼成画像 Agent 的用户输入文本。"""
        return (
            f"心情: {request.mood}\n"
            f"人群: {request.party_type}\n"
            f"类型偏好: {', '.join(request.genres) or '无'}\n"
            f"时长上限(分钟): {request.max_runtime_minutes}\n"
            f"地区: {request.region_preference}\n"
            f"年代: {request.year_preference}\n"
            f"已看过: {', '.join(request.exclude_titles) or '无'}\n"
            f"允许剧透: {request.spoilers_ok}\n"
            f"额外要求: {request.free_text or '无'}\n"
            "请输出 TasteProfile JSON。"
        )

    def _build_search_query(self, request: RecommendRequest, profile: TasteProfile) -> str:
        """把画像 + 表单约束拼成检索 Agent 输入（含建议的 discover 参数）。"""
        # 预先算好 discover 参数提示，降低模型乱填工具参数的概率
        year_gte, year_lte = self._year_bounds(request.year_preference)
        lang = self._resolve_language(request, profile) or ""

        genres = ",".join(profile.genre_hints or request.genres)
        parts = [
            "请只调用一次 movies_discover（用下列建议参数），取到结果后立刻输出 JSON；不要反复换参 discover。",
            f"画像摘要: {profile.summary}",
            f"建议 with_genres: {genres or '不限'}",
            f"建议 year_gte: {year_gte or 0}, year_lte: {year_lte or 0}",
            f"建议 max_runtime: {request.max_runtime_minutes or 0}",
            f"建议 with_original_language: {lang or '不限'}（仅 zh/en/ja/ko）",
            f"discover_notes: {profile.discover_notes}",
            f"exclude_ids: {request.exclude_ids}",
            f"已看片名(仅必要时用 movies_search 辅助排除): {request.exclude_titles}",
            "最终只输出含 movies 数组的 JSON，且每部必须带工具返回的 poster_url。",
        ]
        return "\n".join(parts)

    def _build_recommend_query(
        self,
        request: RecommendRequest,
        profile: TasteProfile,
        candidates: List[CandidateMovie],
    ) -> str:
        """把用户偏好 + 精简候选列表拼成推荐 Agent 输入。"""
        # 只塞精简字段进 prompt；片名/海报等最终以候选元数据为准
        slim = [
            {
                "id": c.id,
                "title": c.title,
                "year": c.year,
                "genres": c.genres,
                "rating": c.rating,
                "poster_url": c.poster_url,
                "overview": (c.overview or "")[:180],
            }
            for c in candidates
        ]
        return (
            f"用户心情: {request.mood}; 人群: {request.party_type}; "
            f"剧透允许: {request.spoilers_ok}\n"
            f"画像: {profile.summary}\n"
            f"额外要求: {request.free_text or '无'}\n"
            f"候选列表(只能从中选):\n{json.dumps(slim, ensure_ascii=False)}\n"
            "请输出 RecommendResult JSON（3~5 部）。"
        )

    # ----- helpers -----

    @staticmethod
    def _year_bounds(year_preference: str) -> Tuple[Optional[int], Optional[int]]:
        """表单年代偏好 → TMDB discover 的 (year_gte, year_lte)。"""
        year = datetime.now().year
        if year_preference == "近5年":
            return year - 5, None
        if year_preference == "近10年":
            return year - 10, None
        if year_preference == "经典":
            return None, 2000
        return None, None

    def _discover_by_profile(
        self,
        request: RecommendRequest,
        profile: TasteProfile,
    ) -> List[CandidateMovie]:
        """不经 LLM，按画像字段确定性 discover；空结果自动放宽条件。"""
        year_gte, year_lte = self._year_bounds(request.year_preference)
        lang = self._resolve_language(request, profile)
        genres = ",".join(profile.genre_hints or request.genres) or None
        return get_movie_service().discover_with_relax(
            with_genres=genres,
            year_gte=year_gte,
            year_lte=year_lte,
            max_runtime=request.max_runtime_minutes,
            with_original_language=lang,
            page=1,
            exclude_ids=request.exclude_ids,
        )

    def _parse_candidates(self, raw: str, exclude_ids: List[int]) -> List[CandidateMovie]:
        """从检索 Agent 文本抽出 movies，过滤 exclude_ids 与空标题。"""
        data = self._extract_json(raw)
        if not data:
            return []
        items = data.get("movies") if isinstance(data, dict) else None
        if not isinstance(items, list):
            return []
        exclude = set(exclude_ids)
        out: List[CandidateMovie] = []
        for item in items:
            if not isinstance(item, dict) or "id" not in item:
                continue
            try:
                movie = CandidateMovie(
                    id=int(item["id"]),
                    title=str(item.get("title") or ""),
                    year=item.get("year"),
                    genres=item.get("genres") or [],
                    runtime=item.get("runtime"),
                    rating=item.get("rating"),
                    poster_url=item.get("poster_url"),
                    overview=item.get("overview") or "",
                )
            except Exception:
                continue
            if movie.id in exclude or not movie.title:
                continue
            out.append(movie)
        return out

    def _card_from_candidate(
        self,
        src: CandidateMovie,
        *,
        why: str = "",
        vibe_tags: Optional[List[str]] = None,
        caution: Optional[str] = None,
        overview_safe: str = "",
        runtime: Optional[int] = None,
        poster_url: Optional[str] = None,
    ) -> MovieCard:
        """候选 → MovieCard；缺海报时按 id 拉 detail 回填（仅最终 3~5 部）。"""
        poster = src.poster_url or poster_url
        title = src.title
        year = src.year
        genres = list(src.genres or [])
        rating = src.rating
        overview = overview_safe or (src.overview or "")[:200]
        rt = runtime if runtime is not None else src.runtime

        if not poster:
            try:
                detail = get_movie_service().get_detail(src.id)
                poster = detail.poster_url
                title = title or detail.title
                year = year if year is not None else detail.year
                genres = genres or list(detail.genres or [])
                rating = rating if rating is not None else detail.rating
                if not overview_safe and detail.overview:
                    overview = detail.overview[:200]
                if rt is None:
                    rt = detail.runtime
            except Exception:
                logger.warning("MovieCard 海报回填失败 id=%s", src.id)

        return MovieCard(
            id=src.id,
            title=title,
            year=year,
            genres=genres,
            runtime=rt,
            rating=rating,
            poster_url=poster,
            why=why,
            vibe_tags=vibe_tags or [],
            caution=caution,
            overview_safe=overview,
        )

    def _enforce_candidate_ids(
        self,
        result: RecommendResult,
        candidates: List[CandidateMovie],
        profile: TasteProfile,
    ) -> RecommendResult:
        """白名单闸：丢弃候选外 id；元数据以 TMDB 候选为准；不足 3 部则补齐并降级。"""
        allowed = {c.id: c for c in candidates}
        kept: List[MovieCard] = []
        for card in result.movies:
            if card.id not in allowed:
                continue
            src = allowed[card.id]
            kept.append(
                self._card_from_candidate(
                    src,
                    why=card.why,
                    vibe_tags=card.vibe_tags,
                    caution=card.caution,
                    overview_safe=card.overview_safe or (src.overview or "")[:200],
                    runtime=card.runtime if card.runtime is not None else src.runtime,
                    poster_url=card.poster_url,
                )
            )
        if 3 <= len(kept) <= 5:
            result.movies = kept
            return result

        # 合法片不足 3 部：按评分从候选补齐，并标记降级
        result.is_fallback = True
        have = {m.id for m in kept}
        ranked = sorted(
            candidates,
            key=lambda m: (m.rating is not None, m.rating or 0),
            reverse=True,
        )
        for c in ranked:
            if c.id in have:
                continue
            kept.append(
                self._card_from_candidate(
                    c,
                    why="系统按候选热度补齐",
                    overview_safe=(c.overview or "")[:200],
                )
            )
            if len(kept) >= 3:
                break
        result.movies = kept[:5]
        if not result.profile_summary and profile:
            result.profile_summary = profile.summary
        if not result.playlist_name:
            result.playlist_name = "今日候选速选"
        return result

    def _fallback_result(
        self,
        request: RecommendRequest,
        profile: Optional[TasteProfile],
        candidates: List[CandidateMovie],
        reason: str,
    ) -> RecommendResult:
        """诚实降级：尽量用真片凑片单，强制 is_fallback=True。"""
        if not candidates:
            try:
                candidates = self._discover_by_profile(
                    request,
                    profile
                    or TasteProfile(
                        summary=reason,
                        genre_hints=list(request.genres),
                    ),
                )
            except Exception:
                candidates = []

        movies: List[MovieCard] = []
        for c in candidates[:5]:
            movies.append(
                self._card_from_candidate(
                    c,
                    why=f"降级推荐（{reason}）",
                    overview_safe=(c.overview or "")[:200],
                )
            )
        return RecommendResult(
            playlist_name="降级片单",
            profile_summary=(profile.summary if profile else reason),
            movies=movies,
            is_fallback=True,
            taste_profile=profile,
        )

    @staticmethod
    def _extract_json(text: str) -> Optional[dict]:
        """从模型文本提取 JSON 对象（纯 JSON / 代码块 / 夹杂说明均可）。"""
        if not text:
            return None
        text = text.strip()
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            pass
        fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence:
            try:
                data = json.loads(fence.group(1))
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                pass
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
        return None

    def health_snapshot(self) -> dict[str, Any]:
        """返回各 Agent 名称与工具数量（供 /api/recommend/health）。"""
        return {
            "agents": [
                {"name": self.profile_agent.name, "tools_count": 0},
                {
                    "name": self.search_agent.name,
                    "tools_count": len(self.search_agent.list_tools()),
                },
                {"name": self.recommend_agent.name, "tools_count": 0},
            ]
        }


_recommender: Optional[MultiAgentMovieRecommender] = None


def get_movie_recommender() -> MultiAgentMovieRecommender:
    """获取进程内编排器单例（懒加载，避免重复初始化 LLM/Agent）。"""
    global _recommender
    if _recommender is None:
        _recommender = MultiAgentMovieRecommender()
    return _recommender
