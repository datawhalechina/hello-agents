"""Hand-written, explicitly labelled offline fixture. This is NOT an LLM run."""


def fixture(sources):
    rows = [
        {"source_id": "P1", "task": "实时候选云选择与人工决策支持", "data": "Himawari-9与C波段相控阵雷达；富山湾现场示例", "method": "卫星红外指标与近实时雷达辅助人工选择", "relevance": "direct",
         "findings": [{"text": "示例展示了高频观测支持目标选择与飞机引导。", "evidence_ids": ["P1-E1", "P1-E2"]}], "limitations": [{"text": "不评估播撒效果；摘要未提供本地独立分类标签集。", "evidence_ids": ["P1-E2"]}]},
        {"source_id": "P2", "task": "历史作业报告的信息抽取", "data": "832份NOAA报告；美国2000—2025年", "method": "PDF抽取与LLM结构化；人工抽样复核", "relevance": "method_reference",
         "findings": [{"text": "可借鉴报告结构化与人工核验流程。", "evidence_ids": ["P2-E1", "P2-E2"]}], "limitations": [{"text": "98.38%是信息抽取准确率；作业记录不能直接作为适宜条件标签。", "evidence_ids": ["P2-E2"]}]},
        {"source_id": "P3", "task": "过冷层状云冰晶聚合机制与速率", "data": "瑞士高原冬季层云的CLOUDLAB现场观测", "method": "IceDetectNet、因果分析、机器学习与物理模型", "relevance": "method_reference",
         "findings": [{"text": "可借鉴微物理变量组织和统计模型与物理模型对照。", "evidence_ids": ["P3-E1", "P3-E2"]}], "limitations": [{"text": "微物理聚合研究不能直接充当本地作业条件分类基线。", "evidence_ids": ["P3-E2"]}]},
        {"source_id": "S1", "task": "北方层状冷云条件标准的适用范围", "data": "未录入条款阈值", "method": "专家核对范围并独立确认标签", "relevance": "standard",
         "findings": [{"text": "需先确认地区与云型适用性。", "evidence_ids": ["S1-E1"]}], "limitations": [{"text": "此示例不包含可执行的阈值规则。", "evidence_ids": ["S1-E1"]}]}
    ]
    comparison = {"summary": "三篇论文分别覆盖实时选云、历史报告抽取和微物理机制，适合比较可迁移思路，不能按准确率直接排名。",
                  "comparisons": [{"source_ids": ["P1", "P2", "P3"], "can_compare_metrics": False,
                                   "reason": "预测目标、数据和评价口径不同，P2的信息抽取准确率不能与作业条件判识比较。",
                                   "evidence_ids": ["P1-E2", "P2-E2", "P3-E2"]}],
                  "gaps": [{"question": "缺失或延迟观测时，何时应该给出证据不足？", "basis": "实时多源决策需要时效；标签还需本地专家和适用标准确认。所选片段不足以判定该问题的新颖性。", "evidence_ids": ["P1-E1", "S1-E1"]}]}
    ideas = [{"id": "T1", "title": "缺测与延迟条件下的证据分级和拒判机制", "research_question": "在适用地区和云型内，缺测或延迟时加入质量标记与拒判是否降低错误的适宜条件判定？",
              "hypothesis": "在可接受覆盖率下，质量标记加拒判可降低被接受样本的错误率。", "evidence_ids": ["P1-E1", "P1-E2", "S1-E1"],
              "data_requirements": "经专家独立标注的事件级卫星、雷达与必要物理观测；真实到达时间和质量标记；先确认标准适用性。当前未取得。",
              "baselines": ["经专家确认的适用规则", "单源简单分类模型", "不带拒判的简单融合模型"],
              "steps": ["盘点本地资料和可用时刻，确认地区、云型、标签定义和专家核验流程。", "按独立天气事件划分训练与测试，确保决策时刻之后的信息不会进入输入。", "对随机缺失、连续缺失及真实延迟分别评测；只在验证集选择拒判阈值。", "固定测试集，对照无拒判与质量标记拒判，记录分类型错误及覆盖率。"],
              "metrics": ["宏平均F1与各类混淆矩阵", "适宜条件的错误接受率", "风险—覆盖率曲线", "不同缺失情形的性能变化"],
              "falsification": "在相同覆盖率和测试事件上，错误率未降低，或改进仅来自丢弃几乎全部样本，则不支持假设。",
              "risks": ["没有独立专家标签则无法验证分类性能", "模拟缺失不能替代真实缺测外部验证", "尚需系统检索已有拒判和缺失模态研究"], "novelty": "尚未系统检索核验"},
             {"id": "T2", "title": "作业记录与作业条件标签的分离及审计", "research_question": "把历史作业记录与独立条件标注分离，能否减少训练集中的代理标签偏差？",
              "hypothesis": "独立专家条件标注比直接把作业记录当标签，更能反映指定条件定义。", "evidence_ids": ["P2-E1", "P2-E2", "S1-E1"],
              "data_requirements": "有许可的历史日志、决策时刻观测与专家复核；记录来源和无法核实项。",
              "baselines": ["人工复核的条件标签", "历史作业记录代理标签（仅作偏差分析对照）"],
              "steps": ["建立带来源的报告抽取表，区分实际作业记录和条件观测。", "由专家在适用范围内独立判定条件，记录分歧与证据不足。", "按事件核查两类标签的分歧，分析资料缺失和决策约束。"],
              "metrics": ["抽取字段准确率", "专家间一致性", "代理标签与独立条件标签的分歧比例"],
              "falsification": "若独立盲审无法形成稳定标签，或未观察到预设的代理偏差，则需修改问题和标注协议。",
              "risks": ["历史日志可能缺少未作业事件", "样本规模和地区覆盖待确认"], "novelty": "尚未系统检索核验"}]
    review = {"verdict": "需人工核验：两条想法是待验证假设，尚无新颖性或实验性能证据。",
              "checks": [{"item": "任务与指标可比性", "status": "pass", "detail": "已经区分选云、信息抽取与微物理研究。", "evidence_ids": ["P1-E2", "P2-E2", "P3-E2"]},
                         {"item": "标准适用性与标签", "status": "needs_check", "detail": "需导师确认地区云型并由专家独立标注；不能从本示例生成阈值。", "evidence_ids": ["S1-E1"]},
                         {"item": "新颖性和可行性", "status": "needs_check", "detail": "需补充系统检索、全文精读和数据许可；不把所选片段的缺失当成研究空白证明。", "evidence_ids": ["P1-E2", "P2-E2"]}],
              "next_searches": ["cloud seeding seedability missing observations radar satellite", "weather modification selective classification abstention", "人工增雨 作业条件 识别 缺测 标签 专家"]}
    return {"analysis": {"papers": rows}, "comparison": comparison, "ideas": {"ideas": ideas}, "review": review}
