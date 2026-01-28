from pydantic import BaseModel, Field
from typing import List

class Location(BaseModel):
    """地理位置模型"""
    lat: float = Field(..., description="纬度")
    lng: float = Field(..., description="经度")


class Attraction(BaseModel):
    """
    景点信息模型（核心模型）

    - 必须字段：景点名称、类型、评分、建议游玩时间、描述、地址、经纬度、景点图片 URL 列表、门票价格
    """
    name: str = Field(..., description="景点名称")
    type: str = Field("", description="景点类型，例如：历史文化、公园、博物馆等")
    rating: float | str = Field("N/A", description="评分")
    suggested_duration_hours: float | None = Field(
        default=None,
        description="建议游玩时长（单位：小时，例如 2.5 表示约 2.5 小时）",
    )
    description: str = Field("", description="景点描述 / 简介")
    address: str = Field("", description="地址")
    location: Location | None = Field(default=None, description="地理位置坐标")
    image_urls: List[str] = Field(
        default_factory=list,
        description="景点图片 URL 列表（只允许景点图片）",
    )
    ticket_price: float | str = Field(
        "N/A",
        description="景点门票价格（数值或字符串，如“免费”、“100 元”）",
    )


class Hotel(BaseModel):
    """酒店信息模型"""
    name: str = Field(..., description="酒店名称")
    address: str = Field("", description="地址")
    location: Location | None = Field(default=None, description="地理位置坐标")
    price: float | str = Field("N/A", description="价格")
    rating: float | str = Field("N/A", description="评分")
    distance_to_main_attraction_km: float | None = Field(
        default=None,
        description="距离主要景点的距离（单位：公里），用于推荐离景点更近的酒店",
    )

class Dining(BaseModel):
    """餐饮信息模型"""
    name: str = Field(..., description="餐厅名称")
    address: str = Field("", description="地址")
    location: Location | None = None
    cost_per_person: float | str = Field("N/A", description="人均消费")
    rating: float | str = Field("N/A", description="评分")

class Weather(BaseModel):
    """天气信息模型"""
    date: str = Field(..., description="日期")
    day_weather: str = Field(..., description="白天天气现象")
    night_weather: str = Field(..., description="夜间天气现象")
    day_temp: str = Field(..., description="白天温度（数值字符串，例如 25）")
    night_temp: str = Field(..., description="夜间温度（数值字符串，例如 15）")
    day_wind: str | None = Field(
        default=None, description="白天风向与风力描述，例如 东风3级"
    )
    night_wind: str | None = Field(
        default=None, description="夜间风向与风力描述，例如 西北风2级"
    )