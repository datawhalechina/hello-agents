"""
MCP工具包装器 - 将单个MCP工具包装成HelloAgents Tool

这个模块将MCP服务器的每个工具展开为独立的HelloAgents Tool对象，
使得Agent可以像调用普通工具一样调用MCP工具。
"""

from typing import Dict, Any, Optional, List
from ..base import Tool, ToolParameter


class MCPWrappedTool(Tool):
    """
    MCP工具包装器 - 将单个MCP工具包装成HelloAgents Tool
    
    这个类将MCP服务器的一个工具（如 read_file）包装成一个独立的Tool对象。
    Agent调用时只需提供参数，无需了解MCP的内部结构。
    
    示例：
        >>> # 内部使用，由MCPTool自动创建
        >>> wrapped_tool = MCPWrappedTool(
        ...     mcp_tool=mcp_tool_instance,
        ...     tool_info={
        ...         "name": "read_file",
        ...         "description": "Read a file...",
        ...         "input_schema": {...}
        ...     }
        ... )
    """
    
    def __init__(self,
                 mcp_tool: 'MCPTool',  # type: ignore
                 tool_info: Dict[str, Any],
                 prefix: str = ""):
        """
        初始化MCP包装工具

        Args:
            mcp_tool: 父MCP工具实例
            tool_info: MCP工具信息（包含name, description, input_schema）
            prefix: 工具名前缀（如 "filesystem_"）
        """
        self.mcp_tool = mcp_tool
        self.tool_info = tool_info
        self.mcp_tool_name = tool_info.get('name', 'unknown')

        # 构建工具名：prefix + mcp_tool_name
        tool_name = f"{prefix}{self.mcp_tool_name}" if prefix else self.mcp_tool_name

        # 获取描述
        description = tool_info.get('description', f'MCP工具: {self.mcp_tool_name}')

        # 解析参数schema
        self._parameters = self._parse_input_schema(tool_info.get('input_schema', {}))

        # 初始化父类
        super().__init__(
            name=tool_name,
            description=description
        )
    
    def _parse_input_schema(self, input_schema: Dict[str, Any]) -> List[ToolParameter]:
        """
        将MCP的input_schema转换为HelloAgents的ToolParameter列表

        Args:
            input_schema: MCP工具的input_schema（JSON Schema格式）

        Returns:
            ToolParameter列表
        """
        parameters = []

        properties = input_schema.get('properties', {})
        required_fields = input_schema.get('required', [])

        for param_name, param_info in properties.items():
            param_type = param_info.get('type', 'string')
            param_desc = param_info.get('description', '')
            is_required = param_name in required_fields

            parameters.append(ToolParameter(
                name=param_name,
                type=param_type,  # 直接使用JSON Schema的类型字符串
                description=param_desc,
                required=is_required
            ))

        return parameters
    
    def get_parameters(self) -> List[ToolParameter]:
        """
        获取工具参数定义

        Returns:
            ToolParameter列表
        """
        return self._parameters

    def run(self, params: Dict[str, Any]) -> str:
        """
        执行MCP工具

        Args:
            params: 工具参数（直接传递给MCP工具）

        Returns:
            执行结果
        """
        # 构建MCP调用参数
        mcp_params = {
            "action": "call_tool",
            "tool_name": self.mcp_tool_name,
            "arguments": params
        }

        # 调用父MCP工具
        return self.mcp_tool.run(mcp_params)

