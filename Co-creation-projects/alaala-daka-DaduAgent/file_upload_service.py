"""
RAG知识库文件上传处
"""
from vector_uploader_service.file_uploader import _file_upload_service
import os
from tool.logger_handler import logger
def upload_file_or_dir(abs_path):
    if os.path.isdir(abs_path):
        _file_upload_service.dir_upload(abs_path)
    elif os.path.isfile(abs_path):
        _file_upload_service.file_upload(abs_path)
    else:
        logger.error("[upload_file_or_dir]提供链接无效")
        raise ValueError
        
    

if __name__=="__main__":
    path=''#由此输入有效链接
    upload_file_or_dir(abs_path=path)    