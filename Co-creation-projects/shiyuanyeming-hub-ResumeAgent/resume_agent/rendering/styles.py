"""Validated visual themes migrated from the ResumeAgent notebook."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StyleTheme:
    accent: str
    secondary: str
    tint: str
    border: str
    font_family: str


STYLE_CATALOG: dict[str, dict[str, StyleTheme]] = {
    "zh": {
        "藏青现代": StyleTheme(
            accent="#1F4E79",
            secondary="#4A6785",
            tint="#EDF2F8",
            border="#B8CCE4",
            font_family='"PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", sans-serif',
        ),
        "经典墨色": StyleTheme(
            accent="#222222",
            secondary="#555555",
            tint="#F2F2F2",
            border="#BBBBBB",
            font_family='"Songti SC", "STSong", "PingFang SC", serif',
        ),
        "清新青碧": StyleTheme(
            accent="#0F766E",
            secondary="#3E6E68",
            tint="#E1F5EE",
            border="#9BD8CB",
            font_family='"PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", sans-serif',
        ),
    },
    "en": {
        "青灰Teal": StyleTheme(
            accent="#0F4C5C",
            secondary="#52666B",
            tint="#EEF6F7",
            border="#A9C9CF",
            font_family='"Helvetica Neue", Arial, sans-serif',
        ),
        "经典黑白": StyleTheme(
            accent="#111111",
            secondary="#555555",
            tint="#F5F5F5",
            border="#BBBBBB",
            font_family='"Helvetica Neue", Arial, sans-serif',
        ),
        "现代蓝": StyleTheme(
            accent="#1D4ED8",
            secondary="#4B638A",
            tint="#EFF4FF",
            border="#AFC5F5",
            font_family='"Helvetica Neue", Arial, sans-serif',
        ),
    },
    "ja": {
        "藏青JIS": StyleTheme(
            accent="#223A5E",
            secondary="#52647E",
            tint="#EDF1F6",
            border="#ABB8CA",
            font_family='"Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", sans-serif',
        ),
        "墨黑JIS": StyleTheme(
            accent="#111111",
            secondary="#555555",
            tint="#F5F5F5",
            border="#BBBBBB",
            font_family='"Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", sans-serif',
        ),
        "蓝灰JIS": StyleTheme(
            accent="#3A5F7A",
            secondary="#60798A",
            tint="#EEF2F6",
            border="#B2C1CC",
            font_family='"Hiragino Kaku Gothic ProN", "Noto Sans CJK JP", sans-serif',
        ),
    },
}


DEFAULT_STYLES = {
    "zh": "藏青现代",
    "en": "青灰Teal",
    "ja": "藏青JIS",
}


def default_style(locale: str) -> str:
    try:
        return DEFAULT_STYLES[locale]
    except KeyError as error:
        raise ValueError(f"unsupported locale: {locale}") from error


def get_theme(locale: str, style: str) -> StyleTheme:
    if locale not in STYLE_CATALOG:
        raise ValueError(f"unsupported locale: {locale}")
    try:
        return STYLE_CATALOG[locale][style]
    except KeyError as error:
        raise ValueError(f"unsupported style for {locale}: {style}") from error
