"""Pydantic 契约（D4）— 前后端对齐的请求/响应模型。"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ============ 枚举字面量（与前端表单对齐） ============

Mood = Literal["放松", "欢乐", "虐心", "烧脑", "紧张刺激", "温馨"]
PartyType = Literal["独自", "情侣", "家庭", "朋友"]
RegionPreference = Literal["华语", "好莱坞", "日韩", "欧洲", "不限"]
YearPreference = Literal["不限", "近5年", "近10年", "经典"]


# ============ 请求模型 ============


class RecommendRequest(BaseModel):
    """观影偏好 / 智能推荐请求（F1）"""

    mood: Mood = Field(..., description="当前心情")
    party_type: PartyType = Field(..., description="观影人群")
    genres: List[str] = Field(default_factory=list, description="偏好类型标签")
    max_runtime_minutes: Optional[int] = Field(
        default=None,
        description="最大时长（分钟）；null=不限",
        examples=[120],
    )
    region_preference: RegionPreference = Field(default="不限", description="地区偏好")
    year_preference: YearPreference = Field(default="不限", description="年代偏好")
    exclude_titles: List[str] = Field(default_factory=list, description="已看过片名")
    spoilers_ok: bool = Field(default=False, description="是否允许剧透")
    free_text: str = Field(default="", description="额外自由文本要求")
    exclude_ids: List[int] = Field(
        default_factory=list,
        description="换一批时排除的 TMDB 电影 id",
    )
    taste_profile: Optional["TasteProfile"] = Field(
        default=None,
        description="若传入则跳过画像 Agent（换一批复用）",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "mood": "放松",
                "party_type": "独自",
                "genres": ["剧情", "喜剧"],
                "max_runtime_minutes": 120,
                "region_preference": "不限",
                "year_preference": "近10年",
                "exclude_titles": [],
                "spoilers_ok": False,
                "free_text": "不要太沉重",
                "exclude_ids": [],
            }
        }
    }


# ============ 领域子模型 ============


class TasteProfile(BaseModel):
    """画像 Agent 结构化输出（内部契约，后续 Agent 使用）"""

    summary: str = Field(default="", description="口味摘要")
    genre_hints: List[str] = Field(default_factory=list, description="类型倾向")
    language_hints: List[str] = Field(default_factory=list, description="语言/地区倾向")
    avoid: List[str] = Field(default_factory=list, description="禁忌/规避项")
    discover_notes: str = Field(default="", description="discover 友好检索条件说明")


class CandidateMovie(BaseModel):
    """检索 Agent / MovieService 候选片"""

    id: int = Field(..., description="TMDB movie id")
    title: str
    year: Optional[int] = None
    genres: List[str] = Field(default_factory=list)
    runtime: Optional[int] = Field(default=None, description="片长（分钟）")
    rating: Optional[float] = None
    poster_url: Optional[str] = None
    overview: Optional[str] = None


class MovieDetail(CandidateMovie):
    """电影详情（TMDB /movie/{id} + credits）"""

    tagline: Optional[str] = None
    original_title: Optional[str] = None
    vote_count: Optional[int] = None
    original_language: Optional[str] = None
    countries: List[str] = Field(default_factory=list)
    directors: List[str] = Field(default_factory=list)
    cast: List[str] = Field(default_factory=list)
    tmdb_url: Optional[str] = None


class MovieCard(BaseModel):
    """推荐结果卡片（F2 / F3）"""

    id: int = Field(..., description="TMDB movie id")
    title: str
    year: Optional[int] = None
    genres: List[str] = Field(default_factory=list)
    runtime: Optional[int] = None
    rating: Optional[float] = None
    poster_url: Optional[str] = None
    why: str = Field(default="", description="推荐理由")
    vibe_tags: List[str] = Field(default_factory=list)
    caution: Optional[str] = Field(default=None, description="适看提示")
    overview_safe: str = Field(default="", description="安全简介（遵守 spoilers_ok）")


class RecommendResult(BaseModel):
    """推荐结果主体"""

    playlist_name: str = ""
    profile_summary: str = ""
    movies: List[MovieCard] = Field(default_factory=list)
    is_fallback: bool = Field(default=False, description="是否为降级结果（D5）")
    taste_profile: Optional[TasteProfile] = Field(
        default=None,
        description="本次使用的画像；换一批时可原样回传以跳过画像 Agent",
    )

# ============ 响应包装 ============


class RecommendResponse(BaseModel):
    success: bool
    message: str = ""
    data: Optional[RecommendResult] = None


class MovieListResponse(BaseModel):
    """确定性搜片列表响应（search / discover）"""

    success: bool
    message: str = ""
    data: List[CandidateMovie] = Field(default_factory=list)


class MovieDetailResponse(BaseModel):
    """电影详情响应"""

    success: bool
    message: str = ""
    data: Optional[MovieDetail] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: Optional[str] = None


RecommendRequest.model_rebuild()
RecommendResult.model_rebuild()
