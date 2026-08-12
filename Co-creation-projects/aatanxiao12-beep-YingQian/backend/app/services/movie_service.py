"""MovieService — TMDB HTTP 封装（D1 确定性通道）。

供 /api/movies/* 与 Agent Tool 复用；密钥仅来自环境变量。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from ..config import Settings, get_settings
from ..exceptions import MovieServiceError
from ..models.schemas import CandidateMovie, MovieDetail
from ..utils.logger import get_logger

logger = get_logger("app.movie_service")

TMDB_API_BASE = "https://api.themoviedb.org/3"

# TMDB with_original_language 只认 ISO 639-1；画像常误传「好莱坞」「英语」
_VALID_TMDB_LANGS = frozenset(
    {"zh", "en", "ja", "ko", "fr", "de", "es", "it", "hi", "th", "pt", "ru"}
)
_LANG_ALIASES = {
    "华语": "zh",
    "中文": "zh",
    "汉语": "zh",
    "普通话": "zh",
    "国语": "zh",
    "好莱坞": "en",
    "英语": "en",
    "英文": "en",
    "english": "en",
    "美片": "en",
    "日韩": "ja",
    "日语": "ja",
    "日本": "ja",
    "japanese": "ja",
    "韩语": "ko",
    "韩文": "ko",
    "韩国": "ko",
    "korean": "ko",
    "法语": "fr",
    "德语": "de",
    "西语": "es",
    "西班牙语": "es",
}


def normalize_tmdb_language(raw: Optional[str]) -> Optional[str]:
    """把地区/中文名归一成 TMDB 语言码；无法识别则返回 None。"""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    lower = text.lower()
    if lower in _VALID_TMDB_LANGS:
        return lower
    mapped = _LANG_ALIASES.get(text) or _LANG_ALIASES.get(lower)
    if mapped in _VALID_TMDB_LANGS:
        return mapped
    # 容错：en-US / zh-CN
    if "-" in lower or "_" in lower:
        primary = lower.replace("_", "-").split("-", 1)[0]
        if primary in _VALID_TMDB_LANGS:
            return primary
    return None


class MovieService:
    """TMDB 电影查询服务：search / discover / 类型名 id 映射。"""

    def __init__(self, settings: Optional[Settings] = None) -> None:
        """初始化配置、类型缓存占位，以及复用的 httpx 客户端。"""
        self.settings = settings or get_settings()
        self._genre_id_to_name: Optional[Dict[int, str]] = None
        self._genre_name_to_id: Optional[Dict[str, int]] = None
        self._client = httpx.Client(timeout=30.0)

    def close(self) -> None:
        """关闭底层 HTTP 客户端（进程退出或测试 teardown 时调用）。"""
        self._client.close()

    def _auth_headers_and_params(self) -> tuple[dict, dict]:
        """组装鉴权：优先 Bearer Access Token，否则 query 带 api_key。"""
        token, api_key = self.settings.resolve_tmdb_credentials()
        if not token and not api_key:
            raise MovieServiceError(
                "TMDB 未配置：请在 .env 设置 TMDB_ACCESS_TOKEN 或 TMDB_API_KEY",
                status_code=503,
            )

        headers: dict = {"Accept": "application/json"}
        params: dict = {
            "language": self.settings.tmdb_language,
            "include_adult": str(self.settings.tmdb_include_adult).lower(),
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            params["api_key"] = api_key  # type: ignore[assignment]
        return headers, params

    def _get(self, path: str, extra_params: Optional[Dict[str, Any]] = None) -> dict:
        """对 TMDB 发 GET，统一处理超时、网络错误与非 2xx / 非 JSON。"""
        headers, params = self._auth_headers_and_params()
        if extra_params:
            for k, v in extra_params.items():
                if v is not None and v != "":
                    params[k] = v

        url = f"{TMDB_API_BASE}{path}"
        try:
            resp = self._client.get(url, headers=headers, params=params)
        except httpx.TimeoutException as e:
            raise MovieServiceError(f"TMDB 请求超时: {e}") from e
        except httpx.HTTPError as e:
            raise MovieServiceError(f"TMDB 网络错误: {e}") from e

        if resp.status_code == 401:
            raise MovieServiceError(
                "TMDB 鉴权失败：请检查 Access Token / API Key",
                status_code=401,
            )
        if resp.status_code == 404:
            raise MovieServiceError("影片不存在或已下架", status_code=404)
        if resp.status_code >= 400:
            raise MovieServiceError(
                f"TMDB 请求失败: HTTP {resp.status_code}, {resp.text[:200]}"
            )

        try:
            return resp.json()
        except ValueError as e:
            raise MovieServiceError("TMDB 返回非 JSON") from e

    def _poster_url(self, poster_path: Optional[str]) -> Optional[str]:
        """把 TMDB 相对 poster_path 拼成可访问的完整图片 URL。"""
        if not poster_path:
            return None
        base = self.settings.tmdb_image_base_url.rstrip("/")
        return f"{base}{poster_path}"

    def _parse_year(self, release_date: Optional[str]) -> Optional[int]:
        """从 release_date（YYYY-MM-DD）解析上映年份。"""
        if not release_date or len(release_date) < 4:
            return None
        try:
            return int(release_date[:4])
        except ValueError:
            return None

    def ensure_genres(self) -> None:
        """拉取并缓存类型 id ↔ 中文名称（仅首次请求时打 TMDB）。"""
        if self._genre_id_to_name is not None:
            return

        data = self._get("/genre/movie/list")
        id_to_name: Dict[int, str] = {}
        name_to_id: Dict[str, int] = {}
        for g in data.get("genres") or []:
            gid = g.get("id")
            name = (g.get("name") or "").strip()
            if gid is None or not name:
                continue
            id_to_name[int(gid)] = name
            name_to_id[name] = int(gid)
            name_to_id[name.lower()] = int(gid)

        self._genre_id_to_name = id_to_name
        self._genre_name_to_id = name_to_id

    def resolve_genre_ids(self, genres: Optional[str]) -> Optional[str]:
        """将 '剧情,喜剧' 或 '18,35' 转为 TMDB with_genres 所需的 id 串。"""
        if not genres or not genres.strip():
            return None

        self.ensure_genres()
        assert self._genre_name_to_id is not None

        ids: List[str] = []
        for part in genres.split(","):
            raw = part.strip()
            if not raw:
                continue
            if raw.isdigit():
                ids.append(raw)
                continue
            gid = self._genre_name_to_id.get(raw) or self._genre_name_to_id.get(raw.lower())
            if gid is not None:
                ids.append(str(gid))
        return ",".join(ids) if ids else None

    def _map_result(self, item: dict) -> CandidateMovie:
        """把 TMDB 单条原始结果映射为内部 CandidateMovie。"""
        self.ensure_genres()
        assert self._genre_id_to_name is not None

        genre_names: List[str] = []
        for gid in item.get("genre_ids") or []:
            name = self._genre_id_to_name.get(int(gid))
            if name:
                genre_names.append(name)

        title = item.get("title") or item.get("original_title") or ""
        return CandidateMovie(
            id=int(item["id"]),
            title=title,
            year=self._parse_year(item.get("release_date")),
            genres=genre_names,
            runtime=None,  # 列表接口通常无片长，需 detail 才有
            rating=item.get("vote_average"),
            poster_url=self._poster_url(item.get("poster_path")),
            overview=item.get("overview") or "",
        )

    def _map_detail(self, item: dict) -> MovieDetail:
        """把 TMDB /movie/{id}（可含 credits）映射为 MovieDetail。"""
        genre_names: List[str] = []
        for g in item.get("genres") or []:
            name = (g.get("name") or "").strip()
            if name:
                genre_names.append(name)
        if not genre_names and item.get("genre_ids"):
            self.ensure_genres()
            assert self._genre_id_to_name is not None
            for gid in item["genre_ids"]:
                name = self._genre_id_to_name.get(int(gid))
                if name:
                    genre_names.append(name)

        title = item.get("title") or item.get("original_title") or ""
        runtime = item.get("runtime")
        if runtime is not None:
            try:
                runtime = int(runtime)
                if runtime <= 0:
                    runtime = None
            except (TypeError, ValueError):
                runtime = None

        countries: List[str] = []
        for c in item.get("production_countries") or []:
            name = (c.get("name") or "").strip()
            if name:
                countries.append(name)

        directors: List[str] = []
        cast_names: List[str] = []
        credits = item.get("credits") or {}
        for person in credits.get("crew") or []:
            if person.get("job") == "Director":
                name = (person.get("name") or "").strip()
                if name and name not in directors:
                    directors.append(name)
        for person in (credits.get("cast") or [])[:8]:
            name = (person.get("name") or "").strip()
            if name:
                cast_names.append(name)

        movie_id = int(item["id"])
        original_title = (item.get("original_title") or "").strip() or None
        if original_title and original_title == title:
            original_title = None

        vote_count = item.get("vote_count")
        try:
            vote_count = int(vote_count) if vote_count is not None else None
        except (TypeError, ValueError):
            vote_count = None

        return MovieDetail(
            id=movie_id,
            title=title,
            year=self._parse_year(item.get("release_date")),
            genres=genre_names,
            runtime=runtime,
            rating=item.get("vote_average"),
            poster_url=self._poster_url(item.get("poster_path")),
            overview=item.get("overview") or "",
            tagline=(item.get("tagline") or "").strip() or None,
            original_title=original_title,
            vote_count=vote_count,
            original_language=(item.get("original_language") or "").strip() or None,
            countries=countries,
            directors=directors,
            cast=cast_names,
            tmdb_url=f"https://www.themoviedb.org/movie/{movie_id}",
        )

    def get_detail(self, movie_id: int) -> MovieDetail:
        """按 id 取电影详情（含 credits：导演 / 主演）。"""
        if movie_id <= 0:
            raise MovieServiceError("movie_id 必须为正整数", status_code=400)

        data = self._get(
            f"/movie/{movie_id}",
            {"append_to_response": "credits"},
        )
        return self._map_detail(data)

    def search(
        self,
        q: str,
        year: Optional[int] = None,
        page: int = 1,
    ) -> List[CandidateMovie]:
        """按关键词搜索电影（TMDB GET /search/movie）。"""
        query = (q or "").strip()
        if not query:
            raise MovieServiceError("搜索关键词 q 不能为空", status_code=400)

        data = self._get(
            "/search/movie",
            {
                "query": query,
                "year": year,
                "page": page,
            },
        )
        return [self._map_result(item) for item in data.get("results") or []]

    def discover(
        self,
        with_genres: Optional[str] = None,
        year: Optional[int] = None,
        year_gte: Optional[int] = None,
        year_lte: Optional[int] = None,
        max_runtime: Optional[int] = None,
        with_original_language: Optional[str] = None,
        sort_by: str = "popularity.desc",
        page: int = 1,
    ) -> List[CandidateMovie]:
        """按条件发现电影（TMDB GET /discover/movie）。"""
        genre_ids = self.resolve_genre_ids(with_genres)
        lang = normalize_tmdb_language(with_original_language)

        params: Dict[str, Any] = {
            "sort_by": sort_by or "popularity.desc",
            "page": page,
            "with_genres": genre_ids,
            "with_original_language": lang,
        }
        if year is not None:
            params["primary_release_year"] = year
        if year_gte is not None:
            params["primary_release_date.gte"] = f"{year_gte}-01-01"
        if year_lte is not None:
            params["primary_release_date.lte"] = f"{year_lte}-12-31"
        if max_runtime is not None:
            params["with_runtime.lte"] = max_runtime

        if with_original_language and not lang:
            logger.warning(
                "discover 丢弃非法 language=%r",
                with_original_language,
            )
        logger.info(
            "TMDB discover params genres=%r lang=%r year=%s gte=%s lte=%s runtime_lte=%s sort=%s",
            genre_ids,
            lang,
            year,
            year_gte,
            year_lte,
            max_runtime,
            sort_by or "popularity.desc",
        )

        data = self._get("/discover/movie", params)
        return [self._map_result(item) for item in data.get("results") or []]

    def discover_with_relax(
        self,
        with_genres: Optional[str] = None,
        year: Optional[int] = None,
        year_gte: Optional[int] = None,
        year_lte: Optional[int] = None,
        max_runtime: Optional[int] = None,
        with_original_language: Optional[str] = None,
        sort_by: str = "popularity.desc",
        page: int = 1,
        exclude_ids: Optional[List[int]] = None,
    ) -> List[CandidateMovie]:
        """discover；若空结果则逐步放宽：去语言 → 去片长 → 去年代 → 仅类型。"""
        exclude = set(exclude_ids or [])

        attempts: List[Dict[str, Any]] = [
            {
                "with_genres": with_genres,
                "year": year,
                "year_gte": year_gte,
                "year_lte": year_lte,
                "max_runtime": max_runtime,
                "with_original_language": with_original_language,
            },
            {
                "with_genres": with_genres,
                "year": year,
                "year_gte": year_gte,
                "year_lte": year_lte,
                "max_runtime": max_runtime,
                "with_original_language": None,
            },
            {
                "with_genres": with_genres,
                "year": year,
                "year_gte": year_gte,
                "year_lte": year_lte,
                "max_runtime": None,
                "with_original_language": None,
            },
            {
                "with_genres": with_genres,
                "year": None,
                "year_gte": None,
                "year_lte": None,
                "max_runtime": None,
                "with_original_language": None,
            },
        ]

        seen_keys: set = set()
        for i, kwargs in enumerate(attempts):
            key = tuple(sorted((k, repr(v)) for k, v in kwargs.items()))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            movies = self.discover(sort_by=sort_by, page=page, **kwargs)
            kept = [m for m in movies if m.id not in exclude]
            if kept:
                if i > 0:
                    logger.warning(
                        "discover 空结果已放宽(step=%d) -> %d 部 params=%s",
                        i,
                        len(kept),
                        kwargs,
                    )
                return kept
            logger.warning("discover 无结果 step=%d params=%s", i, kwargs)

        return []


_movie_service: Optional[MovieService] = None


def get_movie_service() -> MovieService:
    """获取进程内 MovieService 单例（REST 与 Agent Tool 共用）。"""
    global _movie_service
    if _movie_service is None:
        _movie_service = MovieService()
    return _movie_service
