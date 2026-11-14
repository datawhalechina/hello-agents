# src/agent/common/agent_result.py
from typing import Optional, Annotated
from pydantic import BaseModel, ConfigDict, Field, BeforeValidator


def _parse_float(v):
    """把 akshare 常见脏数值（'-2.04%'、'1,234.5'、'--'）清洗成 float 或 None。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace("%", "").replace(",", "").replace("，", "")
        if s in ("", "-", "--", "—", "N/A", "n/a", "nan", "NaN", "None", "null"):
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return v


# 任意数值字段都可用：遇到脏字符串自动清洗，遇到缺失自动变 None
SafeFloat = Annotated[Optional[float], BeforeValidator(_parse_float)]


class BaseAgentOutput(BaseModel):
    """所有子 Agent 输出结构的共同基类，统一序列化入口。"""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    agent_name: str = Field(default="", description="产生该结果的子 Agent 名称")
    stock_code: str = Field(description="股票代码")
    stock_name: Optional[str] = Field(default=None, description="股票名称")
    errors: list[str] = Field(default_factory=list, description="按维度记录的错误信息")
    fetched_at: Optional[str] = Field(default=None, description="采集时间，ISO 格式")

    def to_json(self, indent: int = 2) -> str:
        """统一序列化入口：全项目只此一处，禁止在业务代码里手工 json.dumps / model_dump_json。"""
        return self.model_dump_json(indent=indent, exclude_none=True)