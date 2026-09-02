import yaml
import os
from tool.path_tool import get_abs_path

def RagLoadConfig(abs_path:str|None=None,encoding='utf-8'):
    if not abs_path:
        abs_path=get_abs_path("config/RagConfig.yml")
    with open(abs_path,'r',encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)

def PromptLoadConfig(abs_path:str|None=None,encoding='utf-8'):
    if not abs_path:
        abs_path=get_abs_path("config/PromptConfig.yml")
    with open(abs_path,'r',encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)
    
def AgentLoadConfig(abs_path:str|None=None,encoding='utf-8'):
    if not abs_path:
        abs_path=get_abs_path("config/AgentConfig.yml")
    with open(abs_path,'r',encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)
    
def ChromaLoadConfig(abs_path:str|None=None,encoding='utf-8'):
    if not abs_path:
        abs_path=get_abs_path("config/ChromaConfig.yml")
    with open(abs_path,'r',encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)

def SystemLoadConfig(abs_path:str|None=None,encoding='utf-8'):
    if not abs_path:
        abs_path=get_abs_path("config/SystemConfig.yml")
    # 优先读 YAML 文件；文件不存在时 fallback 到环境变量
    if os.path.exists(abs_path):
        with open(abs_path,'r',encoding=encoding) as f:
            return yaml.load(f,Loader=yaml.FullLoader)
    # 从环境变量读取
    return {
        "encoding": encoding,
        "deepseek_api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "tavily_api_key": os.environ.get("TAVILY_API_KEY", ""),
    }

def FileManageLoadConfig(abs_path:str|None=None,encoding='utf-8'):
    if not abs_path:
        abs_path=get_abs_path("config/FileManageConfig.yml")
    with open(abs_path,'r',encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)

Rag_Config=RagLoadConfig()
Prompt_Config=PromptLoadConfig()
Chroma_Config=ChromaLoadConfig()
Agent_Config=AgentLoadConfig()
System_Config=SystemLoadConfig()
FileManage_Config=FileManageLoadConfig()

def SessionLoadConfig(abs_path:str|None=None,encoding='utf-8'):
    if not abs_path:
        abs_path=get_abs_path("config/SessionConfig.yml")
    with open(abs_path,'r',encoding=encoding) as f:
        return yaml.load(f,Loader=yaml.FullLoader)

Session_Config=SessionLoadConfig()

def ModelLoadConfig(abs_path:str|None=None,encoding='utf-8'):
    """读取模型注册表 config/ModelConfig.yml。
    文件缺失时返回内存默认（不写盘）：保持 DeepSeek 默认行为（base_url/api_key 留空 → 环境变量）。
    """
    if not abs_path:
        abs_path=get_abs_path("config/ModelConfig.yml")
    if os.path.exists(abs_path):
        with open(abs_path,'r',encoding=encoding) as f:
            return yaml.load(f,Loader=yaml.FullLoader) or {}
    return {
        "active_model": "deepseek-default",
        "models": [{
            "name": "deepseek-default",
            "label": "DeepSeek（默认）",
            "base_url": "",
            "api_key": "",
            "model": "deepseek-v4-pro",
        }],
        "embedding": {
            "label": "DashScope Embedding（默认）",
            "base_url": "",
            "api_key": "",
            "model": "text-embedding-v4",
        },
        "reranker": {
            "label": "DashScope Reranker（默认）",
            "base_url": "",
            "api_key": "",
            "model": "gte-rerank-v2",
        },
    }

Model_Config=ModelLoadConfig()

def reload_model_config() -> dict:
    """就地重读 ModelConfig.yml 到模块级 Model_Config（保持外部 import 引用有效）"""
    Model_Config.clear()
    Model_Config.update(ModelLoadConfig())
    return Model_Config

def save_model_config() -> None:
    """将 Model_Config 写回 config/ModelConfig.yml"""
    abs_path=get_abs_path("config/ModelConfig.yml")
    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    with open(abs_path,"w",encoding="utf-8") as f:
        yaml.dump(Model_Config, f, allow_unicode=True, default_flow_style=False)

