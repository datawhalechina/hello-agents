
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import Forum, Message
from app.crud import get_forum
from app.agent.agent import run_simple_agent

# Define the 5 Evaluation Dimensions (Optimized for Multi-Agent Advantages)
EVALUATION_METRICS = {
    "1. 观点多样性与碰撞 (Perspective Diversity & Collision)": {
        "definition": "是否涵盖议题的多个对立面或不同维度，存在鲜明的观点碰撞和张力。",
        "score_1": "观点单一，老生常谈，缺乏新意或对立视角。",
        "score_5": "涵盖多学科/多立场视角，存在深度的观点交锋和辩论。",
        "optimization": "引入背景、立场各异的角色，鼓励辩论。"
    },
    "2. 深度演进 (Depth Evolution)": {
        "definition": "随着对话进行，观点是否变得更加深刻，是否解决了初步的质疑，实现螺旋上升。",
        "score_1": "观点在原地打转，只是换个说法重复。",
        "score_5": "像剥洋葱一样层层递进，从表面现象深入到本质机制或哲学层面。",
        "optimization": "引入定期总结和深度思考机制，防止循环论证。"
    },
    "3. 交互批判性 (Interactive Criticality)": {
        "definition": "对他人观点的回应是否具有批判性，能否精准指出逻辑漏洞并迫使对方回应。",
        "score_1": "自说自话，或只是简单的附和/反对，无逻辑支撑。",
        "score_5": "精准打击对方逻辑弱点，迫使对方修正或完善观点，形成有效对话。",
        "optimization": "共享记忆机制，确保智能体能准确引用和反驳。"
    },
    "4. 观点实质性与落地性 (Argument Substantiality & Grounding)": {
        "definition": "发言是否具备实质内容，引用具体案例、数据或历史事实，拒绝“假大空”。",
        "score_1": "充斥正确的废话、盲目附和，缺乏细节支撑。",
        "score_5": "论据详实，引用具体数据、文献或案例支撑论点，逻辑严密。",
        "optimization": "接入外部知识库（RAG）或专家角色设定。"
    },
    "5. 角色鲜明度 (Character Distinctiveness)": {
        "definition": "角色是否具有独特的人格魅力和语言风格，而非千篇一律的AI味。",
        "score_1": "所有角色说话都像同一个AI助手，千人一面。",
        "score_5": "即使遮住名字，也能通过语言风格和思维方式分辨出是谁。",
        "optimization": "ReAct动态生成的高自由度角色，强化人设指令。"
    }
}

def get_forum_history(db: Session, forum_id: int) -> str:
    """Fetch and format forum history for evaluation."""
    forum = get_forum(db, forum_id)
    if not forum:
        print(f"Forum {forum_id} not found.")
        return ""
    
    messages = db.query(Message).filter(Message.forum_id == forum_id).order_by(Message.timestamp.asc()).all()
    
    history_str = f"Forum Topic: {forum.topic}\n\n"
    for msg in messages:
        history_str += f"[{msg.speaker_name}]: {msg.content}\n"
    
    return history_str

def compare_forums(forum_id_a: int, forum_id_b: int, ablation_desc: str):
    """Run ablation study evaluation (A vs B)."""
    db = SessionLocal()
    try:
        history_a = get_forum_history(db, forum_id_a)
        history_b = get_forum_history(db, forum_id_b)

        if not history_a or not history_b:
            print("One or both forums not found.")
            return

        print(f"Comparing Forum {forum_id_a} vs Forum {forum_id_b} (Ablation: {ablation_desc})...")
        
        prompt = f"""
        你是一位公正、专业的辩论与讨论评估专家。请对以下两场圆桌论坛进行【对比分析】（Side-by-Side Evaluation）。
        这两场论坛基于相同的主题，但设置上存在消融差异（Ablation Difference）：{ablation_desc}。
        
        【论坛 A 对话记录】
        {history_a[:8000]} # Truncate if too long
        
        【论坛 B 对话记录】
        {history_b[:8000]} # Truncate if too long
        
        【评估任务】
        请基于以下 5 个维度，分别对 A 和 B 进行打分（1-5分），并详细说明为何其中一方优于另一方。
        """
        
        for dim, criteria in EVALUATION_METRICS.items():
            prompt += f"\n### {dim}\n"
            prompt += f"- 核心定义: {criteria['definition']}\n"
            prompt += f"- 1分标准: {criteria['score_1']}\n"
            prompt += f"- 5分标准: {criteria['score_5']}\n"
            prompt += f"- 参考优化方向: {criteria['optimization']}\n"

        prompt += """
        \n【输出格式要求】
        请直接输出一个 Markdown 格式的对比报告，包含以下章节：
        1. **总体评分对比表** (包含各维度 A/B 得分)
        2. **维度逐项分析** (针对每个维度，分析 A 和 B 的表现差异，指出消融设置带来的具体影响)
        3. **消融结论** (总结该变量对讨论质量的关键影响，例如：“去掉理论库导致观点深度显著下降...”)
        """

        result_text = run_simple_agent(
            "AblationEvaluationAgent",
            "你是一位公正、专业的多智能体讨论评估专家。",
            prompt,
        )
        
        if result_text:
            
            # Save result
            os.makedirs("exam/results", exist_ok=True)
            output_file = f"exam/results/ablation_{forum_id_a}_vs_{forum_id_b}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# 消融实验报告: Forum {forum_id_a} vs {forum_id_b}\n")
                f.write(f"**消融变量描述**: {ablation_desc}\n\n")
                f.write(result_text)
            
            print(f"Ablation study complete. Report saved to {output_file}")
            print(result_text)
        else:
            print("HelloAgents evaluation failed.")

    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python exam/ablation_study.py <forum_id_A> <forum_id_B> <ablation_description>")
    else:
        compare_forums(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3])
