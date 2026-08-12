"""确定性搜片路由（D1）：不经过 LLM，直接走 MovieService → TMDB。"""

from typing import Optional

from fastapi import APIRouter, Path, Query

from ...models.schemas import MovieDetailResponse, MovieListResponse
from ...services.movie_service import get_movie_service
from ...utils.logger import get_logger

router = APIRouter(prefix="/movies", tags=["Movies"])
logger = get_logger("app.movies")


@router.get(
    "/search",
    response_model=MovieListResponse,
    summary="文本搜索电影",
    description="对应 TMDB `GET /search/movie`，参数 `q` 必填。",
)
async def search_movies(
    q: str = Query(..., min_length=1, description="搜索关键词", examples=["盗梦空间"]),
    year: Optional[int] = Query(default=None, description="上映年份"),
    page: int = Query(default=1, ge=1, le=500, description="页码"),
):
    movies = get_movie_service().search(q=q, year=year, page=page)
    logger.info("search q=%r year=%s -> %d", q, year, len(movies))
    return MovieListResponse(
        success=True,
        message=f"搜索成功，共 {len(movies)} 条",
        data=movies,
    )


@router.get(
    "/discover",
    response_model=MovieListResponse,
    summary="条件发现电影",
    description="对应 TMDB `GET /discover/movie`；`with_genres` 支持中文类型名或 id。",
)
async def discover_movies(
    with_genres: Optional[str] = Query(
        default=None,
        description="类型：名称或 id，逗号分隔，如 剧情,喜剧 或 18,35",
        examples=["科幻"],
    ),
    year: Optional[int] = Query(default=None, description="精确上映年"),
    year_gte: Optional[int] = Query(default=None, description="上映年起"),
    year_lte: Optional[int] = Query(default=None, description="上映年止"),
    max_runtime: Optional[int] = Query(
        default=None,
        ge=1,
        description="最大片长（分钟）→ with_runtime.lte",
    ),
    with_original_language: Optional[str] = Query(
        default=None,
        description="原始语言，如 zh / en / ja / ko",
    ),
    sort_by: str = Query(default="popularity.desc", description="排序字段"),
    page: int = Query(default=1, ge=1, le=500, description="页码"),
):
    movies = get_movie_service().discover(
        with_genres=with_genres,
        year=year,
        year_gte=year_gte,
        year_lte=year_lte,
        max_runtime=max_runtime,
        with_original_language=with_original_language,
        sort_by=sort_by,
        page=page,
    )
    logger.info("discover genres=%r -> %d", with_genres, len(movies))
    return MovieListResponse(
        success=True,
        message=f"发现成功，共 {len(movies)} 条",
        data=movies,
    )


@router.get(
    "/{movie_id}",
    response_model=MovieDetailResponse,
    summary="电影详情",
    description="对应 TMDB `GET /movie/{movie_id}`，补全片长 runtime 等详情字段。",
)
async def get_movie_detail(
    movie_id: int = Path(..., ge=1, description="TMDB 电影 id", examples=[550]),
):
    movie = get_movie_service().get_detail(movie_id)
    logger.info("detail id=%s title=%r runtime=%s", movie_id, movie.title, movie.runtime)
    return MovieDetailResponse(
        success=True,
        message="查询成功",
        data=movie,
    )
