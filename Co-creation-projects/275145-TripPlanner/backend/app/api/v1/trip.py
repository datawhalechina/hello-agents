from fastapi import APIRouter, Request, Depends, HTTPException
from app.models.trip_model import TripPlanRequest, TripPlanResponse
from app.observability.logger import default_logger as logger
from app.exceptions.custom_exceptions import (
    BusinessException,
    LLMServiceException,
    MapServiceException,
    ImageServiceException
)
from app.exceptions.error_codes import ErrorCode
from app.middleware.auth import get_user_id
from app.agents.planner import CITY_BOUNDS
from datetime import datetime
from typing import List, Optional
import uuid

# 导入新的Agent
from app.agents.planner import PlannerAgent

# 导入共享的服务实例
from app.services.llm_service import LLMService
from app.services.vector_memory_service import vector_memory_service
from app.services.redis_service import redis_service

router = APIRouter()

# 初始化所有Agent
# attraction_agent = AttractionSearchAgent()
# hotel_agent = HotelSearchAgent()
# weather_agent = WeatherQueryAgent()
planner_agent = PlannerAgent(llm_service=LLMService, memory_service=vector_memory_service)


@router.post("/plan", response_model=TripPlanResponse)
def plan_trip(request: TripPlanRequest, http_request: Request):
    """
    接收行程规划请求，通过多智能体协作完成规划。（增强版 - 支持记忆和上下文）
    """
    # 获取用户ID（从认证中间件获取）
    user_id = get_user_id(http_request)
    
    logger.info(
        f"接收到新的行程规划请求",
        extra={
            "destination": request.destination,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "budget": request.budget,
            "preferences": request.preferences,
            "hotel_preferences": request.hotel_preferences,
            "user_id": user_id
        }
    )

    try:
        # 参数验证
        if not request.destination or not request.destination.strip():
            raise BusinessException(
                ErrorCode.MISSING_PARAMETER,
                details={"field": "destination", "message": "目的地不能为空"}
            )
        
        if not request.start_date or not request.end_date:
            raise BusinessException(
                ErrorCode.MISSING_PARAMETER,
                details={"field": "date_range", "message": "日期范围不能为空"}
            )
        
        # 城市支持验证（警告但不阻止）
        if request.destination not in CITY_BOUNDS:
            logger.warning(
                f"⚠️ 用户请求不支持的城市: {request.destination}。"
                f"支持的城市包括：北京、上海、广州、深圳、成都、杭州、重庆、武汉、西安、苏州、天津、南京、长沙、郑州、"
                f"厦门、青岛、大连、三亚、丽江、桂林、昆明、哈尔滨、沈阳、济南、黄山、张家界、敦煌、拉萨、乌鲁木齐、宁波等30个热门旅游城市。"
                f"对于不支持的城市，系统将尝试进行基础规划，但可能存在准确度降低的情况。",
                extra={
                    "destination": request.destination,
                    "supported_cities_count": len(CITY_BOUNDS),
                    "is_supported_city": False
                }
            )
        else:
            logger.info(
                f"✅ 用户请求支持的城市: {request.destination}",
                extra={"is_supported_city": True}
            )

        # 调用增强的PlannerAgent进行规划
        final_plan = planner_agent.plan_trip(request=request, user_id=user_id)
        
        # 保存向量记忆和完整行程
        if final_plan:
            # 存储用户行程到向量数据库
            trip_data = {
                "destination": request.destination,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "preferences": request.preferences,
                "hotel_preferences": request.hotel_preferences,
                "budget": request.budget,
                "trip_title": final_plan.trip_title,
                "days": [day.dict() for day in final_plan.days]
            }
            vector_memory_service.store_user_trip(user_id, trip_data)
            
            # 存储用户偏好
            vector_memory_service.store_user_preference(user_id, "trip_preferences", {
                "destination": request.destination,
                "preferences": request.preferences,
                "hotel_preferences": request.hotel_preferences,
                "budget": request.budget
            })
            
            # 保存向量索引
            vector_memory_service.save()
            
            # 保存完整行程到Redis（新增）
            trip_id = str(uuid.uuid4())
            full_trip_data = final_plan.model_dump()
            full_trip_data["id"] = trip_id
            full_trip_data["created_at"] = datetime.now().isoformat()
            redis_service.store_trip(user_id, trip_id, full_trip_data)
            
            # 返回时包含trip_id
            final_plan_dict = final_plan.model_dump()
            final_plan_dict["id"] = trip_id
            final_plan_dict["created_at"] = datetime.now().isoformat()
            final_plan = TripPlanResponse(**final_plan_dict)

        if not final_plan:
            raise BusinessException(
                ErrorCode.TRIP_PLAN_FAILED,
                details={"message": "无法生成行程计划，请检查日志获取更多信息"}
            )

        logger.info(
            f"行程规划成功",
            extra={
                "destination": request.destination,
                "trip_title": final_plan.trip_title,
                "days": len(final_plan.days),
                "user_id": user_id
            }
        )

        return final_plan

    except BusinessException:
        # 业务异常直接抛出，由全局异常处理器处理
        raise
    except Exception as e:
        # 其他异常包装为业务异常
        logger.error(
            f"处理/plan请求时发生意外错误: {e}",
            exc_info=True,
            extra={
                "destination": request.destination,
                "error_type": type(e).__name__,
                "user_id": user_id
            }
        )
        raise BusinessException(
            ErrorCode.TRIP_PLAN_FAILED,
            message=f"行程规划失败: {str(e)}",
            details={"error_type": type(e).__name__}
        )


