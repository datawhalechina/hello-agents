"""
测试增强系统功能
测试JWT认证和向量记忆服务
"""
import asyncio
import json
import sys
import requests
from typing import Dict, Any

# API基础URL
BASE_URL = "http://localhost:8000"

def test_auth_system():
    """测试认证系统"""
    print("=== 测试认证系统 ===")
    
    # 检查服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("   服务器未正常运行，请先启动服务器:")
            print("   python run.py")
            return None
    except requests.exceptions.ConnectionError:
        print("   服务器未运行，请先启动服务器:")
        print("   python run.py")
        print("   然后重新运行测试脚本")
        return None
    
    # 1. 测试用户注册
    register_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    print("1. 测试用户注册...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json=register_data)
    if response.status_code == 200:
        auth_data = response.json()
        print(f"   注册成功，获得令牌: {auth_data['access_token'][:20]}...")
        access_token = auth_data['access_token']
    else:
        print(f"   注册失败: {response.status_code} - {response.text}")
        return None
    
    # 2. 测试用户登录
    login_data = {
        "email": "test@example.com",
        "password": "testpassword123"
    }
    
    print("2. 测试用户登录...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
    if response.status_code == 200:
        auth_data = response.json()
        print(f"   登录成功，获得令牌: {auth_data['access_token'][:20]}...")
        access_token = auth_data['access_token']
    else:
        print(f"   登录失败: {response.status_code} - {response.text}")
        return None
    
    # 3. 测试获取用户信息
    headers = {"Authorization": f"Bearer {access_token}"}
    print("3. 测试获取用户信息...")
    response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)
    if response.status_code == 200:
        user_data = response.json()
        print(f"   用户信息: {user_data}")
    else:
        print(f"   获取用户信息失败: {response.status_code} - {response.text}")
    
    # 4. 测试访客会话
    print("4. 测试访客会话...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/guest")
    if response.status_code == 200:
        guest_data = response.json()
        print(f"   访客会话: {guest_data}")
        return access_token
    else:
        print(f"   创建访客会话失败: {response.status_code} - {response.text}")
        return access_token

def test_trip_planning_with_auth(access_token: str):
    """测试带认证的行程规划"""
    print("\n=== 测试带认证的行程规划 ===")
    
    # 检查服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("   服务器未正常运行")
            return
    except requests.exceptions.ConnectionError:
        print("   服务器未运行")
        return
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 第一次行程规划
    trip_request = {
        "destination": "北京",
        "start_date": "2024-10-01",
        "end_date": "2024-10-03",
        "preferences": ["历史", "文化"],
        "hotel_preferences": ["经济型"],
        "budget": "中等"
    }
    
    print("1. 第一次行程规划（北京历史文化）...")
    response = requests.post(f"{BASE_URL}/api/v1/trips/plan", json=trip_request, headers=headers)
    if response.status_code == 200:
        trip_data = response.json()
        print(f"   行程规划成功: {trip_data['trip_title']}")
        print(f"   行程天数: {len(trip_data['days'])}")
    else:
        print(f"   行程规划失败: {response.status_code} - {response.text}")
        return
    
    # 第二次行程规划（应该利用记忆）
    trip_request2 = {
        "destination": "北京",
        "start_date": "2024-11-01",
        "end_date": "2024-11-02",
        "preferences": ["历史"],
        "hotel_preferences": ["经济型"],
        "budget": "中等"
    }
    
    print("2. 第二次行程规划（应该利用记忆）...")
    response = requests.post(f"{BASE_URL}/api/v1/trips/plan", json=trip_request2, headers=headers)
    if response.status_code == 200:
        trip_data = response.json()
        print(f"   行程规划成功: {trip_data['trip_title']}")
        print(f"   行程天数: {len(trip_data['days'])}")
    else:
        print(f"   行程规划失败: {response.status_code} - {response.text}")

def test_vector_memory_service():
    """测试向量记忆服务"""
    print("\n=== 测试向量记忆服务 ===")
    
    try:
        from app.services.vector_memory_service import VectorMemoryService
        
        # 创建向量记忆服务实例
        memory_service = VectorMemoryService()
        
        # 1. 存储用户偏好
        print("1. 存储用户偏好...")
        memory_service.store_user_preference(
            user_id="test_user_123",
            preference_type="trip_preferences",
            preference_data={
                "destination": "北京",
                "preferences": ["历史", "文化"],
                "budget": "中等"
            }
        )
        
        # 2. 存储用户行程
        print("2. 存储用户行程...")
        memory_service.store_user_trip(
            user_id="test_user_123",
            trip_data={
                "destination": "北京",
                "trip_title": "北京历史文化3日游",
                "preferences": ["历史", "文化"],
                "days": [
                    {
                        "day": 1,
                        "theme": "皇家建筑探索",
                        "attractions": [
                            {"name": "故宫博物院", "type": "历史文化"},
                            {"name": "天坛公园", "type": "历史文化"}
                        ]
                    }
                ]
            }
        )
        
        # 3. 存储目的地知识
        print("3. 存储目的地知识...")
        memory_service.store_destination_knowledge(
            destination="北京",
            knowledge_data={
                "description": "中国的首都，历史文化名城",
                "highlights": ["故宫", "长城", "天坛"],
                "best_season": "春秋两季",
                "culture": "传统文化与现代文明交融"
            }
        )
        
        # 4. 检索用户记忆
        print("4. 检索用户记忆...")
        user_memories = memory_service.retrieve_user_memories(
            user_id="test_user_123",
            query="北京历史景点",
            limit=5
        )
        print(f"   找到 {len(user_memories)} 条用户记忆")
        for i, memory in enumerate(user_memories):
            print(f"   {i+1}. {memory['type']}: {memory.get('text_representation', '')[:50]}...")
        
        # 5. 检索知识记忆
        print("5. 检索知识记忆...")
        knowledge_memories = memory_service.retrieve_knowledge_memories(
            query="北京特色景点",
            limit=3
        )
        print(f"   找到 {len(knowledge_memories)} 条知识记忆")
        for i, memory in enumerate(knowledge_memories):
            print(f"   {i+1}. {memory['type']}: {memory.get('text_representation', '')[:50]}...")
        
        # 6. 混合检索
        print("6. 混合检索...")
        hybrid_results = memory_service.hybrid_search(
            user_id="test_user_123",
            query="北京历史景点推荐",
            user_limit=3,
            knowledge_limit=2
        )
        print(f"   用户记忆: {len(hybrid_results['user_memories'])} 条")
        print(f"   知识记忆: {len(hybrid_results['knowledge_memories'])} 条")
        
        # 7. 获取统计信息
        print("7. 获取统计信息...")
        stats = memory_service.get_stats()
        print(f"   用户记忆数: {stats['user_memory_count']}")
        print(f"   知识记忆数: {stats['knowledge_memory_count']}")
        print(f"   向量维度: {stats['vector_dimension']}")
        
        # 8. 保存索引
        print("8. 保存索引...")
        memory_service.save()
        print("   索引保存成功")
        
        print("\n向量记忆服务测试完成！")
        
    except Exception as e:
        print(f"向量记忆服务测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_integration():
    """测试系统集成"""
    print("\n=== 测试系统集成 ===")
    
    try:
        from app.agents.planner import PlannerAgent
        from app.services.llm_service import LLMService
        from app.services.vector_memory_service import VectorMemoryService
        from app.models.trip_model import TripPlanRequest
        
        # 创建服务实例
        llm_service = LLMService()
        memory_service = VectorMemoryService()
        
        # 创建规划器
        planner = PlannerAgent(llm_service=llm_service, memory_service=memory_service)
        
        # 创建行程请求
        trip_request = TripPlanRequest(
            destination="北京",
            start_date="2024-10-01",
            end_date="2024-10-02",
            preferences=["历史", "文化"],
            hotel_preferences=["经济型"],
            budget="中等"
        )
        
        # 执行行程规划
        print("执行行程规划...")
        plan = planner.plan_trip(request=trip_request, user_id="test_user_123")
        
        if plan:
            print(f"行程规划成功: {plan.trip_title}")
            print(f"行程天数: {len(plan.days)}")
            print(f"总预算: {plan.total_budget.total}")
        else:
            print("行程规划失败")
            
    except Exception as e:
        print(f"系统集成测试失败: {e}")
        print("   这可能是由于缺少必要的API密钥或服务配置问题")
        print("   请检查 .env 文件中的配置是否正确")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("开始测试增强系统功能...\n")
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--memory-only":
            print("仅测试向量记忆服务...")
            test_vector_memory_service()
            print("\n向量记忆服务测试完成！")
            return
        elif sys.argv[1] == "--help":
            print("测试脚本使用说明:")
            print("  python test_enhanced_system.py            # 运行所有测试")
            print("  python test_enhanced_system.py --memory-only  # 仅测试向量记忆服务")
            print("\n注意：测试认证和API功能需要先启动服务器:")
            print("  python run.py")
            return
    
    # 测试向量记忆服务
    test_vector_memory_service()
    
    # 测试认证系统
    access_token = test_auth_system()
    
    # 测试行程规划
    if access_token:
        test_trip_planning_with_auth(access_token)
    
    # 测试系统集成
    test_integration()
    
    print("\n所有测试完成！")
    print("\n如需单独测试向量记忆服务，可以使用:")
    print("  python test_enhanced_system.py --memory-only")

if __name__ == "__main__":
    main()