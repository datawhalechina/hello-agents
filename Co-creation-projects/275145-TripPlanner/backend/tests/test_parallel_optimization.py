"""
性能优化测试 - 并行执行对比串行执行
测试景点、酒店、天气查询的并行化性能提升
"""
import time
import json
from app.models.trip_model import TripPlanRequest
from app.agents.planner import PlannerAgent
from app.services.llm_service import LLMService
from app.services.vector_memory_service import VectorMemoryService
from app.observability.logger import default_logger as logger
from app.config import settings
import sys
import traceback

def create_test_request(destination="北京", days=3):
    """创建测试请求"""
    return TripPlanRequest(
        destination=destination,
        start_date="2024-10-01",
        end_date=f"2024-10-{days:02d}",
        preferences=["历史", "文化"],
        hotel_preferences=["经济型"],
        budget="中等"
    )

def test_single_request(destination="北京", label="测试"):
    """测试单个请求的性能"""
    logger.info(f"\n{'='*60}")
    logger.info(f"开始 {label} - 目的地: {destination}")
    logger.info(f"{'='*60}")
    
    try:
        # 初始化服务
        logger.info("初始化服务...")
        llm_service = LLMService()
        memory_service = VectorMemoryService()
        planner = PlannerAgent(llm_service=llm_service, memory_service=memory_service)
        
        # 创建测试请求
        request = create_test_request(destination)
        
        # 开始计时
        start_time = time.time()
        
        # 执行行程规划
        logger.info(f"\n执行行程规划...")
        result = planner.plan_trip(request, user_id=f"test_{destination}")
        
        # 结束计时
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # 输出结果
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ {label} 完成!")
        logger.info(f"{'='*60}")
        logger.info(f"⏱️  总耗时: {elapsed_time:.2f} 秒")
        
        if result:
            logger.info(f"📝 行程标题: {result.trip_title}")
            logger.info(f"📅 行程天数: {len(result.days)} 天")
            logger.info(f"💰 总预算: {result.total_budget.total if result.total_budget else 'N/A'}")
            
            # 统计景点数量
            total_attractions = sum(len(day.attractions) for day in result.days)
            logger.info(f"🏛️  景点数量: {total_attractions} 个")
            
            return elapsed_time, True
        else:
            logger.error("❌ 规划结果为 None")
            return elapsed_time, False
            
    except Exception as e:
        logger.error(f"❌ {label} 执行失败: {e}")
        logger.error(traceback.format_exc())
        return 0, False

def run_performance_test():
    """运行性能测试"""
    logger.info("\n" + "="*80)
    logger.info("🚀 性能优化测试 - 并行执行 vs 串行执行")
    logger.info("="*80)
    
    # 测试参数
    destinations = ["北京", "上海", "杭州"]
    
    results = []
    
    for destination in destinations:
        logger.info(f"\n\n{'#'*80}")
        logger.info(f"测试目的地: {destination}")
        logger.info(f"{'#'*80}")
        
        # 执行测试
        elapsed_time, success = test_single_request(destination, f"{destination}行程规划")
        
        results.append({
            "destination": destination,
            "elapsed_time": elapsed_time,
            "success": success
        })
    
    # 输出总结
    logger.info("\n\n" + "="*80)
    logger.info("📊 性能测试总结")
    logger.info("="*80)
    
    total_time = 0
    success_count = 0
    
    for i, result in enumerate(results, 1):
        status = "✅ 成功" if result["success"] else "❌ 失败"
        logger.info(f"{i}. {result['destination']}: {result['elapsed_time']:.2f} 秒 - {status}")
        total_time += result['elapsed_time']
        if result['success']:
            success_count += 1
    
    logger.info("-" * 80)
    logger.info(f"总耗时: {total_time:.2f} 秒")
    logger.info(f"成功率: {success_count}/{len(results)} ({100*success_count/len(results):.1f}%)")
    
    # 计算平均时间
    if success_count > 0:
        avg_time = total_time / success_count
        logger.info(f"平均耗时: {avg_time:.2f} 秒/请求")
    
    # 性能对比预期
    logger.info("\n" + "="*80)
    logger.info("📈 性能对比")
    logger.info("="*80)
    
    # 根据PERFORMANCE_ANALYSIS.md中的估算
    # 串行执行：景点(3-5s) + 酒店(3-5s) + 天气(2-3s) = 8-13s
    serial_estimate = 11  # 取中间值
    # 并行执行：三个查询并行 = max(3-5s, 3-5s, 2-3s) = 3-5s
    parallel_estimate = 4  # 取中间值
    
    if success_count > 0:
        actual_avg = total_time / success_count
        improvement = (serial_estimate - actual_avg) / serial_estimate * 100
        
        logger.info(f"串行执行预估: {serial_estimate:.0f} 秒")
        logger.info(f"并行执行预估: {parallel_estimate:.0f} 秒")
        logger.info(f"实际执行平均: {actual_avg:.2f} 秒")
        logger.info("-" * 80)
        logger.info(f"⚡ 性能提升: ~{improvement:.1f}%")
        
        if actual_avg < parallel_estimate * 1.5:  # 容错范围50%
            logger.info("✅ 优化效果显著！")
        elif actual_avg < serial_estimate * 0.8:  # 比串行快20%以上
            logger.info("✅ 优化有效！")
        else:
            logger.info("⚠️  优化效果不明显，可能需要进一步调优")
    
    logger.info("="*80)
    
    return results

if __name__ == "__main__":
    try:
        results = run_performance_test()
        logger.info("\n✅ 性能测试完成!")
        
        # 保存结果到文件
        with open("performance_test_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info("📄 测试结果已保存到: performance_test_results.json")
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  测试被用户中断")
    except Exception as e:
        logger.error(f"\n❌ 测试失败: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)