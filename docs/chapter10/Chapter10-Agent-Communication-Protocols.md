<div align="right">
  English | <a href="./第十章%20智能体通信协议.md">中文</a>
</div>

# Chapter 10: Agent Communication Protocols

In previous chapters, we built fully functional standalone agents with reasoning, tool invocation, and memory capabilities. However, when attempting to build more complex AI systems, natural questions arise: **How can agents efficiently interact with the external world? How can multiple agents collaborate with each other?**

This is precisely the core problem that agent communication protocols aim to solve. This chapter will introduce three communication protocols to the HelloAgents framework: **MCP (Model Context Protocol)** for standardized communication between agents and tools, **A2A (Agent-to-Agent Protocol)** for peer-to-peer collaboration between agents, and **ANP (Agent Network Protocol)** for building large-scale agent networks. These three protocols together form the infrastructure layer for agent communication.

Through this chapter's learning, you will master the design philosophy and practical skills of agent communication protocols, understand the design differences between three mainstream protocols, and learn how to choose appropriate protocols to solve practical problems.

## 10.1 Agent Communication Protocol Fundamentals

### 10.1.1 Why Communication Protocols Are Needed

Recall the ReAct agent we built in Chapter 7, which already possesses powerful reasoning and tool invocation capabilities. Let's look at a typical usage scenario:

```python
from hello_agents import ReActAgent, HelloAgentsLLM
from hello_agents.tools import CalculatorTool, SearchTool

llm = HelloAgentsLLM()
agent = ReActAgent(name="AI Assistant", llm=llm)
agent.add_tool(CalculatorTool())
agent.add_tool(SearchTool())

# Agent can complete tasks independently
response = agent.run("Search for the latest AI news and calculate the total market value of related companies")
```

This agent works well, but it faces three fundamental limitations. First is the **tool integration dilemma**: Whenever we need to access a new external service (such as GitHub API, database, file system), we must write a specialized Tool class. This is not only labor-intensive, but tools written by different developers cannot be compatible with each other. Second is the **capability expansion bottleneck**: The agent's capabilities are limited to the predefined tool set and cannot dynamically discover and use new services. Finally is the **lack of collaboration**: When tasks are complex enough to require multiple specialized agents to collaborate (such as researcher + writer + editor), we can only coordinate their work through manual orchestration.

Let's understand these limitations through a more specific example. Suppose you want to build an intelligent research assistant that needs to:

```python
# Traditional approach: Manually integrate each service
class GitHubTool(BaseTool):
    """Need to manually write GitHub API adapter"""
    def run(self, repo_url):
        # Lots of API calling code...
        pass

class DatabaseTool(BaseTool):
    """Need to manually write database adapter"""
    def run(self, query):
        # Database connection and query code...
        pass

class WeatherTool(BaseTool):
    """Need to manually write weather API adapter"""
    def run(self, location):
        # Weather API calling code...
        pass

# Each new service requires repeating this process
agent.add_tool(GitHubTool())
agent.add_tool(DatabaseTool())
agent.add_tool(WeatherTool())
```

This approach has obvious problems: code duplication (each tool must handle HTTP requests, error handling, authentication, etc.), difficult to maintain (API changes require modifying all related tools), cannot be reused (tools from other developers cannot be directly used), poor scalability (adding new services requires extensive coding work).

The **core value of communication protocols** is precisely to solve these problems. It provides a set of standardized interface specifications that allow agents to access various external services in a unified way without needing to write specialized adapters for each service. This is like the Internet's TCP/IP protocol, which allows different devices to communicate with each other without needing to write specialized communication code for each type of device.

With communication protocols, the above code can be simplified to:

```python
from hello_agents.tools import MCPTool

# Connect to MCP server, automatically obtain all tools
mcp_tool = MCPTool()  # Built-in server provides basic tools

# Or connect to professional MCP servers
github_mcp = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-github"])
database_mcp = MCPTool(server_command=["python", "database_mcp_server.py"])

# Agent automatically obtains all capabilities without manually writing adapters
agent.add_tool(mcp_tool)
agent.add_tool(github_mcp)
agent.add_tool(database_mcp)
```

The changes brought by communication protocols are fundamental: **Standardized interfaces** allow different services to provide unified access methods, **interoperability** enables seamless integration of tools from different developers, **dynamic discovery** allows agents to discover new services and capabilities at runtime, and **scalability** enables systems to easily add new functional modules.

### 10.1.2 Comparison of Three Protocol Design Philosophies

Agent communication protocols are not a single solution, but a series of standards designed for different communication scenarios. This chapter uses the three currently mainstream protocols MCP, A2A, and ANP as examples for practice. Below is an overview comparison.

**(1) MCP: Bridge Between Agents and Tools**

MCP (Model Context Protocol) was proposed by the Anthropic team<sup>[1]</sup>, and its core design philosophy is to **standardize the communication method between agents and external tools/resources**. Imagine that your agent needs to access various services such as file systems, databases, GitHub, Slack, etc. The traditional approach is to write specialized adapters for each service, which is not only labor-intensive but also difficult to maintain. MCP defines a unified protocol specification that allows all services to be accessed in the same way.

MCP's design philosophy is "context sharing". It is not just an RPC (Remote Procedure Call) protocol, but more importantly, it allows agents and tools to share rich contextual information. As shown in Figure 10.1, when an agent accesses a code repository, the MCP server can not only provide file content but also provide contextual information such as code structure, dependency relationships, and commit history, enabling the agent to make more intelligent decisions.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-1.png" alt="" width="85%"/>
  <p>Figure 10.1 MCP Design Philosophy</p>
</div>

**(2) A2A: Dialogue Between Agents**

The A2A (Agent-to-Agent Protocol) protocol was proposed by the Google team<sup>2</sup>, and its core design philosophy is to **implement peer-to-peer communication between agents**. Unlike MCP, which focuses on communication between agents and tools, A2A focuses on how agents collaborate with each other. This design allows agents to engage in dialogue, negotiation, and collaboration like human teams.

A2A's design philosophy is "peer-to-peer communication". As shown in Figure 10.2, in an A2A network, each agent is both a service provider and a service consumer. Agents can actively initiate requests and also respond to requests from other agents. This peer-to-peer design avoids the bottleneck of centralized coordinators, making the agent network more flexible and scalable.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-2.png" alt="" width="85%"/>
  <p>Figure 10.2 A2A Design Philosophy</p>
</div>

**(3) ANP: Infrastructure for Agent Networks**

ANP (Agent Network Protocol) is a conceptual protocol framework<sup>3</sup>, currently maintained by the open-source community and not yet having a mature ecosystem. Its core design philosophy is to **build infrastructure for large-scale agent networks**. If MCP solves "how to access tools" and A2A solves "how to dialogue with other agents", then ANP solves "how to discover and connect agents in large-scale networks".

ANP's design philosophy is "decentralized service discovery". In a network containing hundreds or thousands of agents, how can agents find the services they need? As shown in Figure 10.3, ANP provides service registration, discovery, and routing mechanisms, allowing agents to dynamically discover other services in the network without needing to pre-configure all connection relationships.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-3.png" alt="" width="85%"/>
  <p>Figure 10.3 ANP Design Philosophy</p>
</div>

Finally, in Table 10.1, let's use a comparison table to more clearly understand the differences between these three protocols:

<div align="center">
  <p>Table 10.1 Comparison of Three Protocols</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-1.png" alt="" width="85%"/>
</div>

**(4) How to Choose the Right Protocol?**

Current protocols are still in early development stages. MCP's ecosystem is relatively mature, although the timeliness of various tools depends on maintainers. It is more recommended to choose MCP tools backed by large companies.

The key to choosing a protocol lies in understanding your needs:

- If your agent needs to access external services (files, databases, APIs), choose **MCP**
- If you need multiple agents to collaborate on tasks, choose **A2A**
- If you want to build a large-scale agent ecosystem, consider **ANP**

### 10.1.3 HelloAgents Communication Protocol Architecture Design

After understanding the design philosophies of the three protocols, let's see how to implement and use them in the HelloAgents framework. Our design goal is: **Enable learners to use these protocols in the simplest way while maintaining sufficient flexibility to handle complex scenarios**.

As shown in Figure 10.4, the HelloAgents communication protocol architecture adopts a three-layer design, from bottom to top: protocol implementation layer, tool encapsulation layer, and agent integration layer.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-4.png" alt="" width="85%"/>
  <p>Figure 10.4 HelloAgents Communication Protocol Design</p>
</div>

**(1) Protocol Implementation Layer**: This layer contains the specific implementations of the three protocols. MCP is implemented based on the FastMCP library, providing client and server functionality; A2A is implemented based on Google's official a2a-sdk; ANP is our self-developed lightweight implementation, providing service discovery and network management functions. Of course, there is currently also an official [implementation](https://github.com/agent-network-protocol/AgentConnect), but considering future iterations, we only simulate the concept here.

**(2) Tool Encapsulation Layer**: This layer encapsulates protocol implementations into a unified Tool interface. MCPTool, A2ATool, and ANPTool all inherit from BaseTool, providing a consistent `run()` method. This design allows agents to use different protocols in the same way.

**(3) Agent Integration Layer**: This layer is the integration point between agents and protocols. All agents (ReActAgent, SimpleAgent, etc.) use protocol tools through the Tool System without needing to care about underlying protocol details.

### 10.1.4 Learning Objectives and Quick Experience for This Chapter

Let's first look at the learning content for Chapter 10:

```
hello_agents/
├── protocols/                          # Communication protocol module
│   ├── mcp/                            # MCP protocol implementation (Model Context Protocol)
│   │   ├── client.py                   # MCP client (supports 5 transport methods)
│   │   ├── server.py                   # MCP server (FastMCP wrapper)
│   │   └── utils.py                    # Utility functions (create_context/parse_context)
│   ├── a2a/                            # A2A protocol implementation (Agent-to-Agent Protocol)
│   │   └── implementation.py           # A2A server/client (based on a2a-sdk, optional dependency)
│   └── anp/                            # ANP protocol implementation (Agent Network Protocol)
│       └── implementation.py           # ANP service discovery/registration (conceptual implementation)
└── tools/builtin/                      # Built-in tools module
    └── protocol_tools.py               # Protocol tool wrappers (MCPTool/A2ATool/ANPTool)
```

