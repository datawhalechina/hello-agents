"""
文件管理 + RAG 上传 REST API
"""
import os
import datetime
import uuid

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from tool.config_handler import Rag_Config
from tool.file_handler import get_supported_extensions
from tool.logger_handler import logger
from tool.path_tool import get_project_root
from vector_uploader_service.file_record import list_all_files, get_all_records, remove_records_by_file

router = APIRouter()

# 上传目录固定锚定到项目根，确保与 file_manage 沙箱（config/FileManageConfig.yml allowed_paths）一致，
# 避免服务器从非项目根 CWD 启动时上传落在沙箱外、Agent 无法访问。
UPLOAD_DIR = os.path.join(get_project_root(), "uploads")

# 聊天附件大小上限：≥10MB 直接拒绝（与前端一致）
CHAT_UPLOAD_MAX = 10 * 1024 * 1024


@router.get("/files/rag-files")
async def api_list_rag_files():
    """列出已上传到知识库的文件"""
    records = get_all_records()
    # 按文件名聚合
    files_map: dict[str, dict] = {}
    for r in records:
        fname = r.get("file_name", "unknown")
        if fname not in files_map:
            files_map[fname] = {
                "file_name": fname,
                "file_path": r.get("file_path", ""),
                "collection_name": r.get("collection_name", ""),
                "chunk_count": len(r.get("chroma_ids", [])),
                "uploaded_at": r.get("timestamp", ""),
                "chroma_ids": r.get("chroma_ids", []),
            }
        else:
            files_map[fname]["chunk_count"] += len(r.get("chroma_ids", []))
            # 取最新时间戳
            if r.get("timestamp", "") > files_map[fname]["uploaded_at"]:
                files_map[fname]["uploaded_at"] = r.get("timestamp", "")

    return {"files": list(files_map.values()), "total": len(files_map)}


@router.post("/files/upload")
async def api_upload_file(file: UploadFile = File(...)):
    """上传文件到 RAG 知识库"""
    # 验证文件类型（从 Rag_Config.support_extensions 派生）
    allowed_exts = tuple(get_supported_extensions())
    if not file.filename or not file.filename.lower().endswith(allowed_exts):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。仅允许: {', '.join(allowed_exts)}"
        )

    # 保存上传文件
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_name = os.path.basename(file.filename)
    dest_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(dest_path, "wb") as f:
        f.write(content)

    # 上传到 Chroma
    try:
        from vector_uploader_service.file_uploader import File_Uploader
        uploader = File_Uploader()
        result = uploader.file_upload(dest_path)
        logger.info(f"[files] 已上传到 RAG: {safe_name}, chunks={result}")
        return {
            "file_name": safe_name,
            "status": "uploaded",
            "chunks": result if isinstance(result, int) else 0,
        }
    except Exception as e:
        logger.exception(f"[files] RAG 上传失败: {safe_name}")
        raise HTTPException(status_code=500, detail=f"RAG 上传失败: {str(e)}")


@router.post("/files/chat-upload")
async def api_chat_upload_file(file: UploadFile = File(...)):
    """上传聊天附件到沙箱（uploads/），存为副本，不进入 RAG。

    返回 {file_name, path, size}，其中 path 为项目根相对路径（如 uploads/foo.txt），
    必在 file_manage 沙箱内，可直接供 Agent 用 file_manage 读取/修改。
    """
    # 验证文件类型（与 RAG 上传一致，从 Rag_Config.support_extensions 派生）
    allowed_exts = tuple(get_supported_extensions())
    if not file.filename or not file.filename.lower().endswith(allowed_exts):
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。仅允许: {', '.join(allowed_exts)}"
        )

    content = await file.read()
    # ≥10MB 拒绝，与前端一致（用 >= 保证恰好 10MB 也被拒）
    if len(content) >= CHAT_UPLOAD_MAX:
        raise HTTPException(status_code=400, detail="文件大小超过 10MB 上限")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    original_name = os.path.basename(file.filename)
    safe_name = original_name
    # 防同名覆盖（uploads/ 同时被 RAG 与聊天附件使用）
    while os.path.exists(os.path.join(UPLOAD_DIR, safe_name)):
        stem, ext = os.path.splitext(original_name)
        safe_name = f"{stem}_{uuid.uuid4().hex[:8]}{ext}"
    dest_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(dest_path, "wb") as f:
        f.write(content)

    logger.info(f"[files] 聊天附件已存盘: {safe_name}, size={len(content)}")
    # path 固定 uploads/ 前缀 + 前斜杠，保证沙箱校验通过
    return {"file_name": original_name, "path": f"uploads/{safe_name}", "size": len(content)}


@router.delete("/files/rag-files/{file_name}")
async def api_delete_rag_file(file_name: str):
    """从知识库中移除文件记录"""
    records = get_all_records()
    removed = 0
    for r in records:
        if r.get("file_name") == file_name:
            remove_records_by_file(r.get("file_path", ""))
            removed += 1

    if removed == 0:
        raise HTTPException(status_code=404, detail=f"未找到文件 '{file_name}'")

    return {"deleted": file_name, "records_removed": removed}


@router.get("/files/rag-status")
async def api_rag_status():
    """RAG 知识库统计"""
    records = get_all_records()
    files = set()
    total_chunks = 0
    for r in records:
        files.add(r.get("file_name", ""))
        total_chunks += len(r.get("chroma_ids", []))

    # 尝试获取 Chroma collection 大小
    try:
        from vector_uploader_service.file_uploader import File_Uploader
        uploader = File_Uploader()
        chroma_data = uploader.chroma.get(include=[])
        vector_count = len(chroma_data.get("ids", []))
    except Exception:
        vector_count = total_chunks

    return {
        "file_count": len(files),
        "total_chunks": total_chunks,
        "vector_count": vector_count,
        "collection_name": Rag_Config.get("collection_name", "knowledge_base"),
        "supported_extensions": get_supported_extensions(),
    }
