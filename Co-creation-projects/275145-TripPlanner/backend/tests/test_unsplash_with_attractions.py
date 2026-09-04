"""
测试景点图片获取逻辑
直接模拟 planner.py 中的图片搜索流程，方便快速调试
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.unsplash_service import UnsplashService


def test_attraction_images():
    """测试真实景点名称的图片搜索"""
    
    # 初始化 Unsplash 服务
    service = UnsplashService(access_key="qoRz2cAQwJD5kPyrN7_2dqdn_1Kfp-DXq4TQKK_dgI8")
    
    # 模拟几个真实的景点名称（来自北京行程）
    test_cases = [
        {
            "attraction_name": "故宫博物院",
            "destination": "北京"
        },
        {
            "attraction_name": "天安门广场",
            "destination": "北京"
        },
        {
            "attraction_name": "八达岭长城",
            "destination": "北京"
        },
        {
            "attraction_name": "颐和园",
            "destination": "北京"
        },
        {
            "attraction_name": "中国明清两代的皇家宫殿，也是世界上现存规模最大、保存最为完整的木质结构古建筑之一。",
            "destination": "北京"
        }
    ]
    
    print("=" * 80)
    print("开始测试景点图片获取逻辑")
    print("=" * 80)
    
    for idx, case in enumerate(test_cases, 1):
        attraction_name = case["attraction_name"]
        destination = case["destination"]
        
        print(f"\n【测试 {idx}/{len(test_cases)}】")
        print(f"景点名称: {attraction_name}")
        print(f"目标城市: {destination}")
        print("-" * 80)
        
        # 构造搜索关键词（与 planner.py 保持一致）
        search_queries = [
            f"{attraction_name} {destination}",  # 完整名称 + 城市
            f"{attraction_name}",  # 只用景点名
            f"{destination} landmark"  # 兜底：城市地标
        ]
        
        image_url = None
        for query in search_queries:
            print(f"  尝试关键词: '{query}'")
            image_url = service.get_photo_url(query)
            
            if image_url:
                print(f"  ✅ 成功获取图片: {image_url}")
                break
            else:
                print(f"  ⚠️ 未找到图片，尝试下一个关键词")
        
        if not image_url:
            print(f"  ❌ 所有关键词均未找到图片")
        
        print("-" * 80)
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    test_attraction_images()