For this chapter's content, the focus is mainly on application, and the learning objective is to have the ability to apply protocols in your own projects. Also, since protocols are currently in early development stages, there's no need to spend too much effort reinventing the wheel. Before starting practical work, let's prepare the development environment:

```bash
# Install HelloAgents framework (Chapter 10 version)
pip install "hello-agents[protocol]==0.2.2"

# Install NodeJS, refer to documentation in Additional-Chapter
```

Let's experience the basic functionality of the three protocols with the simplest code:

```python
from hello_agents.tools import MCPTool, A2ATool, ANPTool

# 1. MCP: Access tools
mcp_tool = MCPTool()
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "add",
    "arguments": {"a": 10, "b": 20}
})
print(f"MCP calculation result: {result}")  # Output: 30.0

# 2. ANP: Service discovery
anp_tool = ANPTool()
anp_tool.run({
    "action": "register_service",
    "service_id": "calculator",
    "service_type": "math",
    "endpoint": "http://localhost:8080"
})
services = anp_tool.run({"action": "discover_services"})
print(f"Discovered services: {services}")

# 3. A2A: Agent communication
a2a_tool = A2ATool("http://localhost:5000")
print("A2A tool created successfully")
```

This simple example demonstrates the core functionality of the three protocols. In the following sections, we will deeply learn the detailed usage and best practices of each protocol.


## 10.2 MCP Protocol in Practice

Now, let's dive into MCP and master how to enable agents to access external tools and resources.

### 10.2.1 MCP Protocol Concept Introduction

**(1) MCP: The "USB-C" for Agents**

Imagine that your agent might need to do many things simultaneously, such as:
- Read documents from the local file system
- Query PostgreSQL databases
- Search code on GitHub
- Send Slack messages
- Access Google Drive

Traditionally, you would need to write adapter code for each service, handling different APIs, authentication methods, error handling, etc. This is not only labor-intensive but also difficult to maintain. More importantly, different LLM platforms have vastly different function call implementations, requiring extensive code rewrites when switching models.

MCP's emergence changed all this. Just as USB-C unified the connection methods for various devices, **MCP unified the interaction methods between agents and external tools**. Whether you use Claude, GPT, or other models, as long as they support the MCP protocol, they can seamlessly access the same tools and resources.

**(2) MCP Architecture**

The MCP protocol adopts a three-layer architecture design of Host, Client, and Servers. Let's understand how these components work together through the scenario in Figure 10.5.

Suppose you are using Claude Desktop and asking: "What documents are on my desktop?"

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-5.png" alt="" width="85%"/>
  <p>Figure 10.5 MCP Case Demonstration</p>
</div>

**Responsibilities of the Three-Layer Architecture:**

1. **Host (Host Layer)**: Claude Desktop acts as the Host, responsible for receiving user questions and interacting with the Claude model. The Host is the interface users directly interact with, managing the entire conversation flow.

2. **Client (Client Layer)**: When the Claude model decides it needs to access the file system, the MCP Client built into the Host is activated. The Client is responsible for establishing connections with the appropriate MCP Server, sending requests, and receiving responses.

3. **Server (Server Layer)**: The file system MCP Server is called, executes the actual file scanning operation, accesses the desktop directory, and returns the list of found documents.

**Complete Interaction Flow:** User question → Claude Desktop (Host) → Claude model analysis → Needs file information → MCP Client connection → File system MCP Server → Execute operation → Return result → Claude generates answer → Display on Claude Desktop

The advantage of this architectural design lies in **separation of concerns**: The Host focuses on user experience, the Client focuses on protocol communication, and the Server focuses on specific functionality implementation. Developers only need to focus on developing the corresponding MCP Server without caring about the implementation details of the Host and Client.

**(3) Core Capabilities of MCP**

As shown in Table 10.2, the MCP protocol provides three core capabilities, forming a complete tool access framework:

<div align="center">
  <p>Table 10.2 MCP Core Capabilities</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-2.png" alt="" width="85%"/>
</div>

The difference between these three capabilities is: **Tools are active** (execute operations), **Resources are passive** (provide data), **Prompts are instructive** (provide templates).

**(4) MCP Workflow**

Let's understand the complete workflow of MCP through a specific example, as shown in Figure 10.6:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-6.png" alt="" width="85%"/>
  <p>Figure 10.6 MCP Case Demonstration</p>
</div>

A key question is: **How does Claude (or other LLMs) decide which tools to use?**

When a user asks a question, the complete tool selection process is as follows:

1. **Tool Discovery Phase**: After the MCP Client connects to the Server, it first calls `list_tools()` to obtain description information for all available tools (including tool name, function description, parameter definition)

2. **Context Building**: The Client converts the tool list into a format the LLM can understand and adds it to the system prompt. For example:
   ```
   You can use the following tools:
   - read_file(path: str): Read the content of the file at the specified path
   - search_code(query: str, language: str): Search in the codebase
   ```

3. **Model Reasoning**: The LLM analyzes the user's question and available tools, deciding whether to call tools and which tool to call. This decision is based on the tool descriptions and current conversation context

4. **Tool Execution**: If the LLM decides to use a tool, the Client executes the selected tool through the MCP Server and obtains the result

5. **Result Integration**: The tool execution result is sent back to the LLM, which combines the result to generate the final answer

This process is **fully automated**, and the LLM will decide whether to use and how to use tools based on the quality of tool descriptions. Therefore, writing clear and accurate tool descriptions is crucial.

**(5) Differences Between MCP and Function Calling**

Many developers ask: **I'm already using Function Calling, why do I still need MCP?** Let's understand their differences through Table 10.3.

<div align="center">
  <p>Table 10.3 Function Calling vs MCP Comparison</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-3.png" alt="" width="85%"/>
</div>

Here we use the example of an agent needing to access GitHub repositories and the local file system to compare two implementations of the same task in detail.

**Method 1: Using Function Calling**

```python
# Step 1: Define functions for each LLM provider
# OpenAI format
openai_tools = [
    {
        "type": "function",
        "function": {
            "name": "search_github",
            "description": "Search GitHub repositories",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keywords"}
                },
                "required": ["query"]
            }
        }
    }
]

# Claude format
claude_tools = [
    {
        "name": "search_github",
        "description": "Search GitHub repositories",
        "input_schema": {  # Note: not parameters
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search keywords"}
            },
            "required": ["query"]
        }
    }
]

# Step 2: Implement tool functions yourself
def search_github(query):
    import requests
    response = requests.get(
        "https://api.github.com/search/repositories",
        params={"q": query}
    )
    return response.json()

# Step 3: Handle different model response formats
# OpenAI response
if response.choices[0].message.tool_calls:
    tool_call = response.choices[0].message.tool_calls[0]
    result = search_github(**json.loads(tool_call.function.arguments))

# Claude response
if response.content[0].type == "tool_use":
    tool_use = response.content[0]
    result = search_github(**tool_use.input)
```

**Method 2: Using MCP**

```python
from hello_agents.protocols import MCPClient

# Step 1: Connect to community-provided MCP server (no need to implement yourself)
github_client = MCPClient([
    "npx", "-y", "@modelcontextprotocol/server-github"
])

fs_client = MCPClient([
    "npx", "-y", "@modelcontextprotocol/server-filesystem", "."
])

# Step 2: Unified calling method (model-independent)
async with github_client:
    # Automatically discover tools
    tools = await github_client.list_tools()

    # Call tool (standardized interface)
    result = await github_client.call_tool(
        "search_repositories",
        {"query": "AI agents"}
    )

# Step 3: Any model supporting MCP can use it
# OpenAI, Claude, Llama, etc. all use the same MCP client
```

First, it needs to be clarified that Function Calling and MCP are not in competition, but rather complementary. Function Calling is a core capability of large language models, reflecting the model's inherent intelligence, enabling the model to understand when to call functions and precisely generate corresponding call parameters. In contrast, MCP plays the role of an infrastructure protocol, solving the engineering problem of how tools connect with models at the engineering level, describing and calling tools in a standardized way.

We can use a simple analogy to understand: Function Calling is equivalent to learning the skill of "how to make a phone call", including when to dial, how to communicate with the other party, and when to hang up. MCP, on the other hand, is that globally unified "telephone communication standard" that ensures any phone can successfully dial another.

After understanding their complementary relationship, let's next see how to use the MCP protocol in HelloAgents.

### 10.2.2 Using MCP Client

HelloAgents implements complete MCP client functionality based on FastMCP 2.0. We provide both asynchronous and synchronous APIs to suit different usage scenarios. For most applications, the asynchronous API is recommended as it better handles concurrent requests and long-running operations. Below we will provide a step-by-step operation demonstration.

**(1) Connecting to MCP Server**

The MCP client supports multiple connection methods, with the most common being Stdio mode (communicating with local processes through standard input/output):

```python
import asyncio
from hello_agents.protocols import MCPClient

async def connect_to_server():
    # Method 1: Connect to community-provided file system server
    # npx will automatically download and run the @modelcontextprotocol/server-filesystem package
    client = MCPClient([
        "npx", "-y",
        "@modelcontextprotocol/server-filesystem",
        "."  # Specify root directory
    ])

    # Use async with to ensure connection is properly closed
    async with client:
        # Use client here
        tools = await client.list_tools()
        print(f"Available tools: {[t['name'] for t in tools]}")

    # Method 2: Connect to custom Python MCP server
    client = MCPClient(["python", "my_mcp_server.py"])
    async with client:
        # Use client...
        pass

# Run async function
asyncio.run(connect_to_server())
```

**(2) Discovering Available Tools**

After successful connection, the first step is usually to query what tools the server provides:

```python
async def discover_tools():
    client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

    async with client:
        # Get all available tools
        tools = await client.list_tools()

        print(f"Server provides {len(tools)} tools:")
        for tool in tools:
            print(f"\nTool name: {tool['name']}")
            print(f"Description: {tool.get('description', 'No description')}")

            # Print parameter information
            if 'inputSchema' in tool:
                schema = tool['inputSchema']
                if 'properties' in schema:
                    print("Parameters:")
                    for param_name, param_info in schema['properties'].items():
                        param_type = param_info.get('type', 'any')
                        param_desc = param_info.get('description', '')
                        print(f"  - {param_name} ({param_type}): {param_desc}")

asyncio.run(discover_tools())

# Output example:
# Server provides 5 tools:
#
# Tool name: read_file
# Description: Read file content
# Parameters:
#   - path (string): File path
#
# Tool name: write_file
# Description: Write file content
# Parameters:
#   - path (string): File path
#   - content (string): File content
```

