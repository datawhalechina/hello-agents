"""
协议工具集合

提供基于协议实现的工具接口：
- MCP Tool: 基于 fastmcp 库，用于连接和调用 MCP 服务器
- A2A Tool: 基于官方 a2a 库，用于 Agent 间通信（需要安装 a2a）
- ANP Tool: 基于概念实现，用于服务发现和网络管理
"""

from typing import Dict, Any, List, Optional
from ..base import Tool, ToolParameter
import os

# todo: 修改by xc
import gc
import asyncio
import sys
if sys.platform == "win32":
    # Windows 10+: 使用 SelectorEventLoop 替代 ProactorEventLoop，
    # 可避免 GetQueuedCompletionStatus 阻塞问题
    if sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(
            asyncio.WindowsSelectorEventLoopPolicy()
        )
        

# MCP服务器环境变量映射表
# 用于自动检测常见MCP服务器需要的环境变量
MCP_SERVER_ENV_MAP = {
    "server-github": ["GITHUB_PERSONAL_ACCESS_TOKEN"],
    "server-slack": ["SLACK_BOT_TOKEN", "SLACK_TEAM_ID"],
    "server-google-drive": ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"],
    "server-postgres": ["POSTGRES_CONNECTION_STRING"],
    "server-sqlite": [],  # 不需要环境变量
    "server-filesystem": [],  # 不需要环境变量
}


