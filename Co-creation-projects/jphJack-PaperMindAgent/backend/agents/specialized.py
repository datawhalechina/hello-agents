"""6 个专职 Agent：每个绑定角色提示词与工具子集"""
from __future__ import annotations

from backend.agents.base import BaseAgent
from backend.llm.client import DeepSeekClient
from backend.tools.base import ToolRegistry


class PaperParserAgent(BaseAgent):
    """步骤1：扫描文件夹并解析 PDF 为结构化文本"""

    def __init__(self, client: DeepSeekClient, registry: ToolRegistry):
        super().__init__(
            name="PaperParser",
            role=(
                "你是论文解析专家。你的任务是扫描本地文件夹中的 PDF 论文，"
                "使用 parse_pdf 工具将每篇 PDF 解析为保留章节结构的文本。"
                "输出格式：每篇论文含 {path, title, sections:[{heading, content, figure_captions}]}。"
                "若某篇解析失败，记录错误并跳过，继续处理其余论文。"
                "你可以自主决定调用顺序，支持并行处理多篇。"
            ),
            client=client,
            registry=registry,
            tool_names=["scan_folder", "parse_pdf"],
        )


class ExtractorAgent(BaseAgent):
    """步骤2：单篇论文结构化抽取（核心主干）"""

    def __init__(self, client: DeepSeekClient, registry: ToolRegistry):
        super().__init__(
            name="Extractor",
            role=(
                "你是论文结构化抽取专家。你的任务是对每篇已解析论文调用 extract_paper_structure 工具，"
                "抽取固定 schema 的结构化记录（title/task_problem/method/key_contributions/"
                "datasets/metrics/results/limitations/future_work），每字段标注 source_sections 与 confidence。"
                "limitations 是重点字段，必须是论文明确承认或可从结果推断的，不允许臆造。"
                "缺失字段触发针对性补抽。可调用 hybrid_search 回溯原文细节。"
                "每篇结果独立缓存，失败可单独重跑。"
            ),
            client=client,
            registry=registry,
            tool_names=["extract_paper_structure", "hybrid_search"],
        )


class IndexerAgent(BaseAgent):
    """步骤3：向量索引构建"""

    def __init__(self, client: DeepSeekClient, registry: ToolRegistry):
        super().__init__(
            name="Indexer",
            role=(
                "你是向量索引构建专家。你的任务是对已解析论文调用 build_vector_index 工具，"
                "将论文全文按章节分块向量化存入 Chroma 向量库，为后续混合搜索提供点查询能力。"
                "索引构建是增强能力，失败时可降级（跳过 RAG 仅用结构化字段）。"
            ),
            client=client,
            registry=registry,
            tool_names=["build_vector_index"],
        )


class GapAnalyzerAgent(BaseAgent):
    """步骤4：跨论文综合分析与 Gap 识别"""

    def __init__(self, client: DeepSeekClient, registry: ToolRegistry):
        super().__init__(
            name="GapAnalyzer",
            role=(
                "你是研究空白（Gap）识别专家。你的任务是对结构化字段调用 analyze_gaps 工具，"
                "识别四类 Gap 信号：重复局限、方法空白、矛盾结论、未兑现的未来工作。"
                "需要原文细节佐证时调用 hybrid_search 检索相关段落。"
                "输出候选 Gap 列表，每个 Gap 标注来源论文、Gap 类型、论证与置信度。"
            ),
            client=client,
            registry=registry,
            tool_names=["analyze_gaps", "hybrid_search"],
        )


class InnovationGeneratorAgent(BaseAgent):
    """步骤5：创新点生成与筛选"""

    def __init__(self, client: DeepSeekClient, registry: ToolRegistry):
        super().__init__(
            name="InnovationGenerator",
            role=(
                "你是创新点生成专家。你的任务是对候选 Gap 调用 generate_innovations 工具，"
                "生成四类来源的创新方向（方法组合/局限改进/跨域迁移/新场景应用），"
                "用三维评分（新颖性/可行性/显著性）筛选，取综合得分最高的 2-3 个。"
                "调用 web_search 检索近 1-2 年相关工作做新颖性去重。"
                "调用 load_memory 加载历史创新点避免重复，调用 save_memory 保存新创新点。"
            ),
            client=client,
            registry=registry,
            tool_names=["generate_innovations", "web_search", "load_memory", "save_memory"],
        )


class ExperimentDesignerAgent(BaseAgent):
    """步骤6：实验方案设计"""

    def __init__(self, client: DeepSeekClient, registry: ToolRegistry):
        super().__init__(
            name="ExperimentDesigner",
            role=(
                "你是实验方案设计专家。你的任务是对每个创新点调用 design_experiments 工具，"
                "输出可执行研究方案：研究假设、数据集、基线方法、评估指标、消融实验、"
                "实验步骤、预期结果与风险。方案须具体可执行。"
            ),
            client=client,
            registry=registry,
            tool_names=["design_experiments"],
        )


def build_all_specialized_agents(client: DeepSeekClient, registry: ToolRegistry) -> dict:
    """构建全部 6 个专职 Agent，返回 name->agent 字典"""
    return {
        "PaperParser": PaperParserAgent(client, registry),
        "Extractor": ExtractorAgent(client, registry),
        "Indexer": IndexerAgent(client, registry),
        "GapAnalyzer": GapAnalyzerAgent(client, registry),
        "InnovationGenerator": InnovationGeneratorAgent(client, registry),
        "ExperimentDesigner": ExperimentDesignerAgent(client, registry),
    }
