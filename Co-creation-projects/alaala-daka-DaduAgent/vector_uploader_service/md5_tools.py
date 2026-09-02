import os
import hashlib
from tool.config_handler import Rag_Config,System_Config
from tool.logger_handler import logger
def md5_file_check(md5_value:str)->bool:
    """
    查验文件中是否存储该MD5值
    """
    if not os.path.exists(Rag_Config["md5_storage_path"]):
        logger.info("[md5_file_check]md5储值文件未建立，现在初始化")
        return False

    if not os.path.isfile(Rag_Config["md5_storage_path"]):
        logger.critical(f"[md5_file_check]提供链接对应内容非文件")
        raise ValueError()

    with open(Rag_Config["md5_storage_path"],'r',encoding=System_Config["encoding"]) as f:
        for line in f.readlines():
            if md5_value.strip() == line.strip():
                return True
        return False

def md5_trans(string:str)->str:
    """
    将传入字符串转化为MD5值
    """
    hash_obj=hashlib.md5()
    hash_obj.update(string.encode(System_Config["encoding"]))
    return hash_obj.hexdigest()

def md5_loader(md5_value:str)->None:
    if not os.path.exists(Rag_Config["md5_storage_path"]):
            with open(Rag_Config["md5_storage_path"],'w',encoding=System_Config["encoding"]) as f:
                logger.info("[md5_loader]md5储值文件未创建，现在初始化")
                return

    if md5_file_check(md5_value):
        logger.info("[md5_loader]文件已存储")
        return

    with open(Rag_Config["md5_storage_path"],'a',encoding=System_Config["encoding"]) as f:
        f.write(f'{md5_value}\n')
        return
    
    


    
        
