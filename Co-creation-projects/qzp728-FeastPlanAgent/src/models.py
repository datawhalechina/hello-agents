"""Typed input models for a banquet-planning request."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Any


@dataclass
class Guest:
    name: str
    role: str
    notes: str = ""
    must_with: list[str] = field(default_factory=list)
    avoid_with: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Guest":
        return cls(
            name=str(data["name"]),
            role=str(data.get("role", "普通宾客")),
            notes=str(data.get("notes", "")),
            must_with=list(data.get("must_with", [])),
            avoid_with=list(data.get("avoid_with", [])),
        )


@dataclass
class BanquetRequest:
    city: str
    banquet_type: str
    guest_count: int
    seats_per_table: int
    budget: int
    regional_preference: str
    guests: list[Guest]
    dietary_constraints: list[str] = field(default_factory=list)
    seat_overrides: dict[str, str] = field(default_factory=dict)
    date: str = "待定"
    venue_keyword: str = ""

    @property
    def table_count(self) -> int:
        return ceil(self.guest_count / self.seats_per_table)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BanquetRequest":
        request = cls(
            city=str(data["city"]),
            banquet_type=str(data["banquet_type"]),
            guest_count=int(data["guest_count"]),
            seats_per_table=int(data["seats_per_table"]),
            budget=int(data["budget"]),
            regional_preference=str(data.get("regional_preference", data["city"])),
            guests=[Guest.from_dict(item) for item in data.get("guests", [])],
            dietary_constraints=list(data.get("dietary_constraints", [])),
            seat_overrides=dict(data.get("seat_overrides", {})),
            date=str(data.get("date", "待定")),
            venue_keyword=str(data.get("venue_keyword", "")),
        )
        request.validate()
        return request

    def validate(self) -> None:
        if self.guest_count <= 0 or self.seats_per_table <= 1:
            raise ValueError("宾客人数必须大于 0，且每桌人数至少为 2。")
        if self.budget <= 0:
            raise ValueError("总预算必须大于 0。")
        if len(self.guests) != self.guest_count:
            raise ValueError(
                f"guest_count 为 {self.guest_count}，但 guests 中有 {len(self.guests)} 人；请保持一致。"
            )
        names = [guest.name for guest in self.guests]
        if len(names) != len(set(names)):
            raise ValueError("宾客姓名不能重复，请用备注区分同名宾客。")
        unknown = set(self.seat_overrides.values()) - set(names)
        if unknown:
            raise ValueError(f"seat_overrides 中有不在宾客名单中的姓名：{', '.join(sorted(unknown))}")
        if len(set(self.seat_overrides.values())) != len(self.seat_overrides):
            raise ValueError("同一位宾客不能同时被指定为多个核心座位。")