@router.get("/list", response_model=List[TripPlanResponse])
def get_trip_list(http_request: Request):
    """
    获取用户的所有行程列表
    """
    user_id = get_user_id(http_request)
    
    logger.info(f"获取用户行程列表 - UserID: {user_id}")
    
    try:
        trips = redis_service.list_user_trips(user_id)
        logger.info(f"成功获取行程列表 - UserID: {user_id}, Count: {len(trips)}")
        return trips
    except Exception as e:
        logger.error(f"获取行程列表失败: {str(e)}")
        raise BusinessException(ErrorCode.TRIP_PLAN_FAILED, message="获取行程列表失败")


@router.get("/{trip_id}", response_model=TripPlanResponse)
def get_trip(trip_id: str, http_request: Request):
    """
    获取指定行程的完整数据
    """
    user_id = get_user_id(http_request)
    
    logger.info(f"获取行程详情 - UserID: {user_id}, TripID: {trip_id}")
    
    try:
        trip_data = redis_service.get_trip(trip_id)
        
        if not trip_data:
            logger.warning(f"行程不存在 - TripID: {trip_id}")
            raise HTTPException(status_code=404, detail="行程不存在")
        
        logger.info(f"成功获取行程详情 - TripID: {trip_id}")
        return TripPlanResponse(**trip_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取行程详情失败: {str(e)}")
        raise BusinessException(ErrorCode.TRIP_PLAN_FAILED, message="获取行程详情失败")


@router.delete("/{trip_id}")
def delete_trip(trip_id: str, http_request: Request):
    """
    删除指定行程
    """
    user_id = get_user_id(http_request)
    
    logger.info(f"删除行程 - UserID: {user_id}, TripID: {trip_id}")
    
    try:
        success = redis_service.delete_trip(user_id, trip_id)
        
        if not success:
            logger.warning(f"行程不存在或删除失败 - TripID: {trip_id}")
            raise HTTPException(status_code=404, detail="行程不存在或删除失败")
        
        logger.info(f"成功删除行程 - TripID: {trip_id}")
        return {"message": "行程已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除行程失败: {str(e)}")
        raise BusinessException(ErrorCode.TRIP_PLAN_FAILED, message="删除行程失败")