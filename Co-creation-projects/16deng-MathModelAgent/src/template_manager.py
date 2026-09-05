"""
模板管理器模块

提供LaTeX模板的管理和生成
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from jinja2 import Template, Environment, FileSystemLoader


class TemplateManager:
    """模板管理器类"""
    
    def __init__(self, template_dir: str = "./templates"):
        """
        初始化模板管理器
        
        Args:
            template_dir: 模板目录
        """
        self.template_dir = Path(template_dir)
        self.templates = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载所有模板"""
        if not self.template_dir.exists():
            self.template_dir.mkdir(parents=True, exist_ok=True)
            print(f"模板目录已创建: {self.template_dir}")
            return
        
        # 加载所有.tex模板文件
        for template_file in self.template_dir.glob("*.tex"):
            template_name = template_file.stem
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                self.templates[template_name] = template_content
                print(f"已加载模板: {template_name}")
            except Exception as e:
                print(f"加载模板失败 {template_name}: {e}")
    
    def get_template(self, template_name: str) -> Optional[str]:
        """
        获取模板内容
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板内容
        """
        return self.templates.get(template_name)
    
    def list_templates(self) -> List[str]:
        """
        列出所有可用模板
        
        Returns:
            模板名称列表
        """
        return list(self.templates.keys())
    
    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        渲染模板
        
        Args:
            template_name: 模板名称
            context: 模板上下文
            
        Returns:
            渲染后的内容
        """
        template_content = self.get_template(template_name)
        if not template_content:
            raise ValueError(f"模板不存在: {template_name}")
        
        # 创建Jinja2环境
        env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            variable_start_string='{{ ',
            variable_end_string=' }}'
        )
        
        # 渲染模板
        template = env.from_string(template_content)
        return template.render(**context)
    
    def generate(self, template_name: str, context: Dict[str, Any], 
                 output_path: str) -> str:
        """
        生成LaTeX文件
        
        Args:
            template_name: 模板名称
            context: 模板上下文
            output_path: 输出路径
            
        Returns:
            输出文件路径
        """
        # 渲染模板
        content = self.render(template_name, context)
        
        # 创建输出目录
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"LaTeX文件已生成: {output_path}")
        return str(output_file)
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        获取模板信息
        
        Args:
            template_name: 模板名称
            
        Returns:
            模板信息字典
        """
        template_content = self.get_template(template_name)
        if not template_content:
            return {}
        
        # 提取模板中的变量
        env = Environment(
            variable_start_string='{{ ',
            variable_end_string=' }}'
        )
        
        # 解析模板
        ast = env.parse(template_content)
        variables = env.get_undeclared_variables(ast)
        
        return {
            'name': template_name,
            'variables': list(variables),
            'content_length': len(template_content)
        }


class CumcmTemplate(TemplateManager):
    """国赛模板管理器"""
    
    def __init__(self, template_dir: str = "./templates"):
        """初始化国赛模板管理器"""
        super().__init__(template_dir)
        self.default_context = {
            'title': '数学建模论文',
            'team_number': 'XXXX',
            'date': '2026年9月',
            'abstract': '本文研究了...',
            'keywords': '关键词1；关键词2；关键词3',
            'problem_restatement': '',
            'problem_background': '',
            'problem_requirements': '',
            'problem_analysis': '',
            'problem1_analysis': '',
            'problem2_analysis': '',
            'model_assumptions': '',
            'symbol_table': '',
            'model_establishment': '',
            'problem1_solution': '',
            'problem2_solution': '',
            'model_verification': '',
            'model_evaluation': '',
            'model_advantages': '',
            'model_disadvantages': '',
            'model_improvements': '',
            'references': '',
            'code_file': 'code.py'
        }
    
    def generate_paper(self, context: Dict[str, Any], output_path: str) -> str:
        """
        生成国赛论文
        
        Args:
            context: 论文内容
            output_path: 输出路径
            
        Returns:
            输出文件路径
        """
        # 合并默认上下文
        full_context = {**self.default_context, **context}
        
        # 生成论文
        return self.generate('cumcm', full_context, output_path)


class McmIcmTemplate(TemplateManager):
    """美赛模板管理器"""
    
    def __init__(self, template_dir: str = "./templates"):
        """初始化美赛模板管理器"""
        super().__init__(template_dir)
        self.default_context = {
            'title': 'Mathematical Modeling Paper',
            'team_number': 'XXXX',
            'date': 'February 2026',
            'abstract': 'This paper studies...',
            'keywords': 'keyword1; keyword2; keyword3',
            'introduction': '',
            'background': '',
            'problem_statement': '',
            'assumptions': '',
            'symbol_table': '',
            'model_development': '',
            'model1_name': 'Model 1',
            'model1_description': '',
            'model2_name': 'Model 2',
            'model2_description': '',
            'results': '',
            'sensitivity_analysis': '',
            'model_evaluation': '',
            'strengths': '',
            'weaknesses': '',
            'conclusion': '',
            'references': '',
            'code_file': 'code.py'
        }
    
    def generate_paper(self, context: Dict[str, Any], output_path: str) -> str:
        """
        生成美赛论文
        
        Args:
            context: 论文内容
            output_path: 输出路径
            
        Returns:
            输出文件路径
        """
        # 合并默认上下文
        full_context = {**self.default_context, **context}
        
        # 生成论文
        return self.generate('mcm_icm', full_context, output_path)


# 测试代码
if __name__ == "__main__":
    # 测试模板管理器
    manager = TemplateManager()
    
    print("可用模板:")
    for template in manager.list_templates():
        print(f"  - {template}")
    
    # 测试国赛模板
    cumcm = CumcmTemplate()
    
    context = {
        'title': '物流配送路线优化研究',
        'team_number': '20260001',
        'abstract': '本文研究了物流配送路线优化问题...',
        'keywords': '物流配送；路线优化；TSP问题',
    }
    
    output_path = "outputs/cumcm_paper.tex"
    try:
        cumcm.generate_paper(context, output_path)
        print(f"国赛论文已生成: {output_path}")
    except Exception as e:
        print(f"生成失败: {e}")
