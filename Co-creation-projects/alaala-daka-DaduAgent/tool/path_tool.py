import os

def get_project_root()->str:
    """
    获取项目根路径
    """
    current_file_path=os.path.abspath(__file__)
    current_dir=os.path.dirname(current_file_path)
    current_dir=os.path.dirname(current_dir)
    return current_dir

def get_abs_path(relative_path:str)->str:
    """
    根据当前传入相对路径获取绝对路径
    """
    return os.path.abspath(relative_path)