class MCPTool(Tool):
    """MCP (Model Context Protocol) 工具

    连接到 MCP 服务器并调用其提供的工具、资源和提示词。
    
    功能：
    - 列出服务器提供的工具
    - 调用服务器工具
    - 读取服务器资源
    - 获取提示词模板

    使用示例:
        >>> from hello_agents.tools.builtin import MCPTool
        >>>
        >>> # 方式1: 使用内置演示服务器
        >>> tool = MCPTool()  # 自动创建内置服务器
        >>> result = tool.run({"action": "list_tools"})
        >>>
        >>> # 方式2: 连接到外部 MCP 服务器
        >>> tool = MCPTool(server_command=["python", "examples/mcp_example.py"])
        >>> result = tool.run({"action": "list_tools"})
        >>>
        >>> # 方式3: 使用自定义 FastMCP 服务器
        >>> from fastmcp import FastMCP
        >>> server = FastMCP("MyServer")
        >>> tool = MCPTool(server=server)

    注意：使用 fastmcp 库，已包含在依赖中
    """
    
    def __init__(self,
                 name: str = "mcp",
                 description: Optional[str] = None,
                 server_command: Optional[List[str]] = None,
                 server_args: Optional[List[str]] = None,
                 server: Optional[Any] = None,
                 auto_expand: bool = True,
                 env: Optional[Dict[str, str]] = None,
                 env_keys: Optional[List[str]] = None):
        """
        初始化 MCP 工具

        Args:
            name: 工具名称（默认为"mcp"，建议为不同服务器指定不同名称）
            description: 工具描述（可选，默认为通用描述）
            server_command: 服务器启动命令（如 ["python", "server.py"]）
            server_args: 服务器参数列表
            server: FastMCP 服务器实例（可选，用于内存传输）
            auto_expand: 是否自动展开为独立工具（默认True）
            env: 环境变量字典（优先级最高，直接传递给MCP服务器）
            env_keys: 要从系统环境变量加载的key列表（优先级中等）

        环境变量优先级（从高到低）：
            1. 直接传递的env参数
            2. env_keys指定的环境变量
            3. 自动检测的环境变量（根据server_command）

        注意：如果所有参数都为空，将创建内置演示服务器

        示例：
            >>> # 方式1：直接传递环境变量（优先级最高）
            >>> github_tool = MCPTool(
            ...     name="github",
            ...     server_command=["npx", "-y", "@modelcontextprotocol/server-github"],
            ...     env={"GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"}
            ... )
            >>>
            >>> # 方式2：从.env文件加载指定的环境变量
            >>> github_tool = MCPTool(
            ...     name="github",
            ...     server_command=["npx", "-y", "@modelcontextprotocol/server-github"],
            ...     env_keys=["GITHUB_PERSONAL_ACCESS_TOKEN"]
            ... )
            >>>
            >>> # 方式3：自动检测（最简单，推荐）
            >>> github_tool = MCPTool(
            ...     name="github",
            ...     server_command=["npx", "-y", "@modelcontextprotocol/server-github"]
            ...     # 自动从环境变量加载GITHUB_PERSONAL_ACCESS_TOKEN
            ... )
        """
        self.server_command = server_command
        self.server_args = server_args or []
        self.server = server
        self._client = None
        self._available_tools = []
        self.auto_expand = auto_expand
        self.prefix = f"{name}_" if auto_expand else ""

        # 环境变量处理（优先级：env > env_keys > 自动检测）
        self.env = self._prepare_env(env, env_keys, server_command)

        # 如果没有指定任何服务器，创建内置演示服务器
        if not server_command and not server:
            self.server = self._create_builtin_server()

        # 自动发现工具
        self._discover_tools()

        # 设置默认描述或自动生成
        if description is None:
            description = self._generate_description()

        super().__init__(
            name=name,
            description=description
        )

    def _prepare_env(self,
                     env: Optional[Dict[str, str]],
                     env_keys: Optional[List[str]],
                     server_command: Optional[List[str]]) -> Dict[str, str]:
        """
        准备环境变量

        优先级：env > env_keys > 自动检测

        Args:
            env: 直接传递的环境变量字典
            env_keys: 要从系统环境变量加载的key列表
            server_command: 服务器命令（用于自动检测）

        Returns:
            合并后的环境变量字典
        """
        result_env = {}

        # 1. 自动检测（优先级最低）
        if server_command:
            # 从命令中提取服务器名称
            server_name = None
            for part in server_command:
                if "server-" in part:
                    # 提取类似 "@modelcontextprotocol/server-github" 中的 "server-github"
                    server_name = part.split("/")[-1] if "/" in part else part
                    break

            # 查找映射表
            if server_name and server_name in MCP_SERVER_ENV_MAP:
                auto_keys = MCP_SERVER_ENV_MAP[server_name]
                for key in auto_keys:
                    value = os.getenv(key)
                    if value:
                        result_env[key] = value
                        print(f"🔑 自动加载环境变量: {key}")

        # 2. env_keys指定的环境变量（优先级中等）
        if env_keys:
            for key in env_keys:
                value = os.getenv(key)
                if value:
                    result_env[key] = value
                    print(f"🔑 从env_keys加载环境变量: {key}")
                else:
                    print(f"⚠️  警告: 环境变量 {key} 未设置")

        # 3. 直接传递的env（优先级最高）
        if env:
            result_env.update(env)
            for key in env.keys():
                print(f"🔑 使用直接传递的环境变量: {key}")

        return result_env

    def _create_builtin_server(self):
        """创建内置演示服务器"""
        try:
            from fastmcp import FastMCP

            server = FastMCP("HelloAgents-BuiltinServer")

            @server.tool()
            def add(a: float, b: float) -> float:
                """加法计算器"""
                return a + b

            @server.tool()
            def subtract(a: float, b: float) -> float:
                """减法计算器"""
                return a - b

            @server.tool()
            def multiply(a: float, b: float) -> float:
                """乘法计算器"""
                return a * b

            @server.tool()
            def divide(a: float, b: float) -> float:
                """除法计算器"""
                if b == 0:
                    raise ValueError("除数不能为零")
                return a / b

            @server.tool()
            def greet(name: str = "World") -> str:
                """友好问候"""
                return f"Hello, {name}! 欢迎使用 HelloAgents MCP 工具！"

            @server.tool()
            def get_system_info() -> dict:
                """获取系统信息"""
                import platform
                import sys
                return {
                    "platform": platform.system(),
                    "python_version": sys.version,
                    "server_name": "HelloAgents-BuiltinServer",
                    "tools_count": 6
                }

            return server

        except ImportError:
            raise ImportError(
                "创建内置 MCP 服务器需要 fastmcp 库。请安装: pip install fastmcp"
            )

    def _discover_tools(self):
        """发现MCP服务器提供的所有工具"""
        try:
            from hello_agents.protocols.mcp.client import MCPClient
            import asyncio

            async def discover():
                client_source = self.server if self.server else self.server_command
                async with MCPClient(client_source, self.server_args, env=self.env) as client:
                    tools = await client.list_tools()
                    return tools

            # 运行异步发现
            try:
                loop = asyncio.get_running_loop()
                # 如果已有循环，在新线程中运行
                import concurrent.futures
                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(discover())
                    finally:
                        new_loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    self._available_tools = future.result()
            except RuntimeError:
                # 没有运行中的循环
                self._available_tools = asyncio.run(discover())

        except Exception as e:
            # 工具发现失败不影响初始化
            self._available_tools = []

    def _generate_description(self) -> str:
        """生成增强的工具描述"""
        if not self._available_tools:
            return "连接到 MCP 服务器，调用工具、读取资源和获取提示词。支持内置服务器和外部服务器。"

        if self.auto_expand:
            # 展开模式：简单描述
            return f"MCP工具服务器，包含{len(self._available_tools)}个工具。这些工具会自动展开为独立的工具供Agent使用。"
        else:
            # 非展开模式：详细描述
            desc_parts = [
                f"MCP工具服务器，提供{len(self._available_tools)}个工具："
            ]

            # 列出所有工具
            for tool in self._available_tools:
                tool_name = tool.get('name', 'unknown')
                tool_desc = tool.get('description', '无描述')
                # 简化描述，只取第一句
                short_desc = tool_desc.split('.')[0] if tool_desc else '无描述'
                desc_parts.append(f"  • {tool_name}: {short_desc}")

            # 添加调用格式说明
            desc_parts.append("\n调用格式：返回JSON格式的参数")
            desc_parts.append('{"action": "call_tool", "tool_name": "工具名", "arguments": {...}}')

            # 添加示例
            if self._available_tools:
                first_tool = self._available_tools[0]
                tool_name = first_tool.get('name', 'example')
                desc_parts.append(f'\n示例：{{"action": "call_tool", "tool_name": "{tool_name}", "arguments": {{...}}}}')

            return "\n".join(desc_parts)

    def get_expanded_tools(self) -> List['Tool']:  # type: ignore
        """
        获取展开的工具列表

        将MCP服务器的每个工具包装成独立的Tool对象

        Returns:
            Tool对象列表
        """
        if not self.auto_expand:
            return []

        from .mcp_wrapper_tool import MCPWrappedTool

        expanded_tools = []
        for tool_info in self._available_tools:
            wrapped_tool = MCPWrappedTool(
                mcp_tool=self,
                tool_info=tool_info,
                prefix=self.prefix
            )
            expanded_tools.append(wrapped_tool)

        return expanded_tools

    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行 MCP 操作

        Args:
            parameters: 包含以下参数的字典
                - action: 操作类型 (list_tools, call_tool, list_resources, read_resource, list_prompts, get_prompt)
                  如果不指定action但指定了tool_name，会自动推断为call_tool
                - tool_name: 工具名称（call_tool 需要）
                - arguments: 工具参数（call_tool 需要）
                - uri: 资源 URI（read_resource 需要）
                - prompt_name: 提示词名称（get_prompt 需要）
                - prompt_arguments: 提示词参数（get_prompt 可选）

        Returns:
            操作结果
        """
        from hello_agents.protocols.mcp.client import MCPClient

        timeout = getattr(self, 'timeout', 10)

        # 智能推断action：如果没有action但有tool_name，自动设置为call_tool
        action = parameters.get("action", "").lower()
        if not action and "tool_name" in parameters:
            action = "call_tool"
            parameters["action"] = action

        if not action:
            return "错误：必须指定 action 参数或 tool_name 参数"
        
        try:
            # 使用增强的异步客户端
            import asyncio
            from hello_agents.protocols.mcp.client import MCPClient

            async def run_mcp_operation():
                # 根据配置选择客户端创建方式
                if self.server:
                    # 使用内置服务器（内存传输）
                    client_source = self.server
                else:
                    # 使用外部服务器命令
                    client_source = self.server_command

                async with MCPClient(client_source, self.server_args, env=self.env) as client:
                    if action == "list_tools":
                        tools = await client.list_tools()
                        if not tools:
                            return "没有找到可用的工具"
                        result = f"找到 {len(tools)} 个工具:\n"
                        for tool in tools:
                            result += f"- {tool['name']}: {tool['description']}\n"
                        return result

                    elif action == "call_tool":
                        tool_name = parameters.get("tool_name")
                        arguments = parameters.get("arguments", {})
                        if not tool_name:
                            return "错误：必须指定 tool_name 参数"
                        
                        # todo: 修改by xc
                        result = await asyncio.wait_for(client.call_tool(tool_name, arguments), timeout=timeout)
                        # result = await client.call_tool(tool_name, arguments)
                        return f"工具 '{tool_name}' 执行结果:\n{result}"

                    elif action == "list_resources":
                        resources = await client.list_resources()
                        if not resources:
                            return "没有找到可用的资源"
                        result = f"找到 {len(resources)} 个资源:\n"
                        for resource in resources:
                            result += f"- {resource['uri']}: {resource['name']}\n"
                        return result

                    elif action == "read_resource":
                        uri = parameters.get("uri")
                        if not uri:
                            return "错误：必须指定 uri 参数"
                        content = await client.read_resource(uri)
                        return f"资源 '{uri}' 内容:\n{content}"

                    elif action == "list_prompts":
                        prompts = await client.list_prompts()
                        if not prompts:
                            return "没有找到可用的提示词"
                        result = f"找到 {len(prompts)} 个提示词:\n"
                        for prompt in prompts:
                            result += f"- {prompt['name']}: {prompt['description']}\n"
                        return result

                    elif action == "get_prompt":
                        prompt_name = parameters.get("prompt_name")
                        prompt_arguments = parameters.get("prompt_arguments", {})
                        if not prompt_name:
                            return "错误：必须指定 prompt_name 参数"
                        messages = await client.get_prompt(prompt_name, prompt_arguments)
                        result = f"提示词 '{prompt_name}':\n"
                        for msg in messages:
                            result += f"[{msg['role']}] {msg['content']}\n"
                        return result

                    else:
                        return f"错误：不支持的操作 '{action}'"

            # 运行异步操作
            try:
                # 检查是否已有运行中的事件循环
                try:
                    loop = asyncio.get_running_loop()
                    # 如果有运行中的循环，在新线程中运行新的事件循环
                    import concurrent.futures
                    import threading

                    def run_in_thread():
                        # 在新线程中创建新的事件循环
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            return new_loop.run_until_complete(run_mcp_operation())
                        finally:
                            # todo: 修改by xc
                            # 🔑 关键清理 1：取消所有残留任务，防止 transport 未关闭
                            pending = asyncio.all_tasks(new_loop)
                            for task in pending:
                                task.cancel()
                            if pending:
                                new_loop.run_until_complete(
                                    asyncio.gather(*pending, return_exceptions=True)
                                )

                            new_loop.close()

                    # todo: 修改by xc
                    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                    try:
                        future = executor.submit(run_in_thread)
                        # 🔑 关键清理 2：设置超时，避免永久阻塞
                        return future.result(timeout=timeout)
                    finally:
                        # 🔑 关键清理 3：不等待残留线程，直接关闭线程池
                        executor.shutdown(wait=False, cancel_futures=True)

                except RuntimeError:
                    # 没有运行中的循环，直接运行
                    return asyncio.run(run_mcp_operation())
            except Exception as e:
                return f"异步操作失败: {str(e)}"
            finally:
                # todo: 修改by xc
                # 🔑 关键清理 4：强制回收未关闭的管道/文件描述符
                gc.collect()

        except Exception as e:
            return f"MCP 操作失败: {str(e)}"
    
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型: list_tools, call_tool, list_resources, read_resource, list_prompts, get_prompt",
                required=True
            ),
            ToolParameter(
                name="tool_name",
                type="string",
                description="工具名称（call_tool 操作需要）",
                required=False
            ),
            ToolParameter(
                name="arguments",
                type="object",
                description="工具参数（call_tool 操作需要）",
                required=False
            ),
            ToolParameter(
                name="uri",
                type="string",
                description="资源 URI（read_resource 操作需要）",
                required=False
            ),
            ToolParameter(
                name="prompt_name",
                type="string",
                description="提示词名称（get_prompt 操作需要）",
                required=False
            ),
            ToolParameter(
                name="prompt_arguments",
                type="object",
                description="提示词参数（get_prompt 操作可选）",
                required=False
            )
        ]


class A2ATool(Tool):
    """A2A (Agent-to-Agent Protocol) 工具

    连接到 A2A Agent 并进行通信。
    
    功能：
    - 向 Agent 提问
    - 获取 Agent 信息
    - 发送自定义消息

    使用示例:
        >>> from hello_agents.tools.builtin import A2ATool
        >>> # 连接到 A2A Agent（使用默认名称）
        >>> tool = A2ATool(agent_url="http://localhost:5000")
        >>> # 连接到 A2A Agent（自定义名称和描述）
        >>> tool = A2ATool(
        ...     agent_url="http://localhost:5000",
        ...     name="tech_expert",
        ...     description="技术专家，回答技术相关问题"
        ... )
        >>> # 提问
        >>> result = tool.run({"action": "ask", "question": "计算 2+2"})
        >>> # 获取信息
        >>> result = tool.run({"action": "get_info"})
    
    注意：需要安装官方 a2a-sdk 库: pip install a2a-sdk
    详见文档: docs/chapter10/A2A_GUIDE.md
    官方仓库: https://github.com/a2aproject/a2a-python
    """
    
    def __init__(self, agent_url: str, name: str = "a2a", description: str = None):
        """
        初始化 A2A 工具

        Args:
            agent_url: Agent URL
            name: 工具名称（可选，默认为 "a2a"）
            description: 工具描述（可选）
        """
        if description is None:
            description = "连接到 A2A Agent，支持提问和获取信息。需要安装官方 a2a-sdk 库。"

        super().__init__(
            name=name,
            description=description
        )
        self.agent_url = agent_url
        
    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行 A2A 操作
        
        Args:
            parameters: 包含以下参数的字典
                - action: 操作类型 (ask, get_info)
                - question: 问题文本（ask 需要）
        
        Returns:
            操作结果
        """
        try:
            from hello_agents.protocols.a2a.implementation import A2AClient, A2A_AVAILABLE
            if not A2A_AVAILABLE:
                return ("错误：需要安装 a2a-sdk 库\n"
                       "安装命令: pip install a2a-sdk\n"
                       "详见文档: docs/chapter10/A2A_GUIDE.md\n"
                       "官方仓库: https://github.com/a2aproject/a2a-python")
        except ImportError:
            return ("错误：无法导入 A2A 模块\n"
                   "安装命令: pip install a2a-sdk\n"
                   "详见文档: docs/chapter10/A2A_GUIDE.md\n"
                   "官方仓库: https://github.com/a2aproject/a2a-python")

        action = parameters.get("action", "").lower()
        
        if not action:
            return "错误：必须指定 action 参数"
        
        try:
            client = A2AClient(self.agent_url)
            
            if action == "ask":
                question = parameters.get("question")
                if not question:
                    return "错误：必须指定 question 参数"
                response = client.ask(question)
                return f"Agent 回答:\n{response}"
                
            elif action == "get_info":
                info = client.get_info()
                result = "Agent 信息:\n"
                for key, value in info.items():
                    result += f"- {key}: {value}\n"
                return result
                
            else:
                return f"错误：不支持的操作 '{action}'"
                
        except Exception as e:
            return f"A2A 操作失败: {str(e)}"
    
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型: ask(提问), get_info(获取信息)",
                required=True
            ),
            ToolParameter(
                name="question",
                type="string",
                description="问题文本（ask 操作需要）",
                required=False
            )
        ]


