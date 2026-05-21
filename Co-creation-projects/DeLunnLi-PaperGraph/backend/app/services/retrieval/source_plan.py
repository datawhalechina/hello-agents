from __future__ import annotations


def openalex_publication_year_filter(year_from: int | None, year_to: int | None) -> str | None:
    yf = year_from
    yt = year_to
    if yf is not None:
        try:
            yf_i = int(yf)
        except (TypeError, ValueError):
            yf_i = None
    else:
        yf_i = None
    if yt is not None:
        try:
            yt_i = int(yt)
        except (TypeError, ValueError):
            yt_i = None
    else:
        yt_i = None
    if yf_i is not None and yt_i is not None:
        if yf_i > yt_i:
            yf_i, yt_i = yt_i, yf_i
        if yf_i == yt_i:
            return f"publication_year:{yf_i}"
        return f"publication_year:{yf_i}-{yt_i}"
    if yf_i is not None:
        return f"publication_year:>={yf_i}"
    if yt_i is not None:
        return f"publication_year:<={yt_i}"
    return None
