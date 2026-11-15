"""虚构开发材料、示范实现设定与离线协议测试夹具。"""

import re

RESUME = """演示候选人｜Python / Agent 应用开发
以下材料完全虚构，仅用于演示，不对应真实个人。

项目：企业知识库问答助手
使用 Python、FastAPI 开发文档入库和问答接口；独立负责后端 API 与检索链路。
接入向量检索和关键词检索，使用 RAG 生成带原文引用的回答。
为文档缺失、检索为空、供应商超时设计错误提示与降级路径。
使用 SQLite 保存文档元数据和问答记录，使用 Docker Compose 完成本地部署。
整理 30 条问答样例作为回归集，检查引用能否在原文中找到；尚未做独立测试集对比。

技能：Python、FastAPI、SQL、Git、Docker；了解 Agent、RAG 和工具调用。
当前未提供线上并发测试、生产部署或真实用户量的证据。"""

JOB = """Agent 应用开发工程师｜AI 应用方向
岗位要求：
- 熟悉 Python、FastAPI，能独立开发后端接口。
- 理解 RAG，具有向量检索、文档解析和引用校验实践。
- 熟悉 Agent 工具调用与多步骤任务编排。
- 具备 SQL、数据库建模与数据持久化经验。
- 熟悉 Docker、Git 和自动化测试。
- 能设计评测集，分析准确性、延迟和模型调用成本。
- 了解 Redis、消息队列和并发任务处理。
- 能解释个人贡献、技术取舍与失败处理。"""

PROFILES = {
    "development": {
        "name": "Agent 开发",
        "role": "Agent 应用开发工程师",
        "resume": RESUME,
        "job": JOB,
    },
}

# 虚构实现设定供示范候选人使用；不向独立评审透露示范标签或期望分数。
DEVELOPMENT_SCENARIO = """项目是本地企业知识库问答原型。候选人独立负责 FastAPI API、检索链路和 SQLite 存储。
POST /api/questions 接收 workspace_id、request_id、question、可选 document_ids；Pydantic 去除首尾空白，拒绝空问题并限制长度。
字段非法返回 422；指定文档缺失、跨工作区或版本无效统一返回 404 DOCUMENT_UNAVAILABLE，检索和模型调用为零，不泄露其他工作区资源。
SQLite requests 表对 (workspace_id, request_id) 建唯一约束并存 payload_hash、status、answer_id。
事务一写 pending 并提交，随后在事务外调用检索及模型；事务二校验引用并写 answer、置 completed，一起提交。
唯一约束仲裁并发，不能只靠 SELECT 再 INSERT；相同 ID 不同 payload 返回 409，已完成返回旧结果 200，pending 返回 202。
外部模型费用不随数据库回滚，原型不承诺外部调用 exactly-once。崩溃遗留 pending 需要显式恢复，尚无自动租约抢占。
文档入库保留 document_id、version、chunk_id 和原文偏移。固定字符分块，重叠用于保留边界；分块大小尚无独立参数搜索。
关键词侧 SQLite FTS5 MATCH 按 bm25 取 top10，向量侧余弦相似度取 top10。
每侧先按 (document_id, version, chunk_id) 去重；RRF score(c)=sum_r 1/(60+rank_r(c))，名次从1开始，缺席某路贡献为0。
融合按分数降序、并列按稳定 chunk_id 排序取 top5，去重键包含版本，不能平均两种原始分数。
检索为空或证据不足明确拒答，不造引用；生成后逐字检查引用在当前文档版本的原文中，非法引用不保存为成功答案。
候选人设计 pytest 校验空白问题、文档不可用、并发同键、供应商超时、引用失配等路径；这里没有独立运行报告或测试通过数字。
30条样例是开发回归集，检查链路与引用，不是独立效果集，不能证明 RRF 优于纯向量。
计划冻结版本、人工标注 gold chunk，与 BM25-only/vector-only/RRF 比较。Recall@5 逐查询召回金标数除以全部金标数后求均值；
Hit@5 是有命中的查询数除以有答案查询数；无答案样例单独统计拒答。延迟、输入输出 token 和成本需另测，尚无线上数据。
Docker Compose 用于本地 API 与相关依赖部署；Git 管理代码，未使用真实用户数据，也未部署生产环境。
对 Redis、消息队列、微调或高并发生产架构只了解原理，没有在本项目实现。"""

