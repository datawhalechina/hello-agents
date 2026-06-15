"""求职规划API路由"""

from fastapi import APIRouter, HTTPException
from ...models.schemas import CareerRequest, CareerPlanResponse
from ...agents.career_planner_agent import get_career_planner

router = APIRouter(prefix="/career", tags=["求职规划"])


@router.post(
    "/plan",
    response_model=CareerPlanResponse,
    summary="生成求职计划",
    description="根据用户输入的求职需求，生成完整的求职策略报告，包含职位推荐、公司分析、薪资数据和每日任务规划"
)
async def plan_career(request: CareerRequest):
    """生成求职计划"""
    try:
        print(f"\n{'='*60}")
        print(f"[RECV] 收到求职规划请求:")
        print(f"   职位: {request.target_role}")
        print(f"   城市: {request.city}")
        print(f"   周期: {request.target_days}天")
        print(f"{'='*60}\n")

        agent = get_career_planner()
        career_plan = agent.plan_career(request)

        print("[OK] 求职计划生成成功\n")

        return CareerPlanResponse(
            success=True,
            message="求职计划生成成功",
            data=career_plan
        )

    except Exception as e:
        print(f"[FAIL] 生成求职计划失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"生成求职计划失败: {str(e)}"
        )


@router.get(
    "/health",
    summary="健康检查",
    description="检查求职规划服务是否正常"
)
async def health_check():
    """健康检查"""
    try:
        agent = get_career_planner()
        return {
            "status": "healthy",
            "service": "career-planner",
            "has_search_tool": agent.has_brave_search
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"服务不可用: {str(e)}"
        )
