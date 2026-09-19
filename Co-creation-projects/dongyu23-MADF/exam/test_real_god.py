
import sys
import os
import json

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.real_god import RealGodAgent

def test_god_realism():
    print("=== RealGodAgent 逻辑与真实性深度测试 ===\n")
    
    # 增加 max_steps 到 10，确保有足够的思考空间
    # 提示词要求更具体，迫使必须搜索
    agent = RealGodAgent(max_steps=10)
    
    prompt = "生成两位datawhale的角色"
    
    print(f"测试提示词: {prompt}\n")
    print("正在启动 ReAct 循环监测...")
    print("-" * 50)
    
    results = []
    step_count = 0
    search_count = 0
    has_observation = False
    
    # 手动迭代生成器以捕获每个事件
    # Pass n=None to test dynamic N detection
    generator = agent.run(prompt, n=None)
    
    try:
        while True:
            try:
                event = next(generator)
            except StopIteration:
                break
                
            e_type = event.get("type")
            content = event.get("content")
            
            if e_type == "thought":
                step_count += 1
                print(f"\n[第 {step_count} 步 - 思考] 🤔:")
                print(f"  {content}")
            
            elif e_type == "action":
                print(f"\n[行动] 🎬:")
                print(f"  {content}")
                if "Search" in content or "搜索" in content:
                    search_count += 1
            
            elif e_type == "observation":
                has_observation = True
                print(f"\n[观察/搜索结果] 👀:")
                # 截取部分内容展示
                preview = str(content)[:300].replace('\n', ' ') + "..."
                print(f"  {preview}")
            
            elif e_type == "result":
                # Handle single or list results and accumulate
                new_results = content
                if isinstance(new_results, list):
                    if isinstance(results, list):
                        results.extend(new_results)
                    else:
                        results = new_results
                else:
                    if isinstance(results, list):
                        results.append(new_results)
                    else:
                        results = [new_results]
                
                print(f"\n[最终生成结果] 🎉:")
                print(json.dumps(content, ensure_ascii=False, indent=2))
            
            elif e_type == "error":
                print(f"\n[错误] ❌: {content}")

    except Exception as e:
        print(f"\n程序执行异常: {e}")

    print("\n" + "-" * 50)
    print("=== 测试结论分析 ===")
    
    # 1. 验证 ReAct 流程完整性
    if step_count > 0:
        print(f"✅ 逻辑测试: 智能体进行了 {step_count} 步思考。")
    else:
        print("❌ 逻辑测试: 智能体未展示思考过程，可能直接生成了结果。")
        
    # 2. 验证搜索功能
    if search_count > 0:
        print(f"✅ 工具测试: 智能体触发了 {search_count} 次搜索。")
    else:
        print("❌ 工具测试: 智能体完全未触发搜索，可能在“幻觉”或依赖预训练知识。")
        
    # 3. 验证搜索结果利用
    if has_observation:
        print("✅ 数据流测试: 智能体成功接收到了搜索结果（Observation）。")
    else:
        print("❌ 数据流测试: 智能体未获得有效的搜索反馈。")
        
    # 4. 验证最终结果真实性
    if results and isinstance(results, list) and len(results) >= 2:
        names = [p.get('name', '') for p in results]
        bios = [p.get('bio', '') for p in results]
        
        print(f"✅ 生成人物: {', '.join(names)}")
        
        # 检查是否包含目标人物
        found_target = any("Altman" in n or "奥特曼" in n for n in names) and \
                       any("Musk" in n or "马斯克" in n for n in names)
        
        if found_target:
            print("✅ 真实性测试: 成功识别并生成了指定人物。")
            
            # 检查 Bio 深度
            avg_len = sum(len(b) for b in bios) / len(bios)
            if avg_len > 200:
                print(f"✅ 深度测试: 平均生平长度 {int(avg_len)} 字，符合深度要求。")
            else:
                print(f"⚠️ 深度测试: 平均生平长度 {int(avg_len)} 字，略显单薄。")
        else:
            print("❌ 真实性测试: 生成的人物与要求不符。")
    else:
        print("❌ 结果测试: 未能生成有效的 JSON 列表。")

if __name__ == "__main__":
    test_god_realism()
