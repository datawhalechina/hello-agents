
import sys
import os
import json
from typing import List, Dict, Any

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.real_god import RealGodAgent

def test_sequential_generation():
    print("=== RealGodAgent 顺序生成模式测试 ===")
    
    agent = RealGodAgent(max_steps=5)
    prompt = "请生成两位历史上的物理学家：爱因斯坦和牛顿。"
    n = 2
    
    print(f"测试提示词: {prompt}")
    print(f"计划生成数量: {n} 位 (预期将分 2 次独立执行)\n")
    print("-" * 50)
    # Simulate the loop in the endpoint
    generated_names = []
    generated_count = 0
    
    for i in range(n):
        print(f"\n🚀 [第 {i+1}/{n} 次循环] 开始生成第 {i+1} 位角色...")
        
        step_count = 0
        search_count = 0
        current_persona = None
        
        # Each call to agent.run now only generates 1 persona
        generator = agent.run(prompt, n=1, generated_names=generated_names)
        
        try:
            for event in generator:
                e_type = event.get("type")
                content = event.get("content")
                
                if e_type == "thought":
                    step_count += 1
                    print(f"  [思考] {content[:60]}...")
                
                elif e_type == "action":
                    if "Search" in content or "搜索" in content:
                        search_count += 1
                        print(f"  [行动] 🔍 触发搜索: {content}")
                
                elif e_type == "observation":
                    print(f"  [观察/搜索结果] 👀: {content}")
                
                elif e_type == "result":
                    current_persona = content
                    if isinstance(current_persona, list) and len(current_persona) == 1:
                        p = current_persona[0]
                        print(f"  [结果] ✅ 成功生成角色: {p.get('name')} ({p.get('title')})")
                        print(f"         Bio长度: {len(p.get('bio', ''))} 字")
                        print(f"         Stance长度: {len(p.get('stance', ''))} 字")
                        print(f"         完整JSON:\n{json.dumps(p, ensure_ascii=False, indent=2)}")
                        # Add name to list for next iteration
                        if p.get('name'):
                            generated_names.append(p.get('name'))
                    else:
                        print(f"  [警告] ⚠️ 预期生成 1 位，实际生成 {len(current_persona)} 位")
                        print(f"         完整JSON:\n{json.dumps(current_persona, ensure_ascii=False, indent=2)}")
                
                elif e_type == "error":
                    print(f"  [错误] ❌: {content}")
                        
        except Exception as e:
            print(f"  [异常] ❌ 执行异常: {e}")
            
        if current_persona:
            generated_count += 1
        else:
            print("  [失败] ❌ 本次循环未生成有效角色")
            
        print(f"  [统计] 本次消耗思考步数: {step_count}, 搜索次数: {search_count}")
    
    print(f"\n✅ 已生成名单: {generated_names}")
    print("\n" + "-" * 50)
    print("=== 测试总结 ===")
    if generated_count == n:
        print(f"✅ 测试通过: 成功按顺序独立生成了 {generated_count} 位角色。")
    else:
        print(f"❌ 测试失败: 预期生成 {n} 位，实际成功 {generated_count} 位。")

if __name__ == "__main__":
    test_sequential_generation()