**(3) Calling Tools**

When calling tools, simply provide the tool name and parameters conforming to JSON Schema:

```python
async def use_tools():
    client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

    async with client:
        # Read file
        result = await client.call_tool("read_file", {"path": "my_README.md"})
        print(f"File content:\n{result}")

        # List directory
        result = await client.call_tool("list_directory", {"path": "."})
        print(f"Current directory files: {result}")

        # Write file
        result = await client.call_tool("write_file", {
            "path": "output.txt",
            "content": "Hello from MCP!"
        })
        print(f"Write result: {result}")

asyncio.run(use_tools())
```

Here's a safer way to call MCP services for reference:

```python
async def safe_tool_call():
    client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

    async with client:
        try:
            # Try to read a potentially non-existent file
            result = await client.call_tool("read_file", {"path": "nonexistent.txt"})
            print(result)
        except Exception as e:
            print(f"Tool call failed: {e}")
            # Can choose to retry, use default value, or report error to user

asyncio.run(safe_tool_call())
```

**(4) Accessing Resources**

Besides tools, MCP servers can also provide resources:

```python
# List available resources
resources = client.list_resources()
print(f"Available resources: {[r['uri'] for r in resources]}")

# Read resource
resource_content = client.read_resource("file:///path/to/resource")
print(f"Resource content: {resource_content}")
```

**(5) Using Prompt Templates**

MCP servers can provide predefined prompt templates:

```python
# List available prompts
prompts = client.list_prompts()
print(f"Available prompts: {[p['name'] for p in prompts]}")

# Get prompt content
prompt = client.get_prompt("code_review", {"language": "python"})
print(f"Prompt content: {prompt}")
```

**(6) Complete Example: Using GitHub MCP Service**

Let's see how to use the community-provided GitHub MCP service through a complete example, using the encapsulated MCP Tools:

```python
"""
GitHub MCP Service Example

Note: Need to set environment variable
    Windows: $env:GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
    Linux/macOS: export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
"""

from hello_agents.tools import MCPTool

# Create GitHub MCP tool
github_tool = MCPTool(
    server_command=["npx", "-y", "@modelcontextprotocol/server-github"]
)

# 1. List available tools
print("📋 Available tools:")
result = github_tool.run({"action": "list_tools"})
print(result)

# 2. Search repositories
print("\n🔍 Search repositories:")
result = github_tool.run({
    "action": "call_tool",
    "tool_name": "search_repositories",
    "arguments": {
        "query": "AI agents language:python",
        "page": 1,
        "perPage": 3
    }
})
print(result)

```

### 10.2.3 MCP Transport Methods Explained

An important feature of the MCP protocol is **transport agnosticism**. This means the MCP protocol itself does not depend on specific transport methods and can run on different communication channels. HelloAgents, based on FastMCP 2.0, provides complete transport method support, allowing you to choose the most appropriate transport mode based on actual scenarios.

**(1) Transport Methods Overview**

HelloAgents' `MCPClient` supports five transport methods, each with different use cases, as shown in Table 10.4:

<div align="center">
  <p>Table 10.4 MCP Transport Methods Comparison</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-4.png" alt="" width="85%"/>
</div>

**(2) Transport Method Usage Examples**

```python
from hello_agents.tools import MCPTool

# 1. Memory Transport - Memory transport (for testing)
# No parameters specified, uses built-in demo server
mcp_tool = MCPTool()

# 2. Stdio Transport - Standard input/output transport (local development)
# Use command list to start local server
mcp_tool = MCPTool(server_command=["python", "examples/mcp_example_server.py"])

# 3. Stdio Transport with Args - Command transport with parameters
# Can pass additional parameters
mcp_tool = MCPTool(server_command=["python", "examples/mcp_example_server.py", "--debug"])

# 4. Stdio Transport - Community server (npx method)
# Use npx to start community MCP server
mcp_tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

# 5. HTTP/SSE/StreamableHTTP Transport
# Note: MCPTool is mainly for Stdio and Memory transport
# For HTTP/SSE and other remote transports, recommend using MCPClient directly
```

**(3) Memory Transport**

Use case: Unit testing, rapid prototyping

```python
from hello_agents.tools import MCPTool

# Use built-in demo server (Memory transport)
mcp_tool = MCPTool()

# List available tools
result = mcp_tool.run({"action": "list_tools"})
print(result)

# Call tool
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "add",
    "arguments": {"a": 10, "b": 20}
})
print(result)
```

**(4) Stdio Transport - Standard Input/Output Transport**

Use case: Local development, debugging, Python script servers

```python
from hello_agents.tools import MCPTool

# Method 1: Use custom Python server
mcp_tool = MCPTool(server_command=["python", "my_mcp_server.py"])

# Method 2: Use community server (file system)
mcp_tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

# List tools
result = mcp_tool.run({"action": "list_tools"})
print(result)

# Call tool
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "read_file",
    "arguments": {"path": "README.md"}
})
print(result)
```

**(5) HTTP Transport**

Use case: Production environment, remote services, microservice architecture

```python
# Note: MCPTool is mainly for Stdio and Memory transport
# For HTTP/SSE and other remote transports, recommend using underlying MCPClient

import asyncio
from hello_agents.protocols import MCPClient

async def test_http_transport():
    # Connect to remote HTTP MCP server
    client = MCPClient("http://api.example.com/mcp")

    async with client:
        # Get server information
        tools = await client.list_tools()
        print(f"Remote server tools: {len(tools)} tools")

        # Call remote tool
        result = await client.call_tool("process_data", {
            "data": "Hello, World!",
            "operation": "uppercase"
        })
        print(f"Remote processing result: {result}")

# Note: Requires actual HTTP MCP server
# asyncio.run(test_http_transport())
```

**(6) SSE Transport - Server-Sent Events Transport**

Use case: Real-time communication, streaming processing, long connections

```python
# Note: MCPTool is mainly for Stdio and Memory transport
# For SSE transport, recommend using underlying MCPClient

import asyncio
from hello_agents.protocols import MCPClient

async def test_sse_transport():
    # Connect to SSE MCP server
    client = MCPClient(
        "http://localhost:8080/sse",
        transport_type="sse"
    )

    async with client:
        # SSE is especially suitable for streaming processing
        result = await client.call_tool("stream_process", {
            "input": "Large data processing request",
            "stream": True
        })
        print(f"Streaming processing result: {result}")

# Note: Requires MCP server supporting SSE
# asyncio.run(test_sse_transport())
```

**(7) StreamableHTTP Transport - Streaming HTTP Transport**

Use case: HTTP scenarios requiring bidirectional streaming communication

```python
# Note: MCPTool is mainly for Stdio and Memory transport
# For StreamableHTTP transport, recommend using underlying MCPClient

import asyncio
from hello_agents.protocols import MCPClient

async def test_streamable_http_transport():
    # Connect to StreamableHTTP MCP server
    client = MCPClient(
        "http://localhost:8080/mcp",
        transport_type="streamable_http"
    )

    async with client:
        # Supports bidirectional streaming communication
        tools = await client.list_tools()
        print(f"StreamableHTTP server tools: {len(tools)} tools")

# Note: Requires MCP server supporting StreamableHTTP
# asyncio.run(test_streamable_http_transport())
```

### 10.2.4 Using MCP Tools in Agents

Previously, we learned how to use the MCP client directly. But in practical applications, we prefer to have agents **automatically** call MCP tools rather than manually writing calling code. HelloAgents provides the `MCPTool` wrapper, allowing MCP servers to seamlessly integrate into the agent's tool chain.

**(1) Automatic Expansion Mechanism of MCP Tools**

HelloAgents' `MCPTool` has a feature: **automatic expansion**. When you add an MCP tool to an Agent, it automatically expands all tools provided by the MCP server into independent tools, allowing the Agent to call them like ordinary tools.

**Method 1: Using Built-in Demo Server**

We previously implemented calculator tool functions, and here we convert them into MCP services. This is the simplest usage method.

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

agent = SimpleAgent(name="Assistant", llm=HelloAgentsLLM())

# No configuration needed, automatically uses built-in demo server
mcp_tool = MCPTool(name="calculator")
agent.add_tool(mcp_tool)
# ✅ MCP tool 'calculator' expanded into 6 independent tools

# Agent can directly use expanded tools
response = agent.run("Calculate 25 times 16")
print(response)  # Output: The result of 25 times 16 is 400
```

**Tools after automatic expansion**:

- `calculator_add` - Addition calculator
- `calculator_subtract` - Subtraction calculator
- `calculator_multiply` - Multiplication calculator
- `calculator_divide` - Division calculator
- `calculator_greet` - Friendly greeting
- `calculator_get_system_info` - Get system information

When the Agent calls, it only needs to provide parameters, for example: `[TOOL_CALL:calculator_multiply:a=25,b=16]`, and the system will automatically handle type conversion and MCP calls.

**Method 2: Connecting to External MCP Servers**

In actual projects, you need to connect to more powerful MCP servers. These servers can be:
- **Community-provided official servers** (such as file system, GitHub, database, etc.)
- **Custom servers you write yourself** (encapsulating business logic)

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

agent = SimpleAgent(name="File Assistant", llm=HelloAgentsLLM())

# Example 1: Connect to community-provided file system server
fs_tool = MCPTool(
    name="filesystem",  # Specify unique name
    description="Access local file system",
    server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
)
agent.add_tool(fs_tool)

# Example 2: Connect to custom Python MCP server
# For how to write custom MCP servers, refer to Section 10.5
custom_tool = MCPTool(
    name="custom_server",  # Use different name
    description="Custom business logic server",
    server_command=["python", "my_mcp_server.py"]
)
agent.add_tool(custom_tool)

# Agent can now automatically use these tools!
response = agent.run("Please read the my_README.md file and summarize its main content")
print(response)
```