TOPICS = {
    "产品需求": ["用户研究", "需求", "访谈", "业务目标", "prd", "原型", "验收标准"],
    "产品指标": ["任务完成率", "指标口径", "实验", "a/b", "sql", "商业"],
    "算法实验": ["训练", "微调", "偏好", "实验", "消融", "随机种子", "泛化"],
    "数据质量": ["清洗", "数据划分", "数据重复", "泄漏", "测试集"],
    "后端开发": ["python", "fastapi", "接口"],
    "检索与引用": ["rag", "向量", "检索", "引用", "文档解析"],
    "Agent 编排": ["agent", "工具调用", "编排"],
    "数据持久化": ["sql", "数据库", "持久化"],
    "工程交付": ["docker", "git", "测试"],
    "效果评测": ["评测", "延迟", "成本", "准确性"],
    "并发与任务": ["redis", "消息队列", "并发"],
    "个人贡献": ["个人", "贡献", "取舍", "失败"],
}


def lines(text: str) -> list[str]:
    return [
        line.strip().lstrip("-• ")
        for line in text.splitlines()
        if len(line.strip()) > 7
    ]


def topic_of(text: str) -> tuple[str, list[str]]:
    return max(
        TOPICS.items(), key=lambda pair: sum(word in text.lower() for word in pair[1])
    )


def analyze(resume: str, job: str) -> dict:
    resume_lines = lines(resume)
    requirements = []
    for line in lines(job):
        if not re.search(
            r"熟悉|掌握|经验|具备|了解|能够|能独立|理解|能解释|能设计|负责|要求|需要|熟练",
            line,
        ):
            continue
        if line.endswith(("：", ":")):
            continue
        topic, words = topic_of(line)
        candidates = [
            (sum(word in candidate.lower() for word in words), candidate)
            for candidate in resume_lines
            if not re.search(r"未提供|尚未|没有|不熟悉", candidate)
        ]
        score, evidence = max(candidates, default=(0, ""))
        requirements.append(
            {
                "title": line[:140],
                "requirement_quote": line,
                "topic": topic,
                "evidence_quote": evidence if score else "",
                "status": "partial" if score else "missing",
                "reason": "找到相关原文，实际熟练程度仍需面试核实。"
                if score
                else "现有简历未找到直接证据，可补充真实案例或保留待确认。",
            }
        )
    if not requirements:
        quote = lines(job)[0] if lines(job) else job.strip()
        requirements = [
            {
                "title": quote[:140],
                "requirement_quote": quote,
                "topic": "岗位理解",
                "evidence_quote": "",
                "status": "missing",
                "reason": "演示规则未识别技术要点，请切换真实模型或补充明确的岗位要求。",
            }
        ]
    claims = []
    for line in resume_lines:
        if any(
            word in line
            for word in [
                "负责",
                "使用",
                "实现",
                "接入",
                "设计",
                "开发",
                "参与",
                "优化",
                "整理",
            ]
        ):
            topic, _ = topic_of(line)
            claims.append(
                {
                    "text": line[:350],
                    "quote": line,
                    "topic": topic,
                    "risk": "metric"
                    if re.search(r"\d+", line)
                    else "ownership"
                    if "负责" in line
                    else "technical",
                }
            )
        if len(claims) == 6:
            break
    if not claims:
        quote = resume_lines[0] if resume_lines else resume.strip()
        claims = [
            {"text": quote[:350], "quote": quote, "topic": "个人经历", "risk": "normal"}
        ]
    return {
        "summary": "已按关键词整理岗位要求与简历原文。演示模式使用固定规则，不评估真实匹配程度或录用概率。",
        "requirements": requirements[:12],
        "claims": claims,
    }