class ANPTool(Tool):
    """ANP (Agent Network Protocol) 工具

    提供智能体网络管理功能，包括服务发现、节点管理和消息路由。
    这是一个概念性实现，用于演示 Agent 网络管理的核心理念。
    
    功能：
    - 注册和发现服务
    - 添加和管理网络节点
    - 消息路由
    - 网络统计

    使用示例:
        >>> from hello_agents.tools.builtin import ANPTool
        >>> tool = ANPTool()
        >>> # 注册服务
        >>> result = tool.run({
        ...     "action": "register_service",
        ...     "service_id": "calc-1",
        ...     "service_type": "calculator",
        ...     "endpoint": "http://localhost:5001"
        ... })
        >>> # 发现服务
        >>> result = tool.run({
        ...     "action": "discover_services",
        ...     "service_type": "calculator"
        ... })
        >>> # 添加节点
        >>> result = tool.run({
        ...     "action": "add_node",
        ...     "node_id": "agent-1",
        ...     "endpoint": "http://localhost:5001"
        ... })
    
    注意：这是概念性实现，不需要额外依赖
    详见文档: docs/chapter10/ANP_CONCEPTS.md
    """
    
    def __init__(self, name: str = "anp", description: str = None, discovery=None, network=None):
        """初始化 ANP 工具

        Args:
            name: 工具名称
            description: 工具描述
            discovery: 可选的 ANPDiscovery 实例，如果不提供则创建新实例
            network: 可选的 ANPNetwork 实例，如果不提供则创建新实例
        """
        if description is None:
            description = "智能体网络管理工具，支持服务发现、节点管理和消息路由。概念性实现。"

        super().__init__(
            name=name,
            description=description
        )
        from hello_agents.protocols.anp.implementation import ANPDiscovery, ANPNetwork
        self._discovery = discovery if discovery is not None else ANPDiscovery()
        self._network = network if network is not None else ANPNetwork()
        
    def run(self, parameters: Dict[str, Any]) -> str:
        """
        执行 ANP 操作
        
        Args:
            parameters: 包含以下参数的字典
                - action: 操作类型 (register_service, discover_services, add_node, route_message, get_stats)
                - service_id, service_type, endpoint: 服务信息（register_service 需要）
                - node_id, endpoint: 节点信息（add_node 需要）
                - from_node, to_node, message: 路由信息（route_message 需要）
        
        Returns:
            操作结果
        """
        from hello_agents.protocols.anp.implementation import ServiceInfo

        action = parameters.get("action", "").lower()
        
        if not action:
            return "错误：必须指定 action 参数"
        
        try:
            if action == "register_service":
                service_id = parameters.get("service_id")
                service_type = parameters.get("service_type")
                endpoint = parameters.get("endpoint")
                metadata = parameters.get("metadata", {})
                
                if not all([service_id, service_type, endpoint]):
                    return "错误：必须指定 service_id, service_type 和 endpoint 参数"
                
                service = ServiceInfo(service_id, service_type, endpoint, metadata)
                self._discovery.register_service(service)
                return f"✅ 已注册服务 '{service_id}'"

            elif action == "unregister_service":
                service_id = parameters.get("service_id")
                if not service_id:
                    return "错误：必须指定 service_id 参数"

                # 使用 ANPDiscovery 的 unregister_service 方法
                success = self._discovery.unregister_service(service_id)

                if success:
                    return f"✅ 已注销服务 '{service_id}'"
                else:
                    return f"错误：服务 '{service_id}' 不存在"

            elif action == "discover_services":
                service_type = parameters.get("service_type")
                services = self._discovery.discover_services(service_type)

                if not services:
                    return "没有找到服务"

                result = f"找到 {len(services)} 个服务:\n\n"
                for service in services:
                    result += f"服务ID: {service.service_id}\n"
                    result += f"  名称: {service.service_name}\n"
                    result += f"  类型: {service.service_type}\n"
                    result += f"  端点: {service.endpoint}\n"
                    if service.capabilities:
                        result += f"  能力: {', '.join(service.capabilities)}\n"
                    if service.metadata:
                        result += f"  元数据: {service.metadata}\n"
                    result += "\n"
                return result
                
            elif action == "add_node":
                node_id = parameters.get("node_id")
                endpoint = parameters.get("endpoint")
                metadata = parameters.get("metadata", {})
                
                if not all([node_id, endpoint]):
                    return "错误：必须指定 node_id 和 endpoint 参数"
                
                self._network.add_node(node_id, endpoint, metadata)
                return f"✅ 已添加节点 '{node_id}'"
                
            elif action == "route_message":
                from_node = parameters.get("from_node")
                to_node = parameters.get("to_node")
                message = parameters.get("message", {})
                
                if not all([from_node, to_node]):
                    return "错误：必须指定 from_node 和 to_node 参数"
                
                path = self._network.route_message(from_node, to_node, message)
                if path:
                    return f"消息路由路径: {' -> '.join(path)}"
                else:
                    return "无法找到路由路径"
                
            elif action == "get_stats":
                stats = self._network.get_network_stats()
                result = "网络统计:\n"
                for key, value in stats.items():
                    result += f"- {key}: {value}\n"
                return result
                
            else:
                return f"错误：不支持的操作 '{action}'"
                
        except Exception as e:
            return f"ANP 操作失败: {str(e)}"
    
    def get_parameters(self) -> List[ToolParameter]:
        """获取工具参数定义"""
        return [
            ToolParameter(
                name="action",
                type="string",
                description="操作类型: register_service, unregister_service, discover_services, add_node, route_message, get_stats",
                required=True
            ),
            ToolParameter(
                name="service_id",
                type="string",
                description="服务 ID（register_service, unregister_service 需要）",
                required=False
            ),
            ToolParameter(
                name="service_type",
                type="string",
                description="服务类型（register_service 需要）",
                required=False
            ),
            ToolParameter(
                name="endpoint",
                type="string",
                description="端点地址（register_service, add_node 需要）",
                required=False
            ),
            ToolParameter(
                name="node_id",
                type="string",
                description="节点 ID（add_node 需要）",
                required=False
            ),
            ToolParameter(
                name="from_node",
                type="string",
                description="源节点 ID（route_message 需要）",
                required=False
            ),
            ToolParameter(
                name="to_node",
                type="string",
                description="目标节点 ID（route_message 需要）",
                required=False
            ),
            ToolParameter(
                name="message",
                type="object",
                description="消息内容（route_message 需要）",
                required=False
            ),
            ToolParameter(
                name="metadata",
                type="object",
                description="元数据（register_service, add_node 可选）",
                required=False
            )
        ]