def update_config(name: str, values: dict) -> None:
    """
    将配置值写入对应的 YAML 文件。
    注意：不影响已创建的 Agent 实例，新配置在下次创建 Agent 时生效。
    """
    config_files = {
        "agent":      "config/AgentConfig.yml",
        "chroma":     "config/ChromaConfig.yml",
        "rag":        "config/RagConfig.yml",
        "filemanage": "config/FileManageConfig.yml",
        "session":    "config/SessionConfig.yml",
        "ui":         "config/UIConfig.yml",
        "system":     "config/SystemConfig.yml",
    }
    if name not in config_files:
        raise ValueError(f"未知配置 '{name}'。可选: {list(config_files.keys())}")

    abs_path = get_abs_path(config_files[name])
    current = {}
    if os.path.exists(abs_path):
        with open(abs_path, "r", encoding="utf-8") as f:
            current = yaml.safe_load(f) or {}

    current.update(values)

    os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
    with open(abs_path, "w", encoding="utf-8") as f:
        yaml.dump(current, f, allow_unicode=True, default_flow_style=False)


def get_config_schema() -> dict:
    """返回所有可编辑配置的 JSON Schema 描述（供前端表单生成）"""
    return {
        "agent": {
            "title": "Agent 模型设置",
            "fields": {
                "chat_model_name": {
                    "type": "select",
                    "label": "聊天模型",
                    "default": "deepseek-v4-pro",
                    "options": ["deepseek-v4-pro", "deepseek-v4-flash"],
                    "description": "Agent 主对话使用的 DeepSeek 模型",
                }
            }
        },
        "chroma": {
            "title": "向量数据库设置",
            "fields": {
                "embedding_model_name": {
                    "type": "select",
                    "label": "嵌入模型",
                    "default": "text-embedding-v4",
                    "options": ["text-embedding-v4"],
                    "description": "DashScope 文本嵌入模型",
                },
                "collection_name": {
                    "type": "string",
                    "label": "集合名称",
                    "default": "knowledge_base",
                    "description": "Chroma 向量集合名称",
                },
                "reflection_collection_name": {
                    "type": "string",
                    "label": "反思集合名称",
                    "default": "agent_reflections",
                    "description": "反思笔记的 Chroma 集合名称",
                }
            }
        },
        "rag": {
            "title": "RAG 设置",
            "fields": {
                "rag_summarize_model_name": {
                    "type": "select",
                    "label": "RAG 总结模型",
                    "default": "deepseek-v4-flash",
                    "options": ["deepseek-v4-flash", "deepseek-v4-pro"],
                    "description": "RAG 检索总结使用的 DeepSeek 模型",
                }
            }
        },
        "filemanage": {
            "title": "文件管理设置",
            "fields": {
                "mode": {
                    "type": "select",
                    "label": "操作模式",
                    "default": "auto",
                    "options": ["auto", "manual"],
                    "description": "auto: 自由 CRUD（安全边界内）| manual: 写操作需用户批准",
                },
                "max_file_size_read": {
                    "type": "number",
                    "label": "最大读取大小 (字节)",
                    "default": 1048576,
                    "description": "文件读取大小上限",
                },
                "max_file_size_write": {
                    "type": "number",
                    "label": "最大写入大小 (字节)",
                    "default": 5242880,
                    "description": "文件写入大小上限",
                },
                "max_directory_depth": {
                    "type": "number",
                    "label": "最大目录深度",
                    "default": 20,
                    "description": "递归搜索的最大目录深度",
                }
            }
        },
        "session": {
            "title": "会话设置",
            "fields": {
                "auto_save": {
                    "type": "boolean",
                    "label": "自动保存",
                    "default": True,
                    "description": "每轮对话后自动保存会话状态",
                },
                "save_todos": {
                    "type": "boolean",
                    "label": "保存 Todo",
                    "default": True,
                    "description": "同时保存待办清单状态",
                },
                "session_id_length": {
                    "type": "number",
                    "label": "会话 ID 长度",
                    "default": 8,
                    "minimum": 4,
                    "maximum": 32,
                    "description": "新会话 ID 的字符长度",
                }
            }
        },
        "ui": {
            "title": "界面设置",
            "fields": {
                "theme": {
                    "type": "select",
                    "label": "主题",
                    "default": "light",
                    "options": ["light", "dark"],
                    "description": "前端 UI 主题",
                },
                "language": {
                    "type": "select",
                    "label": "语言",
                    "default": "zh",
                    "options": ["zh", "en"],
                    "description": "界面语言",
                },
                "font_size": {
                    "type": "number",
                    "label": "字体大小",
                    "default": 14,
                    "minimum": 11,
                    "maximum": 20,
                    "description": "基础字体大小 (px)",
                },
                "code_font_size": {
                    "type": "number",
                    "label": "代码字体大小",
                    "default": 13,
                    "minimum": 10,
                    "maximum": 18,
                    "description": "代码块字体大小 (px)",
                }
            }
        }
    }


if __name__=='__main__':
    #module_test
    print(Rag_Config["embedding_model_name"])