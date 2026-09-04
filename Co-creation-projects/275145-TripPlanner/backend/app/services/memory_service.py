"""
记忆服务模块
提供用户记忆、知识记忆的存储、检索和更新功能
"""
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path
from app.observability.logger import default_logger as logger


class MemoryService:
    """
    记忆服务
    管理用户记忆和知识记忆
    """
    
    def __init__(self, memory_dir: str = "memory"):
        """
        初始化记忆服务
        
        Args:
            memory_dir: 记忆数据存储目录
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        # 用户记忆文件
        self.user_memory_file = self.memory_dir / "user_memory.json"
        # 知识记忆文件
        self.knowledge_memory_file = self.memory_dir / "knowledge_memory.json"
        
        # 加载记忆
        self.user_memory = self._load_user_memory()
        self.knowledge_memory = self._load_knowledge_memory()
        
        logger.info("记忆服务初始化完成")
    
    def _load_user_memory(self) -> Dict[str, Any]:
        """加载用户记忆"""
        if self.user_memory_file.exists():
            try:
                with open(self.user_memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载用户记忆失败: {e}")
                return {}
        return {}
    
    def _load_knowledge_memory(self) -> Dict[str, Any]:
        """加载知识记忆"""
        if self.knowledge_memory_file.exists():
            try:
                with open(self.knowledge_memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载知识记忆失败: {e}")
                return {}
        return {}
    
    def _save_user_memory(self):
        """保存用户记忆"""
        try:
            with open(self.user_memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户记忆失败: {e}")
    
    def _save_knowledge_memory(self):
        """保存知识记忆"""
        try:
            with open(self.knowledge_memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge_memory, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存知识记忆失败: {e}")
    
    # ============ 用户记忆操作 ============
    
    def store_user_preference(
        self,
        user_id: str,
        preference_type: str,
        preference_data: Dict[str, Any]
    ):
        """
        存储用户偏好
        
        Args:
            user_id: 用户ID（可以是session_id或真实用户ID）
            preference_type: 偏好类型（如：destination_preference, budget_preference等）
            preference_data: 偏好数据
        """
        if user_id not in self.user_memory:
            self.user_memory[user_id] = {
                "long_term_memory": {},
                "short_term_memory": {},
                "meta_memory": {
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                }
            }
        
        if "long_term_memory" not in self.user_memory[user_id]:
            self.user_memory[user_id]["long_term_memory"] = {}
        
        if preference_type not in self.user_memory[user_id]["long_term_memory"]:
            self.user_memory[user_id]["long_term_memory"][preference_type] = []
        
        # 添加时间戳
        preference_data["timestamp"] = datetime.now().isoformat()
        self.user_memory[user_id]["long_term_memory"][preference_type].append(preference_data)
        
        # 更新元记忆
        self.user_memory[user_id]["meta_memory"]["last_updated"] = datetime.now().isoformat()
        
        self._save_user_memory()
        logger.info(f"已存储用户偏好 - UserID: {user_id}, Type: {preference_type}")
    
    def store_user_feedback(
        self,
        user_id: str,
        trip_id: str,
        feedback_data: Dict[str, Any]
    ):
        """
        存储用户反馈
        
        Args:
            user_id: 用户ID
            trip_id: 行程ID
            feedback_data: 反馈数据（包含rating, comments, modifications等）
        """
        if user_id not in self.user_memory:
            self.user_memory[user_id] = {
                "long_term_memory": {},
                "short_term_memory": {},
                "meta_memory": {}
            }
        
        if "feedback_history" not in self.user_memory[user_id]["long_term_memory"]:
            self.user_memory[user_id]["long_term_memory"]["feedback_history"] = []
        
        feedback_entry = {
            "trip_id": trip_id,
            "timestamp": datetime.now().isoformat(),
            **feedback_data
        }
        self.user_memory[user_id]["long_term_memory"]["feedback_history"].append(feedback_entry)
        
        self._save_user_memory()
        logger.info(f"已存储用户反馈 - UserID: {user_id}, TripID: {trip_id}")
    
    def store_short_term_context(
        self,
        user_id: str,
        context_key: str,
        context_data: Any
    ):
        """
        存储短期上下文
        
        Args:
            user_id: 用户ID
            context_key: 上下文键
            context_data: 上下文数据
        """
        if user_id not in self.user_memory:
            self.user_memory[user_id] = {
                "long_term_memory": {},
                "short_term_memory": {},
                "meta_memory": {}
            }
        
        self.user_memory[user_id]["short_term_memory"][context_key] = {
            "data": context_data,
            "timestamp": datetime.now().isoformat()
        }
        
        self._save_user_memory()
    
    def retrieve_user_preferences(
        self,
        user_id: str,
        preference_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        检索用户偏好
        
        Args:
            user_id: 用户ID
            preference_type: 偏好类型，如果为None则返回所有偏好
        
        Returns:
            用户偏好数据
        """
        if user_id not in self.user_memory:
            return {}
        
        long_term = self.user_memory[user_id].get("long_term_memory", {})
        
        if preference_type:
            return long_term.get(preference_type, [])
        else:
            return long_term
    
    def retrieve_user_feedback(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        检索用户反馈历史
        
        Args:
            user_id: 用户ID
            limit: 返回数量限制
        
        Returns:
            反馈历史列表
        """
        if user_id not in self.user_memory:
            return []
        
        feedback_history = self.user_memory[user_id].get("long_term_memory", {}).get("feedback_history", [])
        return feedback_history[-limit:]
    
    def retrieve_short_term_context(
        self,
        user_id: str,
        context_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        检索短期上下文
        
        Args:
            user_id: 用户ID
            context_key: 上下文键，如果为None则返回所有上下文
        
        Returns:
            上下文数据
        """
        if user_id not in self.user_memory:
            return {}
        
        short_term = self.user_memory[user_id].get("short_term_memory", {})
        
        if context_key:
            return short_term.get(context_key, {})
        else:
            return short_term
    
    def retrieve_similar_trips(
        self,
        destination: str,
        preferences: List[str],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        检索相似的历史行程
        
        Args:
            destination: 目的地
            preferences: 偏好列表
            limit: 返回数量限制
        
        Returns:
            相似行程列表
        """
        similar_trips = []
        
        for user_id, user_data in self.user_memory.items():
            feedback_history = user_data.get("long_term_memory", {}).get("feedback_history", [])
            
            for feedback in feedback_history:
                trip_data = feedback.get("trip_data", {})
                if not trip_data:
                    continue
                
                # 简单的相似度计算
                trip_destination = trip_data.get("destination", "")
                trip_preferences = trip_data.get("preferences", [])
                
                # 目的地匹配
                if destination.lower() not in trip_destination.lower():
                    continue
                
                # 偏好匹配度
                preference_match = len(set(preferences) & set(trip_preferences))
                
                if preference_match > 0:
                    similar_trips.append({
                        "trip_data": trip_data,
                        "feedback": feedback,
                        "match_score": preference_match,
                        "user_id": user_id
                    })
        
        # 按匹配度排序
        similar_trips.sort(key=lambda x: x["match_score"], reverse=True)
        return similar_trips[:limit]
    
    # ============ 知识记忆操作 ============
    
    def store_destination_knowledge(
        self,
        destination: str,
        knowledge_data: Dict[str, Any]
    ):
        """
        存储目的地知识
        
        Args:
            destination: 目的地名称
            knowledge_data: 知识数据（包含特色、季节特点、文化背景等）
        """
        if "destinations" not in self.knowledge_memory:
            self.knowledge_memory["destinations"] = {}
        
        if destination not in self.knowledge_memory["destinations"]:
            self.knowledge_memory["destinations"][destination] = {
                "created_at": datetime.now().isoformat(),
                "knowledge": []
            }
        
        knowledge_entry = {
            "timestamp": datetime.now().isoformat(),
            **knowledge_data
        }
        self.knowledge_memory["destinations"][destination]["knowledge"].append(knowledge_entry)
        self.knowledge_memory["destinations"][destination]["last_updated"] = datetime.now().isoformat()
        
        self._save_knowledge_memory()
        logger.info(f"已存储目的地知识 - Destination: {destination}")
    
    def retrieve_destination_knowledge(
        self,
        destination: str
    ) -> Dict[str, Any]:
        """
        检索目的地知识
        
        Args:
            destination: 目的地名称
        
        Returns:
            目的地知识数据
        """
        destinations = self.knowledge_memory.get("destinations", {})
        return destinations.get(destination, {})
    
    def store_experience(
        self,
        experience_type: str,
        experience_data: Dict[str, Any]
    ):
        """
        存储经验（成功案例、失败教训等）
        
        Args:
            experience_type: 经验类型（success_case, failure_lesson, optimization_strategy等）
            experience_data: 经验数据
        """
        if "experiences" not in self.knowledge_memory:
            self.knowledge_memory["experiences"] = {}
        
        if experience_type not in self.knowledge_memory["experiences"]:
            self.knowledge_memory["experiences"][experience_type] = []
        
        experience_entry = {
            "timestamp": datetime.now().isoformat(),
            **experience_data
        }
        self.knowledge_memory["experiences"][experience_type].append(experience_entry)
        
        self._save_knowledge_memory()
        logger.info(f"已存储经验 - Type: {experience_type}")
    
    def retrieve_experiences(
        self,
        experience_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        检索经验
        
        Args:
            experience_type: 经验类型，如果为None则返回所有类型
            limit: 返回数量限制
        
        Returns:
            经验列表
        """
        experiences = self.knowledge_memory.get("experiences", {})
        
        if experience_type:
            return experiences.get(experience_type, [])[-limit:]
        else:
            all_experiences = []
            for exp_type, exp_list in experiences.items():
                all_experiences.extend(exp_list)
            all_experiences.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            return all_experiences[:limit]
    
    # ============ 综合检索 ============
    
    def search_memory(
        self,
        query: str,
        user_id: Optional[str] = None,
        memory_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        综合搜索记忆
        
        Args:
            query: 搜索查询
            user_id: 用户ID（可选）
            memory_types: 记忆类型列表（可选）
        
        Returns:
            搜索结果
        """
        results = {
            "user_memory": {},
            "knowledge_memory": {}
        }
        
        # 搜索用户记忆
        if user_id and user_id in self.user_memory:
            user_data = self.user_memory[user_id]
            
            # 搜索长期记忆
            long_term = user_data.get("long_term_memory", {})
            for key, value in long_term.items():
                if isinstance(value, list):
                    for item in value:
                        if query.lower() in str(item).lower():
                            if key not in results["user_memory"]:
                                results["user_memory"][key] = []
                            results["user_memory"][key].append(item)
            
            # 搜索短期记忆
            short_term = user_data.get("short_term_memory", {})
            for key, value in short_term.items():
                if query.lower() in str(value).lower():
                    results["user_memory"][f"short_term_{key}"] = value
        
        # 搜索知识记忆
        destinations = self.knowledge_memory.get("destinations", {})
        for dest, data in destinations.items():
            if query.lower() in dest.lower():
                results["knowledge_memory"][dest] = data
        
        return results


# 创建全局记忆服务实例
memory_service = MemoryService()

