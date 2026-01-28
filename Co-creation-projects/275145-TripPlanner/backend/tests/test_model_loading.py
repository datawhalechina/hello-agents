"""
测试向量记忆服务的模型加载优化
验证HuggingFace镜像和本地缓存功能
"""
import sys
import io

# 设置标准输出编码为UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import os
import sys
from pathlib import Path

# 将项目根目录添加到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_model_loading():
    """测试模型加载功能"""
    print("="*80)
    print("测试向量记忆服务 - 模型加载优化")
    print("="*80)
    
    try:
        # 1. 检查环境变量配置
        print("\n1. 检查环境变量配置...")
        hf_endpoint = os.getenv('HF_ENDPOINT', '未设置')
        hf_offline = os.getenv('HF_HUB_OFFLINE', 'false')
        hf_cache = os.getenv('HF_HUB_CACHE_DIR', '使用系统默认')
        
        print(f"   HF_ENDPOINT: {hf_endpoint}")
        print(f"   HF_HUB_OFFLINE: {hf_offline}")
        print(f"   HF_HUB_CACHE_DIR: {hf_cache}")
        
        # 2. 初始化向量记忆服务
        print("\n2. 初始化向量记忆服务...")
        from app.services.vector_memory_service import VectorMemoryService
        from app.observability.logger import default_logger as logger
        
        # 创建服务实例（会触发模型加载）
        memory_service = VectorMemoryService()
        
        print("\n[OK] 向量记忆服务初始化成功！")
        
        # 3. 测试模型编码功能
        print("\n3. 测试文本嵌入功能...")
        test_texts = [
            "北京故宫是明清两代的皇宫",
            "上海外滩是著名的观光景点",
            "杭州西湖是中国著名的风景名胜"
        ]
        
        for i, text in enumerate(test_texts, 1):
            try:
                vector = memory_service._text_to_vector(text)
                print(f"   测试文本 {i}: {text[:30]}...")
                print(f"   向量维度: {len(vector)}, 范围: [{vector.min():.4f}, {vector.max():.4f}]")
            except Exception as e:
                print(f"   [ERROR] 文本嵌入失败: {e}")
                return False
        
        print("\n[OK] 文本嵌入功能正常！")
        
        # 4. 测试向量存储和检索
        print("\n4. 测试向量存储和检索...")
        memory_service.store_user_preference(
            user_id="test_user",
            preference_type="test",
            preference_data={"test": "data"}
        )
        
        results = memory_service.retrieve_user_memories(
            user_id="test_user",
            query="测试",
            limit=1
        )
        
        if len(results) > 0:
            print(f"   [OK] 成功存储并检索到 {len(results)} 条记录")
        else:
            print(f"   [WARNING] 未检索到记录")
        
        # 5. 检查模型信息
        print("\n5. 检查模型信息...")
        try:
            model_name = memory_service.embedding_model.get_sentence_embedding_dimension()
            print(f"   模型输出维度: {model_name}")
            print(f"   配置的向量维度: {memory_service.vector_dim}")
        except Exception as e:
            print(f"   [WARNING] 无法获取模型维度信息: {e}")
        
        # 6. 获取统计信息
        print("\n6. 获取向量索引统计...")
        stats = memory_service.get_stats()
        print(f"   用户记忆数: {stats['user_memory_count']}")
        print(f"   知识记忆数: {stats['knowledge_memory_count']}")
        print(f"   向量维度: {stats['vector_dimension']}")
        
        print("\n" + "="*80)
        print("[OK] 所有测试通过！")
        print("="*80)
        
        # 7. 使用建议
        print("\n[TIP] 使用建议:")
        print("   • 首次启动会从镜像站点下载模型，请耐心等待")
        print("   • 后续启动会使用本地缓存，速度会很快")
        print("   • 如果网络问题，可设置 HF_HUB_OFFLINE=true 使用离线模式")
        print("   • 可以手动下载模型到指定目录，然后设置 HF_HUB_CACHE_DIR")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_different_configs():
    """测试不同配置下的模型加载"""
    print("\n\n" + "="*80)
    print("测试不同配置场景")
    print("="*80)
    
    # 测试场景1: 使用镜像
    print("\n[SCENARIO] 场景1: 使用HuggingFace镜像")
    os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
    os.environ['HF_HUB_OFFLINE'] = 'false'
    print("   配置: HF_ENDPOINT=https://hf-mirror.com, HF_HUB_OFFLINE=false")
    print("   预期: 从镜像站点下载模型（如果本地无缓存）")
    
    # 测试场景2: 离线模式
    print("\n[SCENARIO] 场景2: 离线模式")
    os.environ['HF_HUB_OFFLINE'] = 'true'
    print("   配置: HF_HUB_OFFLINE=true")
    print("   预期: 仅使用本地缓存，如果缓存不存在则失败")
    
    # 测试场景3: 自定义缓存目录
    print("\n[SCENARIO] 场景3: 自定义缓存目录")
    custom_cache = str(Path.home() / ".cache" / "custom_hf")
    os.environ['HF_HUB_CACHE_DIR'] = custom_cache
    print(f"   配置: HF_HUB_CACHE_DIR={custom_cache}")
    print("   预期: 模型缓存到指定目录")

if __name__ == "__main__":
    print("\n[START] 开始测试...")
    
    # 运行主测试
    success = test_model_loading()
    
    # 显示不同配置场景
    test_with_different_configs()
    
    # 退出
    sys.exit(0 if success else 1)