When using multiple MCP servers, be sure to specify a different name for each MCPTool. This name will be added as a prefix to the expanded tool names to avoid conflicts. For example: `name="fs"` will expand to `fs_read_file`, `fs_write_file`, etc. If you need to write your own MCP server to encapsulate specific business logic, refer to Section 10.5.

**(2) How MCP Tool Automatic Expansion Works**

Understanding the automatic expansion mechanism helps you better use MCP tools. Let's dive into how it works:

```python
# User code
fs_tool = MCPTool(name="fs", server_command=[...])
agent.add_tool(fs_tool)

# What happens internally:
# 1. MCPTool connects to server, discovers 14 tools
# 2. Creates wrapper for each tool:
#    - fs_read_text_file (parameters: path, tail, head)
#    - fs_write_file (parameters: path, content)
#    - ...
# 3. Registers to Agent's tool registry

# Agent call
response = agent.run("Read README.md")

# Inside Agent:
# 1. Identifies need to call fs_read_text_file
# 2. Generates parameters: path=README.md
# 3. Wrapper converts to MCP format:
#    {"action": "call_tool", "tool_name": "read_text_file", "arguments": {"path": "README.md"}}
# 4. Calls MCP server
# 5. Returns file content
```

The system automatically converts types based on tool parameter definitions:

```python
# Agent calls calculator
agent.run("Calculate 25 times 16")

# Agent generates: a=25,b=16 (string)
# System automatically converts to: {"a": 25.0, "b": 16.0} (number)
# MCP server receives correct number type
```

**(3) Practical Case: Intelligent Document Assistant**

Let's build a complete intelligent document assistant. Here we demonstrate with a simple multi-agent orchestration:

```python
"""
Multi-Agent Collaborative Intelligent Document Assistant

Uses two SimpleAgents for division of labor:
- Agent1: GitHub search expert
- Agent2: Document generation expert
"""
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(dotenv_path="../HelloAgents/.env")

print("="*70)
print("Multi-Agent Collaborative Intelligent Document Assistant")
print("="*70)

# ============================================================
# Agent 1: GitHub Search Expert
# ============================================================
print("\n[Step 1] Creating GitHub search expert...")

github_searcher = SimpleAgent(
    name="GitHub Search Expert",
    llm=HelloAgentsLLM(),
    system_prompt="""You are a GitHub search expert.
Your task is to search GitHub repositories and return results.
Please return clear, structured search results, including:
- Repository name
- Brief description

Keep it concise, don't add extra explanations."""
)

# Add GitHub tool
github_tool = MCPTool(
    name="gh",
    server_command=["npx", "-y", "@modelcontextprotocol/server-github"]
)
github_searcher.add_tool(github_tool)

# ============================================================
# Agent 2: Document Generation Expert
# ============================================================
print("\n[Step 2] Creating document generation expert...")

document_writer = SimpleAgent(
    name="Document Generation Expert",
    llm=HelloAgentsLLM(),
    system_prompt="""You are a document generation expert.
Your task is to generate structured Markdown reports based on provided information.

The report should include:
- Title
- Introduction
- Main content (listed in points, including project names, descriptions, etc.)
- Summary

Please output the complete Markdown format report content directly, do not use tools to save."""
)

# Add file system tool
fs_tool = MCPTool(
    name="fs",
    server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
)
document_writer.add_tool(fs_tool)

# ============================================================
# Execute Task
# ============================================================
print("\n" + "="*70)
print("Starting task execution...")
print("="*70)

try:
    # Step 1: GitHub search
    print("\n[Step 3] Agent1 searching GitHub...")
    search_task = "Search for GitHub repositories about 'AI agent', return the top 5 most relevant results"

    search_results = github_searcher.run(search_task)

    print("\nSearch results:")
    print("-" * 70)
    print(search_results)
    print("-" * 70)

    # Step 2: Generate report
    print("\n[Step 4] Agent2 generating report...")
    report_task = f"""
Based on the following GitHub search results, generate a Markdown format research report:

{search_results}

Report requirements:
1. Title: # AI Agent Framework Research Report
2. Introduction: Explain this is a GitHub project survey about AI Agents
3. Main findings: List found projects and their features (including names, descriptions, etc.)
4. Summary: Summarize common characteristics of these projects

Please output the complete Markdown format report directly.
"""

    report_content = document_writer.run(report_task)

    print("\nReport content:")
    print("=" * 70)
    print(report_content)
    print("=" * 70)

    # Step 3: Save report
    print("\n[Step 5] Saving report to file...")
    import os
    try:
        with open("report.md", "w", encoding="utf-8") as f:
            f.write(report_content)
        print("✅ Report saved to report.md")

        # Verify file
        file_size = os.path.getsize("report.md")
        print(f"✅ File size: {file_size} bytes")
    except Exception as e:
        print(f"❌ Save failed: {e}")

    print("\n" + "="*70)
    print("Task completed!")
    print("="*70)

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

```

`github_searcher` will call `gh_search_repositories` during this process to search GitHub projects. The obtained results will be returned to `document_writer` as input, further guiding report generation, and finally saving the report to report.md.

### 10.2.5 MCP Community Ecosystem

A huge advantage of the MCP protocol is its **rich community ecosystem**. Anthropic and community developers have created a large number of ready-made MCP servers, covering various scenarios such as file systems, databases, API services, etc. This means you don't need to write tool adapters from scratch and can directly use these verified servers.

Here are three resource repositories for the MCP community:

1. **Awesome MCP Servers** (https://github.com/punkpeye/awesome-mcp-servers)
   - Community-maintained curated list of MCP servers
   - Contains various third-party servers
   - Categorized by function, easy to find

2. **MCP Servers Website** (https://mcpservers.org/)
   - Official MCP server directory website
   - Provides search and filtering functions
   - Contains usage instructions and examples

3. **Official MCP Servers** (https://github.com/modelcontextprotocol/servers)
   - Servers officially maintained by Anthropic
   - Highest quality, most complete documentation
   - Contains implementations of commonly used services

Tables 10.5 and 10.6 show commonly used official MCP servers and popular community MCP servers:

<div align="center">
  <p>Table 10.5 Commonly Used Official MCP Servers</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-5.png" alt="" width="85%"/>
</div>

<div align="center">
  <p>Table 10.6 Popular Community MCP Servers</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-6.png" alt="" width="85%"/>
</div>

Here are some particularly interesting case TODOs for reference:

1. **Automated Web Testing (Playwright)**

   ```python
   # Agent can automatically:
   # - Open browser to visit website
   # - Fill forms and submit
   # - Screenshot to verify results
   # - Generate test reports
   playwright_tool = MCPTool(
       name="playwright",
       server_command=["npx", "-y", "@playwright/mcp"]
   )
   ```

2. **Intelligent Note Assistant (Obsidian + Perplexity)**
   ```python
   # Agent can:
   # - Search latest tech news (Perplexity)
   # - Organize into structured notes
   # - Save to Obsidian knowledge base
   # - Automatically establish links between notes
   ```

3. **Project Management Automation (Jira + GitHub)**
   ```python
   # Agent can:
   # - Create Jira tasks from GitHub Issues
   # - Sync code commits to Jira
   # - Automatically update Sprint progress
   # - Generate project reports
   ```

5. **Content Creation Workflow (YouTube + Notion + Spotify)**

   ```python
   # Agent can:
   # - Get YouTube video subtitles
   # - Generate content summaries
   # - Save to Notion database
   # - Play background music (Spotify)
   ```

Through this section's explanation, I hope you can explore more MCP implementation cases, and contributions to HelloAgents are welcome! Next, let's learn about the A2A protocol.

## 10.3 A2A Protocol in Practice

A2A (Agent-to-Agent) is a protocol that supports direct communication and collaboration between agents.

### 10.3.1 Protocol Design Motivation

The MCP protocol solved the interaction between agents and tools, while the A2A protocol solves the collaboration problem between agents. In a task requiring multi-agent (such as researcher, writer, editor) collaboration, they need to communicate, delegate tasks, negotiate capabilities, and synchronize states.

Traditional central coordinator (star topology) solutions have three main problems:

- **Single Point of Failure**: Coordinator failure leads to overall system paralysis.
- **Performance Bottleneck**: All communication goes through the central node, limiting concurrency.
- **Difficult to Scale**: Adding or modifying agents requires changing central logic.

The A2A protocol adopts a peer-to-peer (P2P) architecture (mesh topology), allowing agents to communicate directly, fundamentally solving the above problems. Its core is the two abstract concepts of **Task** and **Artifact**, which is its biggest difference from MCP, as shown in Table 10.7.

<div align="center">
  <p>Table 10.7 A2A Core Concepts</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-7.png" alt="" width="85%"/>
</div>

To implement management of the collaboration process, A2A defines a standardized lifecycle for tasks, including states such as creation, negotiation, delegation, in-progress, completion, and failure, as shown in Figure 10.7.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-7.png" alt="" width="85%"/>
  <p>Figure 10.7 A2A Task Lifecycle</p>
</div>


This mechanism enables agents to perform task negotiation, progress tracking, and exception handling.

The A2A request lifecycle is a sequence that details the four main steps a request follows: agent discovery, authentication, send message API, and send message stream API. Figure 10.8 below, borrowed from the official website's flowchart, shows the operational flow, illustrating the interaction between client, A2A server, and authentication server.

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-8.png" alt="" width="85%"/>
  <p>Figure 10.8 A2A Request Lifecycle</p>
</div>

### 10.3.2 A2A Protocol in Practice

Most existing A2A implementations are `Sample Code`, and even Python implementations are quite cumbersome. Therefore, here we only adopt a method that simulates the protocol's ideas, implementing partial functionality through the A2A-SDK.

**(2) Creating a Simple A2A Agent**

Let's create an A2A agent, again using the calculator case as a demonstration:

```python
from hello_agents.protocols.a2a.implementation import A2AServer, A2A_AVAILABLE

def create_calculator_agent():
    """Create a calculator agent"""
    if not A2A_AVAILABLE:
        print("❌ A2A SDK not installed, please run: pip install a2a-sdk")
        return None

    print("🧮 Creating calculator agent")

    # Create A2A server
    calculator = A2AServer(
        name="calculator-agent",
        description="Professional mathematical calculation agent",
        version="1.0.0",
        capabilities={
            "math": ["addition", "subtraction", "multiplication", "division"],
            "advanced": ["power", "sqrt", "factorial"]
        }
    )

    # Add basic calculation skills
    @calculator.skill("add")
    def add_numbers(query: str) -> str:
        """Addition calculation"""
        try:
            # Simple parsing of "calculate 5 + 3" format
            parts = query.replace("calculate", "").replace("plus", "+").replace("add", "+")
            if "+" in parts:
                numbers = [float(x.strip()) for x in parts.split("+")]
                result = sum(numbers)
                return f"Calculation result: {' + '.join(map(str, numbers))} = {result}"
            else:
                return "Please use format: calculate 5 + 3"
        except Exception as e:
            return f"Calculation error: {e}"

    @calculator.skill("multiply")
    def multiply_numbers(query: str) -> str:
        """Multiplication calculation"""
        try:
            parts = query.replace("calculate", "").replace("times", "*").replace("×", "*")
            if "*" in parts:
                numbers = [float(x.strip()) for x in parts.split("*")]
                result = 1
                for num in numbers:
                    result *= num
                return f"Calculation result: {' × '.join(map(str, numbers))} = {result}"
            else:
                return "Please use format: calculate 5 * 3"
        except Exception as e:
            return f"Calculation error: {e}"

    @calculator.skill("info")
    def get_info(query: str) -> str:
        """Get agent information"""
        return f"I am {calculator.name}, can perform basic mathematical calculations. Supported skills: {list(calculator.skills.keys())}"

    print(f"✅ Calculator agent created successfully, supported skills: {list(calculator.skills.keys())}")
    return calculator

# Create agent
calc_agent = create_calculator_agent()
if calc_agent:
    # Test skills
    print("\n🧪 Testing agent skills:")
    test_queries = [
        "Get information",
        "Calculate 10 + 5",
        "Calculate 6 * 7"
    ]

    for query in test_queries:
        if "information" in query.lower():
            result = calc_agent.skills["info"](query)
        elif "+" in query:
            result = calc_agent.skills["add"](query)
        elif "*" in query or "×" in query:
            result = calc_agent.skills["multiply"](query)
        else:
            result = "Unknown query type"

        print(f"  📝 Query: {query}")
        print(f"  🤖 Reply: {result}")
        print()
```

**(2) Custom A2A Agent**

You can also create your own A2A agent, here's a simple demonstration:

```python
from hello_agents.protocols.a2a.implementation import A2AServer, A2A_AVAILABLE

def create_custom_agent():
    """Create custom agent"""
    if not A2A_AVAILABLE:
        print("Please install A2A SDK first: pip install a2a-sdk")
        return None

    # Create agent
    agent = A2AServer(
        name="my-custom-agent",
        description="My custom agent",
        capabilities={"custom": ["skill1", "skill2"]}
    )

    # Add skills
    @agent.skill("greet")
    def greet_user(name: str) -> str:
        """Greet user"""
        return f"Hello, {name}! I am a custom agent."

    @agent.skill("calculate")
    def simple_calculate(expression: str) -> str:
        """Simple calculation"""
        try:
            # Safe calculation (only supports basic operations)
            allowed_chars = set('0123456789+-*/(). ')
            if all(c in allowed_chars for c in expression):
                result = eval(expression)
                return f"Calculation result: {expression} = {result}"
            else:
                return "Error: Only basic mathematical operations supported"
        except Exception as e:
            return f"Calculation error: {e}"

    return agent

# Create and test custom agent
custom_agent = create_custom_agent()
if custom_agent:
    # Test skills
    print("Testing greeting skill:")
    result1 = custom_agent.skills["greet"]("Zhang San")
    print(result1)

    print("\nTesting calculation skill:")
    result2 = custom_agent.skills["calculate"]("10 + 5 * 2")
    print(result2)
```

### 10.3.3 Using HelloAgents A2A Tools

HelloAgents provides a unified A2A tool interface.

**(1) Creating A2A Agent Server**

First, let's create an Agent server:

```python
from hello_agents.protocols import A2AServer
import threading

# Create researcher Agent service
researcher = A2AServer(
    name="researcher",
    description="Agent responsible for searching and analyzing materials",
    version="1.0.0"
)

# Define skills
@researcher.skill("research")
def handle_research(text: str) -> str:
    """Handle research requests"""
    import re
    match = re.search(r'research\s+(.+)', text, re.IGNORECASE)
    topic = match.group(1).strip() if match else text

    # Actual research logic (simplified here)
    result = {
        "topic": topic,
        "findings": f"Research results about {topic}...",
        "sources": ["Source 1", "Source 2", "Source 3"]
    }
    return str(result)

# Start service in background
def start_server():
    researcher.run(host="localhost", port=5000)

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print("✅ Researcher Agent service started at http://localhost:5000")

    # Keep program running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nService stopped")
```

**(2) Creating A2A Agent Client**

Now, let's create a client to communicate with the server:

```python
from hello_agents.protocols import A2AClient

# Create client to connect to researcher Agent
client = A2AClient("http://localhost:5000")

# Send research request
response = client.execute_skill("research", "research AI applications in healthcare")
print(f"Received response: {response.get('result')}")

# Output:
# Received response: {'topic': 'AI applications in healthcare', 'findings': 'Research results about AI applications in healthcare...', 'sources': ['Source 1', 'Source 2', 'Source 3']}
```

**(3) Creating Agent Network**

For collaboration among multiple Agents, we can connect multiple Agents to each other:

```python
from hello_agents.protocols import A2AServer, A2AClient
import threading
import time

# 1. Create multiple Agent services
researcher = A2AServer(
    name="researcher",
    description="Researcher"
)

@researcher.skill("research")
def do_research(text: str) -> str:
    import re
    match = re.search(r'research\s+(.+)', text, re.IGNORECASE)
    topic = match.group(1).strip() if match else text
    return str({"topic": topic, "findings": f"Research results for {topic}"})

writer = A2AServer(
    name="writer",
    description="Writer"
)

@writer.skill("write")
def write_article(text: str) -> str:
    import re
    match = re.search(r'write\s+(.+)', text, re.IGNORECASE)
    content = match.group(1).strip() if match else text

    # Try to parse research data
    try:
        data = eval(content)
        topic = data.get("topic", "Unknown topic")
        findings = data.get("findings", "No research results")
    except:
        topic = "Unknown topic"
        findings = content

    return f"# {topic}\n\nBased on research: {findings}\n\nArticle content..."

editor = A2AServer(
    name="editor",
    description="Editor"
)

@editor.skill("edit")
def edit_article(text: str) -> str:
    import re
    match = re.search(r'edit\s+(.+)', text, re.IGNORECASE)
    article = match.group(1).strip() if match else text

    result = {
        "article": article + "\n\n[Edited and optimized]",
        "feedback": "Article quality is good",
        "approved": True
    }
    return str(result)

# 2. Start all services
threading.Thread(target=lambda: researcher.run(port=5000), daemon=True).start()
threading.Thread(target=lambda: writer.run(port=5001), daemon=True).start()
threading.Thread(target=lambda: editor.run(port=5002), daemon=True).start()
time.sleep(2)  # Wait for services to start

# 3. Create clients to connect to each Agent
researcher_client = A2AClient("http://localhost:5000")
writer_client = A2AClient("http://localhost:5001")
editor_client = A2AClient("http://localhost:5002")

# 4. Collaboration workflow
def create_content(topic):
    # Step 1: Research
    research = researcher_client.execute_skill("research", f"research {topic}")
    research_data = research.get('result', '')

    # Step 2: Write
    article = writer_client.execute_skill("write", f"write {research_data}")
    article_content = article.get('result', '')

    # Step 3: Edit
    final = editor_client.execute_skill("edit", f"edit {article_content}")
    return final.get('result', '')

# Usage
result = create_content("AI applications in healthcare")
print(f"\nFinal result:\n{result}")
```

### 10.3.4 Using A2A Tools in Agents

Now let's see how to integrate A2A into HelloAgents agents.

**(1) Using A2ATool Wrapper**

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import A2ATool
from dotenv import load_dotenv

load_dotenv()
llm = HelloAgentsLLM()

# Assume a researcher Agent service is already running at http://localhost:5000

# Create coordinator Agent
coordinator = SimpleAgent(name="Coordinator", llm=llm)

# Add A2A tool, connect to researcher Agent
researcher_tool = A2ATool(
    name="researcher",
    description="Researcher Agent, can search and analyze materials",
    agent_url="http://localhost:5000"
)
coordinator.add_tool(researcher_tool)

# Coordinator can call researcher Agent
response = coordinator.run("Please have the researcher help me research AI applications in education")
print(response)
```

**(2) Practical Case: Intelligent Customer Service System**

Let's build a complete intelligent customer service system with three Agents:
- **Receptionist**: Analyzes customer question types
- **Technical Expert**: Answers technical questions
- **Sales Consultant**: Answers sales questions

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import A2ATool
from hello_agents.protocols import A2AServer
import threading
import time
from dotenv import load_dotenv

load_dotenv()
llm = HelloAgentsLLM()

# 1. Create technical expert Agent service
tech_expert = A2AServer(
    name="tech_expert",
    description="Technical expert, answers technical questions"
)

@tech_expert.skill("answer")
def answer_tech_question(text: str) -> str:
    import re
    match = re.search(r'answer\s+(.+)', text, re.IGNORECASE)
    question = match.group(1).strip() if match else text
    # In actual applications, this would call LLM or knowledge base
    return f"Technical answer: Regarding '{question}', I suggest you check our technical documentation..."

# 2. Create sales consultant Agent service
sales_advisor = A2AServer(
    name="sales_advisor",
    description="Sales consultant, answers sales questions"
)

@sales_advisor.skill("answer")
def answer_sales_question(text: str) -> str:
    import re
    match = re.search(r'answer\s+(.+)', text, re.IGNORECASE)
    question = match.group(1).strip() if match else text
    return f"Sales answer: Regarding '{question}', we have special offers..."

# 3. Start services
threading.Thread(target=lambda: tech_expert.run(port=6000), daemon=True).start()
threading.Thread(target=lambda: sales_advisor.run(port=6001), daemon=True).start()
time.sleep(2)

# 4. Create receptionist Agent (using HelloAgents' SimpleAgent)
receptionist = SimpleAgent(
    name="Receptionist",
    llm=llm,
    system_prompt="""You are a customer service receptionist, responsible for:
1. Analyzing customer question types (technical questions or sales questions)
2. Forwarding questions to appropriate experts
3. Organizing expert answers and returning them to customers

Please remain polite and professional."""
)

# Add technical expert tool
tech_tool = A2ATool(
    agent_url="http://localhost:6000",
    name="tech_expert",
    description="Technical expert, answers technical-related questions"
)
receptionist.add_tool(tech_tool)

# Add sales consultant tool
sales_tool = A2ATool(
    agent_url="http://localhost:6001",
    name="sales_advisor",
    description="Sales consultant, answers price and purchase-related questions"
)
receptionist.add_tool(sales_tool)

# 5. Handle customer inquiries
def handle_customer_query(query):
    print(f"\nCustomer inquiry: {query}")
    print("=" * 50)
    response = receptionist.run(query)
    print(f"\nCustomer service reply: {response}")
    print("=" * 50)

# Test different types of questions
if __name__ == "__main__":
    handle_customer_query("How do I call your API?")
    handle_customer_query("What is the price of the enterprise version?")
    handle_customer_query("How do I integrate it into my Python project?")
```

**(3) Advanced Usage: Agent Negotiation**

The A2A protocol also supports negotiation mechanisms between Agents:

```python
from hello_agents.protocols import A2AServer, A2AClient
import threading
import time

# Create two Agents that need to negotiate
agent1 = A2AServer(
    name="agent1",
    description="Agent 1"
)

@agent1.skill("propose")
def handle_proposal(text: str) -> str:
    """Handle negotiation proposals"""
    import re

    # Parse proposal
    match = re.search(r'propose\s+(.+)', text, re.IGNORECASE)
    proposal_str = match.group(1).strip() if match else text

    try:
        proposal = eval(proposal_str)
        task = proposal.get("task")
        deadline = proposal.get("deadline")

        # Evaluate proposal
        if deadline >= 7:  # Need at least 7 days
            result = {"accepted": True, "message": "Proposal accepted"}
        else:
            result = {
                "accepted": False,
                "message": "Timeline too tight",
                "counter_proposal": {"deadline": 7}
            }
        return str(result)
    except:
        return str({"accepted": False, "message": "Invalid proposal format"})

agent2 = A2AServer(
    name="agent2",
    description="Agent 2"
)

@agent2.skill("negotiate")
def negotiate_task(text: str) -> str:
    """Initiate negotiation"""
    import re

    # Parse task and deadline
    match = re.search(r'negotiate\s+task:(.+?)\s+deadline:(\d+)', text, re.IGNORECASE)
    if match:
        task = match.group(1).strip()
        deadline = int(match.group(2))

        # Send proposal to agent1
        proposal = {"task": task, "deadline": deadline}
        return str({"status": "negotiating", "proposal": proposal})
    else:
        return str({"status": "error", "message": "Invalid negotiation request"})

# Start services
threading.Thread(target=lambda: agent1.run(port=7000), daemon=True).start()
threading.Thread(target=lambda: agent2.run(port=7001), daemon=True).start()
```

## 10.4 ANP Protocol in Practice

After the MCP protocol solved tool invocation and the A2A protocol solved peer-to-peer agent collaboration, the ANP protocol focuses on solving agent management problems in large-scale, open network environments.

In Sections 10.2 and 10.3, we learned about MCP (tool access) and A2A (agent collaboration). Now, let's learn about the ANP (Agent Network Protocol) protocol, which focuses on building **large-scale, open agent networks**.

### 10.4.1 Protocol Goals

When a network contains a large number of agents with different functions (e.g., natural language processing, image recognition, data analysis, etc.), the system faces a series of challenges:

- **Service Discovery**: When a new task arrives, how to quickly find agents capable of handling that task?
- **Intelligent Routing**: If multiple agents can handle the same task, how to choose the most suitable one (e.g., based on load, cost, etc.) and dispatch the task to it?
- **Dynamic Scaling**: How to make newly joined agents discoverable and callable by other members?

The design goal of ANP is to provide a standardized mechanism to solve the above service discovery, routing selection, and network scalability problems.

To achieve its design goals, ANP defines the following core concepts, as shown in Table 10.8:

<div align="center">
  <p>Table 10.8 ANP Core Concepts</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-table-8.png" alt="" width="85%"/>
</div>

We also borrow from the official [Getting Started Guide](https://github.com/agent-network-protocol/AgentNetworkProtocol/blob/main/docs/chinese/ANP入门指南.md) to introduce ANP's architectural design, as shown in Figure 10.9

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-9.png" alt="" width="85%"/>
  <p>Figure 10.9 ANP Overall Process</p>
</div>


In this flowchart, the main steps include:

**1. Service Discovery and Matching:** First, Agent A uses a public discovery service to query based on semantic or functional descriptions to locate Agent B that meets its task requirements. The discovery service establishes an index by pre-crawling standard endpoints (`.well-known/agent-descriptions`) exposed by each agent, thereby achieving dynamic matching between service demanders and providers.

**2. DID-based Identity Verification:** At the start of interaction, Agent A uses its private key to sign a request containing its own DID. After Agent B receives it, it parses the DID to obtain the corresponding public key and uses it to verify the authenticity of the signature and the integrity of the request, thereby establishing trusted communication between both parties.

**3. Standardized Service Execution:** After identity verification passes, Agent B responds to the request, and both parties exchange data or invoke services (such as booking, querying, etc.) according to predefined standard interfaces and data formats. Standardized interaction processes are the foundation for achieving cross-platform and cross-system interoperability.

In summary, the core of this mechanism is using DID to build a decentralized trust foundation and leveraging standardized description protocols to achieve dynamic service discovery. This approach enables agents to form collaborative networks on the internet securely and efficiently without requiring central coordination.

### 10.4.2 Using ANP Service Discovery

**(1) Creating Service Discovery Center**

```python
from hello_agents.protocols import ANPDiscovery, register_service

# Create service discovery center
discovery = ANPDiscovery()

# Register Agent services
register_service(
    discovery=discovery,
    service_id="nlp_agent_1",
    service_name="NLP Processing Expert A",
    service_type="nlp",
    capabilities=["text_analysis", "sentiment_analysis", "ner"],
    endpoint="http://localhost:8001",
    metadata={"load": 0.3, "price": 0.01, "version": "1.0.0"}
)

register_service(
    discovery=discovery,
    service_id="nlp_agent_2",
    service_name="NLP Processing Expert B",
    service_type="nlp",
    capabilities=["text_analysis", "translation"],
    endpoint="http://localhost:8002",
    metadata={"load": 0.7, "price": 0.02, "version": "1.1.0"}
)

print("✅ Service registration completed")
```

**(2) Discovering Services**

```python
from hello_agents.protocols import discover_service

# Find by type
nlp_services = discover_service(discovery, service_type="nlp")
print(f"Found {len(nlp_services)} NLP services")

# Select service with lowest load
best_service = min(nlp_services, key=lambda s: s.metadata.get("load", 1.0))
print(f"Best service: {best_service.service_name} (load: {best_service.metadata['load']})")
```

**(3) Building Agent Network**

```python
from hello_agents.protocols import ANPNetwork

# Create network
network = ANPNetwork(network_id="ai_cluster")

# Add nodes
for service in discovery.list_all_services():
    network.add_node(service.service_id, service.endpoint)

# Establish connections (based on capability matching)
network.connect_nodes("nlp_agent_1", "nlp_agent_2")

stats = network.get_network_stats()
print(f"✅ Network construction completed, total {stats['total_nodes']} nodes")
```

### 10.4.3 Practical Case

Let's build a complete distributed task scheduling system:

```python
from hello_agents.protocols import ANPDiscovery, register_service
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools.builtin import ANPTool
import random
from dotenv import load_dotenv

load_dotenv()
llm = HelloAgentsLLM()

# 1. Create service discovery center
discovery = ANPDiscovery()

# 2. Register multiple compute nodes
for i in range(10):
    register_service(
        discovery=discovery,
        service_id=f"compute_node_{i}",
        service_name=f"Compute Node {i}",
        service_type="compute",
        capabilities=["data_processing", "ml_training"],
        endpoint=f"http://node{i}:8000",
        metadata={
            "load": random.uniform(0.1, 0.9),
            "cpu_cores": random.choice([4, 8, 16]),
            "memory_gb": random.choice([16, 32, 64]),
            "gpu": random.choice([True, False])
        }
    )

print(f"✅ Registered {len(discovery.list_services())} compute nodes")

# 3. Create task scheduler Agent
scheduler = SimpleAgent(
    name="Task Scheduler",
    llm=llm,
    system_prompt="""You are an intelligent task scheduler, responsible for:
1. Analyzing task requirements
2. Selecting the most suitable compute node
3. Assigning tasks

When selecting nodes, consider: load, CPU cores, memory, GPU, and other factors."""
)

# Add ANP tool
anp_tool = ANPTool(
    name="service_discovery",
    description="Service discovery tool, can find and select compute nodes",
    discovery=discovery
)
scheduler.add_tool(anp_tool)

# 4. Intelligent task assignment
def assign_task(task_description):
    print(f"\nTask: {task_description}")
    print("=" * 50)

    # Let Agent intelligently select node
    response = scheduler.run(f"""
    Please select the most suitable compute node for the following task:
    {task_description}

    Requirements:
    1. List all available nodes
    2. Analyze characteristics of each node
    3. Select the most suitable node
    4. Explain selection reasoning
    """)

    print(response)
    print("=" * 50)

# Test different types of tasks
assign_task("Train a large deep learning model, requires GPU support")
assign_task("Process large amounts of text data, requires high memory")
assign_task("Run lightweight data analysis task")
```

This is a load balancing example

```python
from hello_agents.protocols import ANPDiscovery, register_service
import random

# Create service discovery center
discovery = ANPDiscovery()

# Register multiple services of the same type
for i in range(5):
    register_service(
        discovery=discovery,
        service_id=f"api_server_{i}",
        service_name=f"API Server {i}",
        service_type="api",
        capabilities=["rest_api"],
        endpoint=f"http://api{i}:8000",
        metadata={"load": random.uniform(0.1, 0.9)}
    )

# Load balancing function
def get_best_server():
    """Select server with lowest load"""
    servers = discovery.discover_services(service_type="api")
    if not servers:
        return None

    best = min(servers, key=lambda s: s.metadata.get("load", 1.0))
    return best

# Simulate request allocation
for i in range(10):
    server = get_best_server()
    print(f"Request {i+1} -> {server.service_name} (load: {server.metadata['load']:.2f})")

    # Update load (simulated)
    server.metadata["load"] += 0.1
```

## 10.5 Building Custom MCP Servers

In previous sections, we learned how to use existing MCP services. We also learned about the characteristics of different protocols. Now, let's learn how to build our own MCP server.

### 10.5.1 Creating Your First MCP Server

**(1) Why Build a Custom MCP Server?**

Although you can directly use public MCP services, in many practical application scenarios, you need to build custom MCP servers to meet specific needs.

Main motivations include the following:

- **Encapsulating Business Logic**: Encapsulate enterprise-specific business processes or complex operations as standardized MCP tools for unified invocation by agents.
- **Accessing Private Data**: Create a secure and controllable interface or proxy for accessing internal databases, APIs, or other private data sources that cannot be exposed to the public network.
- **Performance Optimization**: Perform deep optimization for high-frequency calls or application scenarios with strict response latency requirements.
- **Custom Feature Extension**: Implement specific functions not provided by standard MCP services, such as integrating proprietary algorithm models or connecting to specific hardware devices.

**(2) Teaching Case: Weather Query MCP Server**

Let's start with a simple weather query server and gradually learn MCP server development:

```python
#!/usr/bin/env python3
"""Weather Query MCP Server"""

import json
import requests
import os
from datetime import datetime
from typing import Dict, Any
from hello_agents.protocols import MCPServer

# Create MCP server
weather_server = MCPServer(name="weather-server", description="Real weather query service")

CITY_MAP = {
    "Beijing": "Beijing", "Shanghai": "Shanghai", "Guangzhou": "Guangzhou",
    "Shenzhen": "Shenzhen", "Hangzhou": "Hangzhou", "Chengdu": "Chengdu",
    "Chongqing": "Chongqing", "Wuhan": "Wuhan", "Xi'an": "Xi'an",
    "Nanjing": "Nanjing", "Tianjin": "Tianjin", "Suzhou": "Suzhou"
}


def get_weather_data(city: str) -> Dict[str, Any]:
    """Get weather data from wttr.in"""
    city_en = CITY_MAP.get(city, city)
    url = f"https://wttr.in/{city_en}?format=j1"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    current = data["current_condition"][0]

    return {
        "city": city,
        "temperature": float(current["temp_C"]),
        "feels_like": float(current["FeelsLikeC"]),
        "humidity": int(current["humidity"]),
        "condition": current["weatherDesc"][0]["value"],
        "wind_speed": round(float(current["windspeedKmph"]) / 3.6, 1),
        "visibility": float(current["visibility"]),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


# Define tool function
def get_weather(city: str) -> str:
    """Get current weather for specified city"""
    try:
        weather_data = get_weather_data(city)
        return json.dumps(weather_data, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e), "city": city}, ensure_ascii=False)


def list_supported_cities() -> str:
    """List all supported Chinese cities"""
    result = {"cities": list(CITY_MAP.keys()), "count": len(CITY_MAP)}
    return json.dumps(result, ensure_ascii=False, indent=2)


def get_server_info() -> str:
    """Get server information"""
    info = {
        "name": "Weather MCP Server",
        "version": "1.0.0",
        "tools": ["get_weather", "list_supported_cities", "get_server_info"]
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


# Register tools to server
weather_server.add_tool(get_weather)
weather_server.add_tool(list_supported_cities)
weather_server.add_tool(get_server_info)


if __name__ == "__main__":
    weather_server.run()
```

**(3) Testing Custom MCP Server**

Then create a test script:

```python
#!/usr/bin/env python3
"""Test Weather Query MCP Server"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'HelloAgents'))
from hello_agents.protocols.mcp.client import MCPClient


async def test_weather_server():
    server_script = os.path.join(os.path.dirname(__file__), "14_weather_mcp_server.py")
    client = MCPClient(["python", server_script])

    try:
        async with client:
            # Test 1: Get server information
            info = json.loads(await client.call_tool("get_server_info", {}))
            print(f"Server: {info['name']} v{info['version']}")

            # Test 2: List supported cities
            cities = json.loads(await client.call_tool("list_supported_cities", {}))
            print(f"Supported cities: {cities['count']} cities")

            # Test 3: Query Beijing weather
            weather = json.loads(await client.call_tool("get_weather", {"city": "Beijing"}))
            if "error" not in weather:
                print(f"\nBeijing weather: {weather['temperature']}°C, {weather['condition']}")

            # Test 4: Query Shenzhen weather
            weather = json.loads(await client.call_tool("get_weather", {"city": "Shenzhen"}))
            if "error" not in weather:
                print(f"Shenzhen weather: {weather['temperature']}°C, {weather['condition']}")

            print("\n✅ All tests completed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_weather_server())
```

**(4) Using Custom MCP Server in Agent**

```python
"""Using Weather MCP Server in Agent"""

import os
from dotenv import load_dotenv
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

load_dotenv()


def create_weather_assistant():
    """Create weather assistant"""
    llm = HelloAgentsLLM()

    assistant = SimpleAgent(
        name="Weather Assistant",
        llm=llm,
        system_prompt="""You are a weather assistant that can query city weather.
Use the get_weather tool to query weather, supports Chinese city names.
"""
    )

    # Add weather MCP tool
    server_script = os.path.join(os.path.dirname(__file__), "14_weather_mcp_server.py")
    weather_tool = MCPTool(server_command=["python", server_script])
    assistant.add_tool(weather_tool)

    return assistant


def demo():
    """Demo"""
    assistant = create_weather_assistant()

    print("\nQuery Beijing weather:")
    response = assistant.run("How's the weather in Beijing today?")
    print(f"Answer: {response}\n")


def interactive():
    """Interactive mode"""
    assistant = create_weather_assistant()

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ['quit', 'exit']:
            break
        response = assistant.run(user_input)
        print(f"Assistant: {response}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        demo()
    else:
        interactive()
```

```
🔗 Connecting to MCP server...
✅ Connection successful!
🔌 Connection disconnected
✅ Tool 'mcp_get_weather' registered.
✅ Tool 'mcp_list_supported_cities' registered.
✅ Tool 'mcp_get_server_info' registered.
✅ MCP tool 'mcp' expanded into 3 independent tools

You: I want to query Beijing's weather
🔗 Connecting to MCP server...
✅ Connection successful!
🔌 Connection disconnected
Assistant: The current weather in Beijing is as follows:

- Temperature: 10.0°C
- Feels like: 9.0°C
- Humidity: 94%
- Weather condition: Light rain
- Wind speed: 1.7 m/s
- Visibility: 10.0 km
- Timestamp: October 9, 2025 13:46:40

Please bring rain gear and adjust your clothing according to weather changes.
```

### 10.5.2 Uploading MCP Server

We created a real weather query MCP server. Now, let's publish it to the Smithery platform so developers worldwide can use our service.

(1) What is Smithery?

[Smithery](https://smithery.ai/) is the official publishing platform for MCP servers, similar to Python's PyPI or Node.js's npm. Through Smithery, users can:

- 🔍 Discover and search for MCP servers
- 📦 Install MCP servers with one click
- 📊 View server usage statistics and ratings
- 🔄 Automatically get server updates

(2) Preparing for Publication
First, we need to organize the project into a standard publishing format. This folder has been organized in the `code` directory for your reference:

```
weather-mcp-server/
├── README.md           # Project documentation
├── LICENSE            # Open source license
├── Dockerfile         # Docker build configuration (recommended)
├── pyproject.toml     # Python project configuration (required)
├── requirements.txt   # Python dependencies
├── smithery.yaml      # Smithery configuration file (required)
└── server.py          # MCP server main file
```

Note that `smithery.yaml` is the configuration file for the Smithery platform:
```yaml
name: weather-mcp-server
displayName: Weather MCP Server
description: Real-time weather query MCP server based on HelloAgents framework
version: 1.0.0
author: HelloAgents Team
homepage: https://github.com/yourusername/weather-mcp-server
license: MIT
categories:
  - weather
  - data
tags:
  - weather
  - real-time
  - helloagents
  - wttr
runtime: container
build:
  dockerfile: Dockerfile
  dockerBuildPath: .
startCommand:
  type: http
tools:
  - name: get_weather
    description: Get current weather for a city
  - name: list_supported_cities
    description: List all supported cities
  - name: get_server_info
    description: Get server information
```

Configuration explanation:

- `name`: Unique identifier for the server (lowercase, hyphen-separated)
- `displayName`: Display name
- `description`: Brief description
- `version`: Version number (follows semantic versioning)
- `runtime`: Runtime environment (python/node)
- `entrypoint`: Entry file
- `tools`: Tool list

`pyproject.toml` is the standard configuration file for Python projects. Smithery requires this file because it will be packaged into a server later:

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "weather-mcp-server"
version = "1.0.0"
description = "Real-time weather query MCP server based on HelloAgents framework"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "HelloAgents Team", email = "xxx"}
]
requires-python = ">=3.10"
dependencies = [
    "hello-agents>=0.2.1",
    "requests>=2.31.0",
]

[project.urls]
Homepage = "https://github.com/yourusername/weather-mcp-server"
Repository = "https://github.com/yourusername/weather-mcp-server"
"Bug Tracker" = "https://github.com/yourusername/weather-mcp-server/issues"

[tool.setuptools]
py-modules = ["server"]
```


Configuration explanation:

- `[build-system]`: Specifies build tool (setuptools)
- `[project]`: Project metadata
  - `name`: Project name
  - `version`: Version number (follows semantic versioning)
  - `dependencies`: Project dependency list
  - `requires-python`: Python version requirement
- `[project.urls]`: Project-related links
- `[tool.setuptools]`: setuptools configuration

Although Smithery automatically generates Dockerfile, providing a custom Dockerfile ensures successful deployment:

```dockerfile
# Multi-stage build for weather-mcp-server
FROM python:3.12-slim-bookworm as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml requirements.txt ./
COPY server.py ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8081

# Expose port (Smithery uses 8081)
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the MCP server
CMD ["python", "server.py"]
```

Dockerfile configuration explanation:

- **Base Image**: `python:3.12-slim-bookworm` - Lightweight Python image
- **Working Directory**: `/app` - Application root directory
- **Port**: `8081` - Smithery platform standard port
- **Start Command**: `python server.py` - Run MCP server

Here, we need to Fork the `hello-agents` repository, get the source code in `code`, and create a repository named `weather-mcp-server` using your own GitHub, changing `yourusername` to your GitHub username.

(3) Submit to Smithery

Open your browser and visit [https://smithery.ai/](https://smithery.ai/). Log in to Smithery using your GitHub account. Click the "Publish Server" button on the page, enter your GitHub repository URL: `https://github.com/yourusername/weather-mcp-server`, and wait for publication.

Once publication is complete, you can see a page similar to this, as shown in Figure 10.10:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-10.png" alt="" width="85%"/>
  <p>Figure 10.10 Smithery Publication Success Page</p>
</div>



Once the server is successfully published, users can use it in the following ways:

Method 1: Through Smithery CLI

```bash
# Install Smithery CLI
npm install -g @smithery/cli

# Install your server
smithery install weather-mcp-server
```

Method 2: Configure in Claude Desktop

```json
{
  "mcpServers": {
    "weather": {
      "command": "smithery",
      "args": ["run", "weather-mcp-server"]
    }
  }
}
```

Method 3: Use in HelloAgents

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools.builtin.protocol_tools import MCPTool

agent = SimpleAgent(name="Weather Assistant", llm=HelloAgentsLLM())

# Use Smithery-installed server
weather_tool = MCPTool(
    server_command=["smithery", "run", "weather-mcp-server"]
)
agent.add_tool(weather_tool)

response = agent.run("How's the weather in Beijing today?")
```

Of course, this is just an example, and there are more usages to explore on your own. Figure 10.11 below shows the information included when an MCP tool is successfully published, displaying the service name "Weather", its unique identifier `@jjyaoao/weather-mcp-server`, and status information. The Tools area shows the methods we just implemented, and the Connect area provides technical information needed to connect and use this service, including the service's **access URL address** and **configuration code snippets** in multiple languages/environments. If you want to learn more, you can click this [link](https://smithery.ai/server/@jjyaoao/weather-mcp-server).

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/10-figures/10-11.png" alt="" width="85%"/>
  <p>Figure 10.11 Successfully Published MCP Tool on Smithery</p>
</div>

Now it's time to create your own MCP server!



## 10.6 Chapter Summary

This chapter systematically introduced three core protocols for agent communication: MCP, A2A, and ANP, and explored their design philosophies, application scenarios, and practical methods.

**Protocol Positioning:**

- **MCP (Model Context Protocol)**: As a bridge between agents and tools, provides a unified tool access interface, suitable for enhancing the capabilities of individual agents.
- **A2A (Agent-to-Agent Protocol)**: As a dialogue system between agents, supports direct communication and task negotiation, suitable for close collaboration in small-scale teams.
- **ANP (Agent Network Protocol)**: As the "internet" for agents, provides service discovery, routing, and load balancing mechanisms, suitable for building large-scale, open agent networks.

**HelloAgents Integration Solution**

In the `HelloAgents` framework, these three protocols are uniformly abstracted as tools (Tool), achieving seamless integration, allowing developers to flexibly add different levels of communication capabilities to agents:

```python
# Unified Tool interface
from hello_agents.tools import MCPTool, A2ATool, ANPTool

# All protocols can be added to Agent as Tools
agent.add_tool(MCPTool(...))
agent.add_tool(A2ATool(...))
agent.add_tool(ANPTool(...))
```

**Practical Experience Summary**

- Prioritize using mature community MCP services to reduce unnecessary redundant development.
- Choose appropriate protocols based on system scale: A2A is recommended for small-scale collaboration scenarios, while ANP should be used for large-scale network scenarios.

After completing this chapter, it is recommended that you:

1. **Hands-on Practice**:
   - Build your own MCP server
   - Create multi-agent collaboration systems using protocols
   - Combination application strategies for MCP, A2A, and ANP
2. **In-depth Learning**:
   - Read MCP official documentation: https://modelcontextprotocol.io
   - Read A2A official documentation: https://a2a-protocol.org/latest/
   - Read ANP official documentation: https://agent-network-protocol.com/guide/
3. **Participate in Community**:
   - Contribute new MCP services to the community
   - Share your own developed agent implementation cases
   - Participate in technical standard discussions for related protocols, or ask questions in Issues or directly help HelloAgents support new example cases

**Congratulations on completing Chapter 10!**

You now have mastered the core knowledge of agent communication protocols. Keep up the good work! 🚀

## Exercises

> **Note**: Some exercises do not have standard answers. The focus is on cultivating learners' comprehensive understanding and practical ability in agent communication protocols.

1. This chapter introduced three agent communication protocols: MCP, A2A, and ANP. Please analyze:

   - Section 10.1.2 compared the design philosophies of the three protocols. Please analyze in depth: Why does MCP emphasize "context sharing", A2A emphasize "conversational collaboration", and ANP emphasize "network topology"? What core problems do these design philosophies solve respectively?
   - Suppose you want to build an "intelligent customer service system" that requires the following functions: (1) Access customer database and order system; (2) Multiple professional customer service agents collaborate to handle complex problems; (3) Support large-scale concurrent user requests. Please select the most appropriate protocol for each function and explain your reasoning.
   - Can the three protocols be used in combination? Please design a practical application scenario showing how to use MCP, A2A, and ANP simultaneously to build a complete agent system. Draw a system architecture diagram and explain the responsibilities of each protocol.

2. MCP (Model Context Protocol) is the standard protocol for agent-tool communication. Based on the content in Section 10.2, please think deeply:

   > **Note**: This is a hands-on practice question, actual operation is recommended

   - In the MCP server implementation in Section 10.2.3, we defined core methods such as `list_tools` and `call_tool`. Please extend this implementation by adding a new MCP server that provides the following tools: (1) Database query tool; (2) Data visualization tool; (3) Report generation tool. Require that tools can collaborate to complete complex data analysis tasks.
   - The MCP protocol supports two important concepts: "Resources" and "Prompts", but this chapter mainly focuses on "Tools". Please consult the MCP official documentation to understand the design purposes of Resources and Prompts, and design an application scenario showing how to use these three core concepts to build a more powerful agent system.
   - MCP uses JSON-RPC 2.0 as the underlying communication protocol and communicates between processes via stdio. Please analyze: What are the advantages and limitations of this design? If you need to support remote MCP servers (accessed via HTTP/WebSocket), how should the current implementation be extended?

3. A2A (Agent-to-Agent Protocol) supports conversational collaboration between agents. Based on the content in Section 10.3, please complete the following extended practice:

   > **Note**: This is a hands-on practice question, actual operation is recommended

   - In the "research team" case in Section 10.3.4, researchers and writers collaborate through the A2A protocol to complete paper writing. Please extend this case by adding a third agent "Reviewer", which can review paper quality and provide revision suggestions. Design the collaboration process among the three agents and implement complete code.
   - The A2A protocol defines message types such as `task` and `task_result`. Please analyze: If conflicts occur during collaboration (such as two agents having different opinions on the same issue), how should a conflict resolution mechanism be designed? Please extend the A2A protocol by adding message types such as "negotiation" and "voting".
   - Compare the A2A protocol with multi-agent frameworks such as AutoGen and CAMEL introduced in Chapter 6: What is the relationship between A2A as a standard protocol and these frameworks? Can they replace each other? Please design a solution that allows agents based on the A2A protocol to communicate with agents in the AutoGen framework.

4. ANP (Agent Network Protocol) supports large-scale agent networks. Based on the content in Section 10.4, please analyze in depth:

   - Section 10.4.2 introduced ANP's network topology design, including star, mesh, hierarchical, and other structures. Please analyze: In what scenarios should which topology structure be chosen? If the network scale expands from 10 agents to 1000 agents, how should the topology structure evolve?
   - The ANP protocol supports "routing" and "discovery" mechanisms, allowing agents to dynamically find suitable collaboration partners. Please design an "intelligent routing algorithm": automatically select the optimal message routing path based on task type, agent capabilities, network load, and other factors.
   - In the "smart city" case in Section 10.4.4, multiple agents collaborate to manage city systems. Please think: If a critical agent (such as a traffic management agent) fails, how should the entire system respond? Please design a "fault tolerance mechanism", including fault detection, backup switching, state recovery, and other functions.

5. Security and privacy protection of agent communication protocols are key issues in practical applications. Please think:

   - In the MCP client implementation in Section 10.2.4, agents can call any tool provided by the MCP server. Please analyze: What security risks does this design have? If the MCP server provides dangerous operations (such as deleting files, executing system commands), how should a permission control mechanism be designed?
   - A2A and ANP protocols involve communication between multiple agents, which may contain sensitive information (such as user privacy data, business secrets). Please design an "end-to-end encryption" solution: ensure that messages are not eavesdropped or tampered with during transmission, while supporting agent identity authentication and access control.
   - In large-scale agent networks, malicious agents may send false information, launch denial-of-service attacks, or steal data from other agents. Please design a "trust evaluation system": dynamically evaluate the trustworthiness of each agent based on historical behavior, collaboration quality, community evaluation, and other factors, and adjust communication strategies accordingly.

## References

[1] Anthropic. (2024). *Model Context Protocol*. Retrieved October 7, 2025, from https://modelcontextprotocol.io/

[2] The A2A Project. (2025). *A2A Protocol: An open protocol for agent-to-agent communication*. Retrieved October 7, 2025, from https://a2a-protocol.org/

[3] Chang, G., Lin, E., Yuan, C., Cai, R., Chen, B., Xie, X., & Zhang, Y. (2025). *Agent Network Protocol technical white paper*. arXiv. https://doi.org/10.48550/arXiv.2508.00007

