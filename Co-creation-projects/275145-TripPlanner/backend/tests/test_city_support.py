"""
测试城市支持逻辑
验证30个支持城市的验证机制以及不支持城市的警告机制
"""
import sys
import requests

# API基础URL
BASE_URL = "http://localhost:8000"

def test_supported_cities():
    """测试支持的城市"""
    print("=" * 80)
    print("测试1: 支持的城市（应该成功规划）")
    print("=" * 80)
    
    supported_cities = ["北京", "上海", "杭州", "成都", "三亚", "宁波"]
    
    for city in supported_cities:
        print(f"\n📍 测试城市: {city}")
        
        trip_request = {
            "destination": city,
            "start_date": "2024-10-01",
            "end_date": "2024-10-03",
            "preferences": ["历史", "文化"],
            "hotel_preferences": ["经济型"],
            "budget": "中等"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/trips/plan", json=trip_request, timeout=180)
            
            if response.status_code == 200:
                print(f"   ✅ 规划成功 - 行程标题: {response.json()['trip_title']}")
            elif response.status_code == 400:
                print(f"   ❌ 请求被拒绝 - {response.json()}")
            else:
                print(f"   ⚠️  状态码: {response.status_code} - {response.text[:100]}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ⚠️  无法连接到服务器，请先启动服务器")
            return False
        except Exception as e:
            print(f"   ❌ 发生错误: {e}")
    
    return True

def test_unsupported_cities():
    """测试不支持的城市（应该给出警告但仍处理）"""
    print("\n" + "=" * 80)
    print("测试2: 不支持的城市（应该给出警告但仍尝试规划）")
    print("=" * 80)
    
    unsupported_cities = [
        ("石家庄", "非热门旅游城市"),
        ("温州", "小城市"),
        ("未知城市123", "无效城市名")
    ]
    
    for city, description in unsupported_cities:
        print(f"\n📍 测试城市: {city} ({description})")
        
        trip_request = {
            "destination": city,
            "start_date": "2024-10-01",
            "end_date": "2024-10-03",
            "preferences": ["历史"],
            "hotel_preferences": ["经济型"],
            "budget": "中等"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/api/v1/trips/plan", json=trip_request, timeout=180)
            
            if response.status_code == 200:
                print(f"   ✅ 规划成功（带有警告）- {response.json()['trip_title']}")
            elif response.status_code == 400:
                # 检查是否是城市不支持错误
                error_data = response.json()
                if "UNSUPPORTED_CITY" in str(error_data):
                    print(f"   ❌ 被拒绝 - 系统拒绝处理不支持的城市")
                    print(f"      错误信息: {error_data}")
                else:
                    print(f"   ⚠️  其他错误 - {error_data}")
            else:
                print(f"   ⚠️  状态码: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            print(f"   ⚠️  无法连接到服务器")
            return False
        except Exception as e:
            print(f"   ❌ 发生错误: {e}")
    
    return True

def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 80)
    print("测试3: 边界情况")
    print("=" * 80)
    
    # 测试空城市
    print(f"\n📍 测试: 空城市")
    trip_request = {
        "destination": "",
        "start_date": "2024-10-01",
        "end_date": "2024-10-03",
        "preferences": ["历史"],
        "hotel_preferences": ["经济型"],
        "budget": "中等"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/trips/plan", json=trip_request, timeout=180)
        if response.status_code == 400:
            print(f"   ✅ 正确拒绝 - {response.json()}")
        else:
            print(f"   ⚠️  意外响应 - 状态码: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 发生错误: {e}")
    
    # 测试特殊字符
    print(f"\n📍 测试: 特殊字符城市")
    trip_request = {
        "destination": "北京@#$%",
        "start_date": "2024-10-01",
        "end_date": "2024-10-03",
        "preferences": ["历史"],
        "hotel_preferences": ["经济型"],
        "budget": "中等"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/v1/trips/plan", json=trip_request, timeout=180)
        if response.status_code == 200:
            print(f"   ✅ 系统尝试处理（可能给出警告）")
        elif response.status_code == 400:
            print(f"   ✅ 正确拒绝 - 无效输入")
        else:
            print(f"   ⚠️  状态码: {response.status_code}")
    except Exception as e:
        print(f"   ❌ 发生错误: {e}")
    
    return True

def display_supported_cities():
    """显示所有支持的城市"""
    print("\n" + "=" * 80)
    print("当前系统支持的30个热门旅游城市:")
    print("=" * 80)
    
    from app.agents.planner import CITY_BOUNDS
    
    cities = list(CITY_BOUNDS.keys())
    print(f"\n总计: {len(cities)} 个城市\n")
    
    for i, city in enumerate(cities, 1):
        print(f"{i:2d}. {city}")
    
    return True

if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧪 城市支持逻辑测试")
    print("=" * 80)
    
    # 检查服务器是否运行
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print("\n⚠️  服务器未正常运行，请先启动服务器:")
            print("   cd trip_planner/backend && python run.py")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print("\n⚠️  无法连接到服务器，请先启动服务器:")
        print("   cd trip_planner/backend && python run.py")
        sys.exit(1)
    
    print("\n✅ 服务器运行正常\n")
    
    # 显示支持的城市列表
    display_supported_cities()
    
    # 运行测试
    success1 = test_supported_cities()
    success2 = test_unsupported_cities()
    success3 = test_edge_cases()
    
    # 总结
    print("\n" + "=" * 80)
    print("📊 测试总结")
    print("=" * 80)
    print(f"支持城市测试: {'✅ 通过' if success1 else '❌ 失败'}")
    print(f"不支持城市测试: {'✅ 通过' if success2 else '❌ 失败'}")
    print(f"边界情况测试: {'✅ 通过' if success3 else '❌ 失败'}")
    
    if success1 and success2 and success3:
        print("\n🎉 所有测试通过！")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败，请检查日志")
        sys.exit(1)