
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

def evaluate_forum(forum_id: int):
    """Run standard evaluation for a single forum."""
    db = SessionLocal()
    try:
        history = get_forum_history(db, forum_id)
        if not history:
            return

        print(f"Evaluating Forum {forum_id}...")
        
        prompt = f"""
        你是一位公正、专业的辩论与讨论评估专家。请根据以下圆桌论坛的对话记录，严格按照给定的 5 个维度进行评分和点评。
        
        【对话记录】
        {history[:10000]}  # Truncate if too long, or handle splitting
        
        【评估维度】
        """
        
        for dim, criteria in EVALUATION_METRICS.items():
            prompt += f"\n### {dim}\n"
            prompt += f"- 核心定义: {criteria['definition']}\n"
            prompt += f"- 1分标准: {criteria['score_1']}\n"
            prompt += f"- 5分标准: {criteria['score_5']}\n"
            prompt += f"- 参考优化方向: {criteria['optimization']}\n"

        prompt += """
        \n【输出格式要求】
        请直接输出一个 JSON 对象，不要包含 Markdown 格式（如 ```json）。格式如下：
        {
            "scores": {
                "topic_adherence": 0,
                "argument_substantiality": 0,
                "boundary_control": 0,
                "contextual_coherence": 0,
                "role_consistency": 0
            },
            "comments": {
                "topic_adherence": "点评...",
                "argument_substantiality": "点评...",
                "boundary_control": "点评...",
                "contextual_coherence": "点评...",
                "role_consistency": "点评..."
            },
            "overall_summary": "整体评价..."
        }
        """

        result_text = run_simple_agent(
            "ForumEvaluationAgent",
            "你是一位公正、专业的多智能体讨论评估专家，只返回要求的 JSON。",
            prompt,
        )
        
        if result_text:
            # Clean up markdown if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0]
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0]
                
            try:
                result = json.loads(result_text)
                
                # Save result
                os.makedirs("exam/results", exist_ok=True)
                output_file = f"exam/results/eval_forum_{forum_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                
                print(f"Evaluation complete. Results saved to {output_file}")
                print(json.dumps(result, ensure_ascii=False, indent=2))
                
            except json.JSONDecodeError:
                print("Failed to parse LLM response as JSON.")
                print("Raw response:", result_text)
        else:
            print("HelloAgents evaluation failed.")

    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python exam/standard_eval.py <forum_id>")
    else:
        evaluate_forum(int(sys.argv[1]))
