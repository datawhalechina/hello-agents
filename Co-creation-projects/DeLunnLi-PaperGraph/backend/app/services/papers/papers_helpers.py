from typing import Any

from ...utils import normalize_arxiv_id

def daily_paper_identity_sig(p: Any) -> str:
    ax = normalize_arxiv_id(getattr(p, "arxiv_id", None))
    if ax:
        return f"arxiv:{ax}"
    doi = (getattr(p, "doi", None) or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    t = (getattr(p, "title", None) or "").strip().lower()
    y = int(getattr(p, "year", 0) or 0)
    return f"ty:{t}|{y}"

def graph_author_node_id(paper_id: int, author_index: int, author: Any) -> str:
    raw_orcid = getattr(author, "orcid", None)
    orc = None
    if raw_orcid:
        s = str(raw_orcid).strip().lower()
        for prefix in ("https://orcid.org/", "http://orcid.org/"):
            if s.startswith(prefix):
                s = s[len(prefix):]
        s = s.strip().rstrip("/")
        if len(s) >= 10:
            orc = s
    if orc:
        return f"author:o:{orc}"
    try:
        aid = getattr(author, "db_id", None)
        if aid is not None and int(aid) > 0:
            return f"author:db:{int(aid)}"
    except Exception:
        pass
    return f"author:p:{int(paper_id)}:{int(author_index)}"

def graph_author_label(author: Any, author_index: int, node_id: str) -> str:
    name = (getattr(author, "name", None) or "").strip() or "Unknown"
    if not str(node_id).startswith("author:p:"):
        return name[:120]
    aff = (getattr(author, "affiliation", None) or "").strip()
    if aff:
        short = aff[:26] + ("…" if len(aff) > 26 else "")
        return f"{name[:80]} ({short})"
    return f"{name[:80]} (#{author_index + 1})"
