import logging
import os
import time

from fastapi import BackgroundTasks, HTTPException, Request

from ...settings import get_settings
from ...models.schemas import (
    DeletePaperResponse,
    LibraryCategoriesResponse,
    LibraryCategoryFolder,
    Paper,
    PapersResponse,
    SavePapersRequest,
    SavePapersResponse,
    UpdatePaperRequest,
    UpdatePaperResponse,
)

logger = logging.getLogger(__name__)

def _merge_tag_lists(base: list[str], extra: list[str], max_n: int = 24) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in (base or []) + (extra or []):
        k = (t or "").strip()
        if not k:
            continue
        low = k.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(k)
        if len(out) >= max_n:
            break
    return out

def list_library_categories(*, db) -> LibraryCategoriesResponse:
    try:
        from app.core.paper_paths import LIBRARY_PDF_ROOT_DIR

        items = db.list_library_category_folders()
        return LibraryCategoriesResponse(
            success=True,
            store_root=LIBRARY_PDF_ROOT_DIR,
            folders=[LibraryCategoryFolder(**x) for x in items],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_library(
    *,
    db,
    litpaper_to_api_paper_fn,
    limit: int = 50,
    offset: int = 0,
    q: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    read_status=None,
    tags: str | None = None,
    category: str | None = None,
) -> PapersResponse:
    try:

        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        cat = (category or "").strip() or None
        if q or year_from or year_to or read_status or tag_list or cat:
            papers_data = db.search_library(
                query=q,
                tags=tag_list,
                year_from=year_from,
                year_to=year_to,
                read_status=read_status.value if read_status else None,
                category=cat,
                limit=limit,
                offset=offset,
            )
        else:
            papers_data = db.get_all_papers(limit=limit, offset=offset, order_by="created_at DESC")

        ids_missing_pdf = [
            int(p.id)
            for p in papers_data
            if p.id is not None and not (getattr(p, "local_pdf_path", None) or "").strip()
        ]
        if ids_missing_pdf:
            repaired = db.repair_library_local_pdf_paths_batch(ids_missing_pdf)
            for p in papers_data:
                if p.id is not None and int(p.id) in repaired:
                    p.local_pdf_path = repaired[int(p.id)]

        total = db.count_papers() if not (q or year_from or year_to or read_status or tag_list or cat) else len(papers_data) + (1 if len(papers_data) >= limit else 0)
        papers = [litpaper_to_api_paper_fn(p) for p in papers_data]
        return PapersResponse(success=True, total=total or len(papers), papers=papers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def save_papers(
    *,
    db,
    request: SavePapersRequest,
    background_tasks: BackgroundTasks,
    api_to_lit_fn,
    litpaper_to_api_paper_fn,
) -> SavePapersResponse:
    try:
        t0 = time.perf_counter()
        from ..graph.kg_relations import build_relations_for_new_paper
        from app.core.paper_paths import (
            LIBRARY_PDF_ROOT_DIR,
            library_pdf_relative_path,
            normalize_library_category_display,
        )
        from app.core.pdf_download import download_paper_pdf_to_path, resolve_paper_pdf_url

        lit_list = [api_to_lit_fn(p) for p in request.papers]
        for api_p, lit_p in zip(request.papers, lit_list):
            if (api_p.source_url or "").strip():
                lit_p.source_url = (api_p.source_url or "").strip()
            if (api_p.pdf_url or "").strip():
                lit_p.pdf_url = (api_p.pdf_url or "").strip()
            if (api_p.doi or "").strip():
                lit_p.doi = (api_p.doi or "").strip()
            if (api_p.arxiv_id or "").strip():
                lit_p.arxiv_id = (api_p.arxiv_id or "").strip()
            # Fill missing arXiv ID from DOI/source URL.
            if not (getattr(lit_p, "arxiv_id", None) or "").strip():
                import re
                for field_val in ((api_p.doi or "").strip(), (api_p.source_url or "").strip()):
                    m = re.search(r"arxiv/([\d.]+)", field_val, re.I)
                    if m:
                        lit_p.arxiv_id = m.group(1)
                        break
            # Infer venue type from journal name when absent.
            if not (getattr(lit_p, "venue_type", None) or "").strip():
                j = (getattr(lit_p, "journal", None) or "").strip()
                if j:
                    import re
                    if re.search(r"(?i)\b(journal|transactions|letters|magazine|review|annals|acta|bulletin)\b", j):
                        lit_p.venue_type = "journal"
                    else:
                        lit_p.venue_type = "conference"

            # Fill missing DOI from source URL.
            if not (getattr(lit_p, "doi", None) or "").strip():
                su = (api_p.source_url or "").strip()
                import re
                m = re.search(r"doi\.org/(10\.\S+)", su, re.I)
                if m:
                    lit_p.doi = m.group(1)

            if (api_p.category or "").strip():
                lit_p.category = normalize_library_category_display(api_p.category)

        llm_classified = 0

        if lit_list and getattr(request, "llm_classify", True):
            try:
                existing_categories = []
                try:
                    existing_categories = db.list_library_categories_by_count(limit=80)
                except Exception:
                    existing_categories = []

                from ...agents import get_paper_analysis_agent

                agent = get_paper_analysis_agent()
                for lit_p in lit_list:
                    cat, extra = agent.classify_for_library(
                        lit_p.title,
                        lit_p.abstract,
                        lit_p.journal,
                        getattr(lit_p, "keywords", None) or [],
                        existing_categories=existing_categories,
                    )
                    lit_p.category = cat
                    lit_p.tags = _merge_tag_lists(lit_p.tags or [], extra)
                    if not getattr(lit_p, "venue_type", None):
                        lit_p.venue_type = agent.classify_venue_type(lit_p.journal)
                    llm_classified += 1
            except Exception as e:
                logger.warning("大模型归类未执行：%s", e)
                for lit_p in lit_list:
                    lit_p.category = normalize_library_category_display(getattr(lit_p, "category", None))
        elif lit_list:

            for lit_p in lit_list:
                lit_p.category = normalize_library_category_display(getattr(lit_p, "category", None))

        for lit_p in lit_list:
            lit_p.category = normalize_library_category_display(getattr(lit_p, "category", None))

        t_after_classify = time.perf_counter()

        # Backfill missing abstracts via Tavily.
        for lit_p in lit_list:
            if not (lit_p.abstract or "").strip() and lit_p.title:
                try:
                    from ...settings import get_settings as _gs
                    _ak = getattr(_gs(), "tavily_api_key", "").strip()
                    if _ak:
                        import httpx
                        _resp = httpx.post("https://api.tavily.com/search", json={
                            "api_key": _ak, "query": f"{lit_p.title} paper abstract", "max_results": 3}, timeout=15.0)
                        for _it in (_resp.json().get("results") or []):
                            if len(_it.get("content","")) > 100:
                                lit_p.abstract = _it["content"][:2000]
                                break
                except Exception: pass

        ids, added_new, updated_existing = db.add_papers(lit_list)
        t_after_db = time.perf_counter()

        t_after_memory = time.perf_counter()

        for pid in ids or []:
            try:
                if pid is None or int(pid) <= 0:
                    continue
                build_relations_for_new_paper(db.db_path, int(pid))
            except Exception:
                continue

        pdf_downloaded = 0
        if request.download_pdfs and lit_list and ids:
            s = get_settings()
            mail = (s.ncbi_email or "").strip()
            data_root = os.path.dirname(os.path.abspath(db.db_path))
            os.makedirs(os.path.join(data_root, LIBRARY_PDF_ROOT_DIR), exist_ok=True)
            for lit_p, pid in zip(lit_list, ids):
                if pid is None or pid < 0:
                    continue
                relpath = library_pdf_relative_path(
                    getattr(lit_p, "category", None), int(pid), getattr(lit_p, "title", None)
                )
                dest = os.path.join(data_root, relpath)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                try:
                    resolved = resolve_paper_pdf_url(lit_p, email=mail)
                except Exception as ex:
                    logger.warning("解析 PDF 链接异常（已跳过该条 PDF）: %s", ex, exc_info=True)
                    resolved = None
                if not resolved:
                    logger.warning(
                        "保存跳过 PDF：无可用链接 title=%r doi=%r",
                        lit_p.title,
                        lit_p.doi,
                    )
                if os.path.isfile(dest) and os.path.getsize(dest) >= 256:
                    db.set_local_pdf_path(int(pid), relpath)
                    pdf_downloaded += 1
                    continue
                if resolved and download_paper_pdf_to_path(lit_p, dest, email=mail):
                    db.set_local_pdf_path(int(pid), relpath)
                    pdf_downloaded += 1
                elif resolved:
                    logger.warning("保存 PDF 下载失败 title=%r", lit_p.title)
        t_after_pdf = time.perf_counter()

        ids_ok = [int(x) for x in ids if x is not None and int(x) >= 0]
        if ids_ok:
            need_repair = []
            for pid in ids_ok:
                row = db.get_paper_by_id(pid)
                if row and not (getattr(row, "local_pdf_path", None) or "").strip():
                    need_repair.append(pid)
            if need_repair:
                db.repair_library_local_pdf_paths_batch(need_repair)

        msg = None
        if (
            request.download_pdfs
            and lit_list
            and pdf_downloaded == 0
            and any(pid is not None and pid >= 0 for pid in ids)
        ):
            msg = "未能写入本地 PDF：请确认含 arXiv / pdf_url 等可下载链接。"

        logger.info(
            "POST /api/papers/save timing total=%.3fs classify=%.3fs db=%.3fs memory=%.3fs pdf=%.3fs"
            " papers=%d llm_classify=%s download_pdfs=%s",
            (t_after_pdf - t0),
            (t_after_classify - t0),
            (t_after_db - t_after_classify),
            (t_after_memory - t_after_db),
            (t_after_pdf - t_after_memory),
            len(lit_list),
            getattr(request, "llm_classify", True),
            getattr(request, "download_pdfs", False),
        )

        return SavePapersResponse(
            success=True,
            added=int(added_new),
            updated=int(updated_existing),
            ids=ids,
            pdf_downloaded=pdf_downloaded,
            llm_classified=llm_classified,
            message=msg,
        )
    except Exception as e:
        logger.exception("POST /api/papers/save 失败")
        raise HTTPException(status_code=500, detail=str(e))

def get_paper_by_id(*, db, paper_id: int, litpaper_to_api_paper_fn) -> Paper:
    p = db.get_paper_by_id(paper_id)
    if not p:
        raise HTTPException(status_code=404, detail="文献不存在")

    if p.id is not None and not (getattr(p, "local_pdf_path", None) or "").strip():
        repaired = db.repair_library_local_pdf_paths_batch([int(p.id)])
        if repaired:
            p2 = db.get_paper_by_id(paper_id)
            if p2:
                p = p2
    return litpaper_to_api_paper_fn(p)

def update_paper_by_id(*, db, paper_id: int, body: UpdatePaperRequest) -> UpdatePaperResponse:
    try:
        from app.core.paper_paths import normalize_library_category_display

        fields = {}
        if body.notes is not None:
            fields["notes"] = body.notes
        if body.tags is not None:
            fields["tags"] = body.tags
        if body.category is not None:
            fields["category"] = normalize_library_category_display(body.category)
        if body.rating is not None:
            fields["rating"] = body.rating
        if body.read_status is not None:
            fields["read_status"] = body.read_status.value
        if body.importance is not None:
            fields["importance"] = body.importance
        ok = db.update_paper(paper_id, **fields)
        if not ok:
            raise HTTPException(status_code=404, detail="未更新或文献不存在")
        return UpdatePaperResponse(success=True, updated_fields=list(fields.keys()))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def delete_paper_by_id(*, db, paper_id: int) -> DeletePaperResponse:
    ok = db.delete_paper(paper_id)
    if not ok:
        raise HTTPException(status_code=404, detail="文献不存在")
    return DeletePaperResponse(success=True, message="已删除")

def build_library_pdf_response_service(*, paper_id: int, request: Request, db_path: str, logger_obj):
    from ..pdf.pdf_service import build_library_pdf_response

    return build_library_pdf_response(
        paper_id=int(paper_id),
        request=request,
        db_path=db_path,
        logger=logger_obj,
    )
