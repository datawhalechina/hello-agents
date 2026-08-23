"""
MathModelAgent Web界面

基于Streamlit的Web界面
"""

import streamlit as st
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.code_executor import CodeExecutor
from src.template_manager import TemplateManager, CumcmTemplate, McmIcmTemplate


# 页面配置
st.set_page_config(
    page_title="MathModelAgent - 智能数学建模助手",
    page_icon="📐",
    layout="wide"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2ca02c;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .info-box {
        background-color: #f0f8ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #f0fff0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2ca02c;
        margin-bottom: 1rem;
    }
    .error-box {
        background-color: #fff0f0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #d62728;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """主函数"""
    
    # 标题
    st.markdown('<div class="main-header">📐 MathModelAgent</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align: center; color: #666;">智能数学建模助手</div>', unsafe_allow_html=True)
    
    # 侧边栏
    with st.sidebar:
        st.markdown("## 功能菜单")
        page = st.radio(
            "选择功能",
            ["🏠 首页", "📝 问题分析", "💻 代码执行", "📄 论文生成", "📚 知识库", "⚙️ 设置"]
        )
    
    # 页面路由
    if page == "🏠 首页":
        show_home()
    elif page == "📝 问题分析":
        show_problem_analysis()
    elif page == "💻 代码执行":
        show_code_execution()
    elif page == "📄 论文生成":
        show_paper_generation()
    elif page == "📚 知识库":
        show_knowledge_base()
    elif page == "⚙️ 设置":
        show_settings()


def show_home():
    """显示首页"""
    
    st.markdown('<div class="sub-header">欢迎使用 MathModelAgent</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>MathModelAgent</strong> 是一个智能数学建模助手，能够帮助您完成数学建模的全过程。
    </div>
    """, unsafe_allow_html=True)
    
    # 功能介绍
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📝 问题分析
        - 自动分析建模问题
        - 提取关键信息
        - 推荐合适的模型
        """)
    
    with col2:
        st.markdown("""
        ### 💻 代码执行
        - 执行Python代码
        - 自动修复错误
        - 生成可视化图表
        """)
    
    with col3:
        st.markdown("""
        ### 📄 论文生成
        - 多种模板选择
        - 自动生成LaTeX
        - 支持国赛/美赛
        """)
    
    # 快速开始
    st.markdown('<div class="sub-header">快速开始</div>', unsafe_allow_html=True)
    
    st.markdown("""
    1. 在左侧菜单选择功能
    2. 输入数学建模问题
    3. 系统自动分析并提供建议
    4. 执行代码并生成论文
    """)


def show_problem_analysis():
    """显示问题分析页面"""
    
    st.markdown('<div class="sub-header">📝 问题分析</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        输入数学建模问题，系统将自动分析并提供建议。
    </div>
    """, unsafe_allow_html=True)
    
    # 问题输入
    problem = st.text_area(
        "请输入数学建模问题描述",
        height=200,
        placeholder="例如：某公司需要优化其物流配送路线..."
    )
    
    if st.button("分析问题"):
        if problem:
            with st.spinner("正在分析问题..."):
                # 模拟分析过程
                st.success("分析完成！")
                
                st.markdown("### 分析结果")
                
                st.markdown("""
                **问题类型：** 优化问题
                
                **关键变量：**
                - 配送点坐标
                - 配送距离
                - 配送时间
                
                **约束条件：**
                - 车辆容量限制
                - 时间窗口限制
                
                **推荐模型：**
                1. TSP（旅行商问题）
                2. VRP（车辆路径问题）
                """)
        else:
            st.warning("请输入问题描述")


def show_code_execution():
    """显示代码执行页面"""
    
    st.markdown('<div class="sub-header">💻 代码执行</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        输入Python代码并执行，支持数据处理、可视化等功能。
    </div>
    """, unsafe_allow_html=True)
    
    # 代码输入
    code = st.text_area(
        "请输入Python代码",
        height=300,
        value="""import numpy as np
import matplotlib.pyplot as plt

# 创建数据
x = np.linspace(0, 10, 100)
y = np.sin(x)

# 绘制图形
plt.figure(figsize=(10, 6))
plt.plot(x, y, linewidth=2)
plt.title('Sine Wave')
plt.xlabel('x')
plt.ylabel('y')
plt.grid(True, alpha=0.3)
plt.show()

print("图表已生成！")"""
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("执行代码"):
            with st.spinner("正在执行代码..."):
                executor = CodeExecutor()
                result = executor.execute(code)
                
                if result['success']:
                    st.success("代码执行成功！")
                    
                    if result['stdout']:
                        st.markdown("### 输出结果")
                        st.code(result['stdout'])
                    
                    if result['figure']:
                        st.markdown("### 生成图表")
                        st.image(f"data:image/png;base64,{result['figure']}")
                else:
                    st.error("代码执行失败")
                    st.code(result['stderr'])
    
    with col2:
        if st.button("执行并修复"):
            with st.spinner("正在执行代码..."):
                executor = CodeExecutor()
                result = executor.execute_with_fix(code)
                
                if result['success']:
                    st.success(f"代码执行成功！（尝试{result.get('attempts', 1)}次）")
                    
                    if result['stdout']:
                        st.markdown("### 输出结果")
                        st.code(result['stdout'])
                    
                    if result['figure']:
                        st.markdown("### 生成图表")
                        st.image(f"data:image/png;base64,{result['figure']}")
                else:
                    st.error(f"代码执行失败（尝试{result.get('attempts', 1)}次）")
                    st.code(result['stderr'])


def show_paper_generation():
    """显示论文生成页面"""
    
    st.markdown('<div class="sub-header">📄 论文生成</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        选择模板并填写内容，生成LaTeX格式的论文。
    </div>
    """, unsafe_allow_html=True)
    
    # 模板选择
    template_manager = TemplateManager()
    templates = template_manager.list_templates()
    
    template_name = st.selectbox(
        "选择模板",
        templates,
        format_func=lambda x: {
            'cumcm': '国赛模板',
            'math_modeling': '通用数学建模模板',
            'mcm_icm': '美赛模板'
        }.get(x, x)
    )
    
    # 论文信息
    st.markdown("### 论文信息")
    
    col1, col2 = st.columns(2)
    
    with col1:
        title = st.text_input("论文标题", "数学建模论文")
        author = st.text_input("作者/队号", "20260001")
    
    with col2:
        date = st.text_input("日期", "2026年9月")
    
    # 论文内容
    st.markdown("### 论文内容")
    
    abstract = st.text_area("摘要", height=150)
    keywords = st.text_input("关键词", "关键词1；关键词2；关键词3")
    
    problem_restatement = st.text_area("问题重述", height=150)
    problem_analysis = st.text_area("问题分析", height=150)
    model_assumptions = st.text_area("模型假设", height=150)
    model_establishment = st.text_area("模型建立与求解", height=150)
    
    if st.button("生成论文"):
        with st.spinner("正在生成论文..."):
            context = {
                'title': title,
                'author': author,
                'date': date,
                'abstract': abstract,
                'keywords': keywords,
                'problem_restatement': problem_restatement,
                'problem_analysis': problem_analysis,
                'model_assumptions': model_assumptions,
                'model_establishment': model_establishment
            }
            
            output_path = f"outputs/{template_name}_paper.tex"
            
            try:
                template_manager.generate(template_name, context, output_path)
                st.success(f"论文已生成：{output_path}")
                
                # 显示生成的LaTeX代码
                with open(output_path, 'r', encoding='utf-8') as f:
                    latex_content = f.read()
                
                st.markdown("### 生成的LaTeX代码")
                st.code(latex_content, language='latex')
                
            except Exception as e:
                st.error(f"生成失败：{e}")


def show_knowledge_base():
    """显示知识库页面"""
    
    st.markdown('<div class="sub-header">📚 知识库</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        管理数学建模知识库，添加和检索建模方法、代码模板等。
    </div>
    """, unsafe_allow_html=True)
    
    # 知识库内容
    knowledge_dir = Path("knowledge")
    
    if knowledge_dir.exists():
        knowledge_files = list(knowledge_dir.glob("*.md"))
        
        if knowledge_files:
            st.markdown("### 知识文档")
            
            for file in knowledge_files:
                with st.expander(file.name):
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    st.markdown(content)
        else:
            st.info("知识库为空，请添加知识文档")
    else:
        st.warning("知识库目录不存在")
    
    # 添加知识
    st.markdown("### 添加知识")
    
    new_title = st.text_input("知识标题")
    new_content = st.text_area("知识内容", height=200)
    
    if st.button("添加知识"):
        if new_title and new_content:
            knowledge_dir.mkdir(exist_ok=True)
            
            file_path = knowledge_dir / f"{new_title}.md"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {new_title}\n\n{new_content}")
            
            st.success(f"知识已添加：{file_path}")
            st.rerun()
        else:
            st.warning("请输入标题和内容")


def show_settings():
    """显示设置页面"""
    
    st.markdown('<div class="sub-header">⚙️ 设置</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        配置项目参数和API密钥。
    </div>
    """, unsafe_allow_html=True)
    
    # API配置
    st.markdown("### API配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        llm_model = st.text_input("LLM模型", "Qwen/Qwen2.5-72B-Instruct")
        llm_api_key = st.text_input("API密钥", type="password")
    
    with col2:
        llm_base_url = st.text_input("API地址", "https://api-inference.modelscope.cn/v1/")
        llm_timeout = st.number_input("超时时间(秒)", value=60, min_value=10, max_value=300)
    
    # 代码执行配置
    st.markdown("### 代码执行配置")
    
    code_timeout = st.number_input("代码执行超时(秒)", value=30, min_value=10, max_value=120)
    max_output_length = st.number_input("最大输出长度", value=10000, min_value=1000, max_value=100000)
    
    # 保存配置
    if st.button("保存配置"):
        st.success("配置已保存")


if __name__ == "__main__":
    main()
