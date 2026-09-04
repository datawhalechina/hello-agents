import yaml
from types import SimpleNamespace

class YAMLResult(SimpleNamespace):
    pass

def read(yaml_path:str):
    try:
        with open(yaml_path, "r") as yaml_file:
            yaml_dict = yaml.safe_load(yaml_file)
            return YAMLResult(**yaml_dict)
    except Exception as e:
        raise Exception(f"[YAML Reader] Error occured when read YAML from path '{ yaml_path }'.\nError: { str(e) }")