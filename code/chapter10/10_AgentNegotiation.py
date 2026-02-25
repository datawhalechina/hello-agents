"""
10.3.4 在智能体中使用A2A工具
（3）高级用法：Agent间协商
"""

from hello_agents.protocols import A2AServer, A2AClient
import threading
import time

# 创建两个需要协商的Agent
agent1 = A2AServer(
    name="agent1",
    description="Agent 1"
)

@agent1.skill("propose")
def handle_proposal(text: str) -> str:
    """处理协商提案"""
    import re
    import json
    
    # 解析提案
    match = re.search(r'propose\s+(.+)', text, re.IGNORECASE)
    proposal_str = match.group(1).strip() if match else text
    
    try:
        proposal = eval(proposal_str)
        task = proposal.get("task")
        deadline = proposal.get("deadline")
        
        # 评估提案
        if deadline >= 7:  # 至少需要7天
            result = {"accepted": True, "message": "接受提案"}
        else:
            result = {
                "accepted": False,
                "message": "时间太紧",
                "counter_proposal": {"deadline": 7}
            }
        return str(result)
    except Exception:
        return str({"accepted": False, "message": "无效的提案格式"})

agent2 = A2AServer(
    name="agent2",
    description="Agent 2"
)

@agent2.skill("negotiate")
def negotiate_task(text: str) -> str:
    """发起协商"""
    import re
    
    # 解析任务和截止日期
    match = re.search(r'negotiate\s+task:(.+?)\s+deadline:(\d+)', text, re.IGNORECASE)
    if match:
        task = match.group(1).strip()
        deadline = int(match.group(2))
        
        # 向agent1发送提案
        proposal = {"task": task, "deadline": deadline}
        return str({"status": "negotiating", "proposal": proposal})
    else:
        return str({"status": "error", "message": "无效的协商请求"})

# 启动服务
if __name__ == "__main__":
    threading.Thread(target=lambda: agent1.run(port=7000), daemon=True).start()
    threading.Thread(target=lambda: agent2.run(port=7001), daemon=True).start()
    time.sleep(2)
    
    # 测试协商流程
    client1 = A2AClient("http://localhost:7000")
    client2 = A2AClient("http://localhost:7001")
    
    # Agent2发起协商
    negotiation = client2.execute_skill("negotiate", "negotiate task:开发新功能 deadline:5")
    print(f"协商请求：{negotiation.get('result')}")
    
    # Agent1评估提案
    proposal = client1.execute_skill("propose", "propose {'task': '开发新功能', 'deadline': 5}")
    print(f"提案评估：{proposal.get('result')}")
    
    # 保持服务运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n服务已停止")

