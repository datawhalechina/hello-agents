import os
import hashlib
from typing import List
from tool.logger_handler import logger
from tool.config_handler import Rag_Config
from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
def get_file_md5_hex(abs_path:str):
    if not os.path.exists(abs_path):
        logger.error("未找到文件路径")
    if not os.path.isfile(abs_path):
        logger.error("所提供路径对应并非文件")

    hash_obj=hashlib.md5()
    
    chunk_size=4096
    try:    
        with open(abs_path,'rb') as f:
            chunk=f.read(chunk_size)
            while chunk:
                hash_obj.update(chunk)
                chunk=f.read(chunk_size)
            return hash_obj.hexdigest()
    except Exception as e:
        logger.exception(f'md5过程出错{str(e)}')

def listdir_readable_file(abs_path:str,type:tuple[str]):
    """
    列出当前目录中可读文件
    """
    files=[]

    if not os.path.isdir(abs_path):
        logger.error('提供路径对应不是目录')
    
    for f in os.listdir(abs_path):
        if f.endswith(type):
            files.append(os.path.join(abs_path,f))

    if not files:
        logger.warning('无可读文件')

    return files

def get_supported_extensions() -> list[str]:
    """
    从 Rag_Config 读取知识库支持的上传扩展名（单一来源）。
    规范化为「小写 + 带点」形式并去重；配置缺失时回退到 .txt/.pdf。
    """
    raw = Rag_Config.get("support_extensions", [".txt", ".pdf"])
    seen: set[str] = set()
    result: list[str] = []
    for e in raw:
        e = str(e).strip().lower()
        if not e.startswith("."):
            e = "." + e
        if e not in seen:
            seen.add(e)
            result.append(e)
    return result


def is_supported_extension(abs_path: str) -> bool:
    """判断文件扩展名（大小写不敏感）是否在支持列表中。"""
    ext = os.path.splitext(abs_path)[1].lower()
    return ext in get_supported_extensions()


def textloader(abs_path:str)->list[Document]|None:
    return TextLoader(abs_path,encoding='utf-8').load()

def pdfloader(abs_path:str)->list[Document]|None:
    return PyPDFLoader(abs_path).load()

def docxloader(abs_path:str)->list[Document]|None:
    return Docx2txtLoader(abs_path).load()

def load_document(abs_path:str)->list[Document]|None:
    """
    按扩展名分发到对应加载器。
    返回统一 list[Document]（内容在 .page_content），不支持的扩展名返回 None。
    """
    if not is_supported_extension(abs_path):
        return None
    ext = os.path.splitext(abs_path)[1].lower()
    if ext == ".pdf":
        return pdfloader(abs_path)
    if ext == ".docx":
        return docxloader(abs_path)
    # 其余文本/代码类一律按 UTF-8 文本读取
    return textloader(abs_path)
