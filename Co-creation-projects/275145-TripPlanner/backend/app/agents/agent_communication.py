"""
智能体通信模块
实现智能体之间的消息传递和协商机制
"""
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from datetime import datetime
from app.observability.logger import default_logger as logger


class MessageType(Enum):
    """消息类型"""
    QUERY = "query"  # 查询
    SUGGESTION = "suggestion"  # 建议
    NEGOTIATION = "negotiation"  # 协商
    FEEDBACK = "feedback"  # 反馈
    RESULT = "result"  # 结果
    REQUEST = "request"  # 请求


class AgentMessage:
    """智能体消息"""
    
    def __init__(
        self,
        sender: str,
        receiver: str,
        message_type: MessageType,
        content: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ):
        """
        初始化消息
        
        Args:
            sender: 发送者名称
            receiver: 接收者名称
            message_type: 消息类型
            content: 消息内容
            context: 上下文信息
        """
        self.sender = sender
        self.receiver = receiver
        self.message_type = message_type
        self.content = content
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()
        self.message_id = f"{sender}_{receiver}_{int(datetime.now().timestamp())}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type.value,
            "content": self.content,
            "context": self.context,
            "timestamp": self.timestamp
        }


class AgentCommunicationHub:
    """
    智能体通信中心
    管理智能体之间的消息传递
    """
    
    def __init__(self):
        """初始化通信中心"""
        self.agents: Dict[str, Any] = {}  # 注册的智能体
        self.message_history: List[AgentMessage] = []
        self.message_handlers: Dict[str, Dict[MessageType, Callable]] = {}
        logger.info("智能体通信中心初始化完成")
    
    def register_agent(self, agent_name: str, agent_instance: Any):
        """
        注册智能体
        
        Args:
            agent_name: 智能体名称
            agent_instance: 智能体实例
        """
        self.agents[agent_name] = agent_instance
        self.message_handlers[agent_name] = {}
        logger.info(f"智能体已注册 - Name: {agent_name}")
    
    def register_message_handler(
        self,
        agent_name: str,
        message_type: MessageType,
        handler: Callable
    ):
        """
        注册消息处理器
        
        Args:
            agent_name: 智能体名称
            message_type: 消息类型
            handler: 处理函数
        """
        if agent_name not in self.message_handlers:
            self.message_handlers[agent_name] = {}
        
        self.message_handlers[agent_name][message_type] = handler
        logger.debug(f"消息处理器已注册 - Agent: {agent_name}, Type: {message_type.value}")
    
    def send_message(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """
        发送消息
        
        Args:
            message: 消息对象
        
        Returns:
            响应内容（如果有）
        """
        # 记录消息历史
        self.message_history.append(message)
        
        # 检查接收者是否存在
        if message.receiver not in self.agents:
            logger.warning(f"接收者不存在 - Receiver: {message.receiver}")
            return None
        
        # 查找消息处理器
        handlers = self.message_handlers.get(message.receiver, {})
        handler = handlers.get(message.message_type)
        
        if handler:
            try:
                response = handler(message)
                logger.debug(
                    f"消息已处理 - From: {message.sender}, To: {message.receiver}, "
                    f"Type: {message.message_type.value}"
                )
                return response
            except Exception as e:
                logger.error(f"消息处理失败: {e}", exc_info=True)
                return None
        else:
            # 如果没有注册处理器，尝试直接调用智能体的处理方法
            agent = self.agents[message.receiver]
            if hasattr(agent, 'handle_message'):
                try:
                    response = agent.handle_message(message)
                    return response
                except Exception as e:
                    logger.error(f"智能体消息处理失败: {e}", exc_info=True)
                    return None
        
        logger.warning(f"未找到消息处理器 - Receiver: {message.receiver}, Type: {message.message_type.value}")
        return None
    
    def broadcast_message(
        self,
        sender: str,
        message_type: MessageType,
        content: Dict[str, Any],
        exclude: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        广播消息给所有智能体
        
        Args:
            sender: 发送者名称
            message_type: 消息类型
            content: 消息内容
            exclude: 排除的智能体列表
        
        Returns:
            响应列表
        """
        exclude = exclude or []
        responses = []
        
        for agent_name in self.agents.keys():
            if agent_name == sender or agent_name in exclude:
                continue
            
            message = AgentMessage(
                sender=sender,
                receiver=agent_name,
                message_type=message_type,
                content=content
            )
            
            response = self.send_message(message)
            if response:
                responses.append({
                    "agent": agent_name,
                    "response": response
                })
        
        return responses
    
    def negotiate(
        self,
        initiator: str,
        participants: List[str],
        topic: str,
        proposals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        协商机制
        
        Args:
            initiator: 发起者
            participants: 参与者列表
            topic: 协商主题
            proposals: 提案
        
        Returns:
            协商结果
        """
        logger.info(f"开始协商 - Initiator: {initiator}, Topic: {topic}, Participants: {participants}")
        
        negotiation_round = 1
        max_rounds = 3
        consensus = False
        final_proposal = proposals
        
        while negotiation_round <= max_rounds and not consensus:
            logger.debug(f"协商第 {negotiation_round} 轮")
            
            responses = {}
            for participant in participants:
                if participant not in self.agents:
                    continue
                
                message = AgentMessage(
                    sender=initiator,
                    receiver=participant,
                    message_type=MessageType.NEGOTIATION,
                    content={
                        "topic": topic,
                        "proposal": final_proposal,
                        "round": negotiation_round
                    }
                )
                
                response = self.send_message(message)
                if response:
                    responses[participant] = response
            
            # 检查是否达成共识
            if len(responses) == len(participants):
                # 简单的共识检查：所有参与者都同意
                all_agree = all(
                    resp.get("status") == "agree" or resp.get("agreement", False)
                    for resp in responses.values()
                )
                
                if all_agree:
                    consensus = True
                    logger.info(f"协商达成共识 - Round: {negotiation_round}")
                else:
                    # 整合反馈，调整提案
                    feedback = [resp.get("feedback", {}) for resp in responses.values()]
                    final_proposal = self._integrate_feedback(final_proposal, feedback)
                    negotiation_round += 1
            else:
                break
        
        return {
            "consensus": consensus,
            "final_proposal": final_proposal,
            "rounds": negotiation_round,
            "responses": responses
        }
    
    def _integrate_feedback(
        self,
        proposal: Dict[str, Any],
        feedback_list: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        整合反馈，调整提案
        
        Args:
            proposal: 原始提案
            feedback_list: 反馈列表
        
        Returns:
            调整后的提案
        """
        # 简单的反馈整合逻辑
        # 实际应用中可以使用更复杂的策略
        adjusted_proposal = proposal.copy()
        
        for feedback in feedback_list:
            if "suggestions" in feedback:
                for key, value in feedback["suggestions"].items():
                    if key in adjusted_proposal:
                        # 简单的平均值调整
                        if isinstance(adjusted_proposal[key], (int, float)) and isinstance(value, (int, float)):
                            adjusted_proposal[key] = (adjusted_proposal[key] + value) / 2
                        else:
                            adjusted_proposal[key] = value
        
        return adjusted_proposal
    
    def get_message_history(
        self,
        agent_name: Optional[str] = None,
        message_type: Optional[MessageType] = None
    ) -> List[AgentMessage]:
        """
        获取消息历史
        
        Args:
            agent_name: 智能体名称（可选）
            message_type: 消息类型（可选）
        
        Returns:
            消息列表
        """
        filtered_messages = self.message_history
        
        if agent_name:
            filtered_messages = [
                msg for msg in filtered_messages
                if msg.sender == agent_name or msg.receiver == agent_name
            ]
        
        if message_type:
            filtered_messages = [
                msg for msg in filtered_messages
                if msg.message_type == message_type
            ]
        
        return filtered_messages


# 创建全局通信中心实例
communication_hub = AgentCommunicationHub()

