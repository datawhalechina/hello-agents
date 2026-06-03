# Chapter 10: Agent Communication Protocols

In previous chapters, we built fully functional standalone agents with reasoning, tool invocation, and memory capabilities. However, when attempting to build more complex AI systems, natural questions arise: How can agents efficiently interact with the external world? How can multiple agents collaborate with each other?

This is precisely the core problem that agent communication protocols aim to solve. This chapter introduces three communication protocols to the HelloAgents framework: MCP (Model Context Protocol) for standardized communication between agents and tools, A2A (Agent-to-Agent Protocol) for peer-to-peer collaboration between agents, and ANP (Agent Network Protocol) for building large-scale agent networks. Together, these three protocols form the infrastructure layer for agent communication.

By studying this chapter, you will not only master practical skills for all three protocols; more importantly, you will understand why they were designed, why they are designed the way they are (and not otherwise), and how to make correct technology choices from first principles.

## 10.1 Agent Communication Protocol Fundamentals

### 10.1.1 First Principles: Why Specialized Communication Protocols?

Before diving into specific protocols, we must answer a fundamental question: With mature schemes like HTTP, gRPC, and REST APIs, why do we still need protocols purpose-built for agents?

The answer lies in the first principles—understanding the essential differences between agents and traditional software.

Traditional software communication assumes the caller knows what it wants to do and the callee offers deterministic capabilities.

Traditional API call:
Developer (human) → writes deterministic code → calls deterministic interface → gets deterministic result

LLM-based agents fundamentally break this assumption:

Agent invocation:
LLM (dynamic decision-making) → decides at runtime what to call → invocation is non-deterministic → results need to be interpreted again

This gap produces three new problems that traditional protocols cannot elegantly solve:

1) Dynamic discovery: Agents decide at run time which tools they need; you cannot hardcode every interface at development time.

2) Semantic understanding: Agents need to “understand” what tools can do, not just mechanically “call” them.

3) Autonomous collaboration: Multiple agents need to negotiate and divide labor like human teams, not just perform simple request–response.

These three problems map directly to the three protocols in this chapter.

Table 10.1 Three core problems and corresponding protocols

- How agents use tools → MCP → Agents ↔ Tools/Data sources
- How agents collaborate with other agents → A2A → Agent ↔ Agent (peer-to-peer)
- How lots of agents interconnect at scale → ANP → Agent networks (large-scale)

The key insight: these protocols are not in competition. They are complementary designs that solve problems at different scales. We will return to this unified view in Section 10.6.

### 10.1.2 A Real Pain Point: The M×N Integration Dilemma

Recall the ReAct agent we built in Chapter 7—it already possesses powerful reasoning and tool invocation capabilities. Here’s a typical usage scenario:

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

This agent works well—until you want to access more external services (GitHub, databases, file systems), and the pain begins:

```python
# Traditional approach: manually integrate each service
class GitHubTool(BaseTool):
    """Manually write GitHub API adapter: HTTP requests, auth, error handling..."""
    def run(self, repo_url): ...

class DatabaseTool(BaseTool):
    """Manually write database adapter: connection, query, exception handling..."""
    def run(self, query): ...

class WeatherTool(BaseTool):
    """Manually write weather API adapter..."""
    def run(self, location): ...

# Repeat this for every new service, and re-do for each LLM application
```

This is the classic M×N problem:

M AI apps × N tools = M×N integration code

Every AI app has to write its own integration for each tool; the code isn’t compatible or reusable across apps and grows combinatorially.

The core value of communication protocols is to turn M×N into M+N. Like the TCP/IP layer for the Internet, standard protocols let different devices interoperate without writing per-pair glue. With a standard, the code above becomes:

```python
from hello_agents.tools import MCPTool

# Connect to an MCP server and automatically obtain all tools it provides
mcp_tool = MCPTool()  # built-in server provides basic tools

# Connect to community-maintained MCP servers—no bespoke adapters required
github_mcp = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-github"])
database_mcp = MCPTool(server_command=["python", "database_mcp_server.py"])

agent.add_tool(github_mcp)
agent.add_tool(database_mcp)
```

This change is fundamental: standardized interfaces unify access to diverse services; interoperability enables seamless integration across developers; dynamic discovery lets agents discover new capabilities at runtime; scalability enables easy module addition.

### 10.1.3 Design Philosophy and Underlying Logic of the Three Protocols

Having clarified “why protocols,” let’s examine how the three mainstream protocols are designed. Pay close attention to the logic behind each one.

**(1) MCP: The bridge between agents and tools—the “USB‑C of AI”**

Proposed by Anthropic in late 2024, MCP takes inspiration from USB‑C.

Before USB‑C, every device had its own port (charging barrel, HDMI, VGA...). USB‑C unified connection—any device supporting it could interoperate.

MCP’s logic is simple:

1) Tool providers implement an MCP Server once → any MCP-compatible app can use it.

2) App developers implement an MCP Client once → they can access any MCP Server.

3) Integration cost drops from M×N to M+N.

As in Figure 10.1, MCP is more than an RPC protocol. Its deeper philosophy is “context sharing.” When an agent accesses a code repository, an MCP Server can return file contents along with structure, dependencies, commit history—rich context that helps the agent decide better.

Figure 10.1 MCP design philosophy

**(2) A2A: Dialogue between agents**

A2A, led by Google in 2025, addresses problems MCP cannot.

A crucial first-principles point: agent collaboration ≠ tool invocation.

Table 10.2 Tool invocation vs. agent collaboration

- Counterparty nature: tools are passive/stateless; agents are proactive/with memory
- Interaction pattern: single request–response vs multi-turn negotiation/long-running tasks
- Task duration: instant vs minutes to days
- Result nature: deterministic data vs outcomes that may require clarification/iteration

A2A’s core metaphor is hiring an expert:

1) Review the expert’s “business card/CV” (learn what they can do);

2) Assign a “task” (state the goal, not the steps);

3) They may ask clarifying questions;

4) They report progress while working;

5) They deliver the final result.

A2A turns these steps into protocol mechanisms (see Section 10.3). Its philosophy is peer-to-peer: every agent is both provider and consumer, avoiding coordinator bottlenecks.

Figure 10.2 A2A design philosophy

**(3) ANP: Infrastructure for agent networks**

ANP, maintained by the open-source community, has a more ambitious goal. It addresses A2A’s limits at scale:

The P2P dilemma:
Agent A wants “an agent who can do financial analysis”
 → But it doesn’t know who can (discovery)
 → Even if it finds one, how to trust a stranger? (trust)
 → With different protocols, how to interoperate? (intercom)

ANP’s core philosophy: make agents first-class citizens of the Internet—discoverable, reachable, and trustable like websites. The logic:

1) In an open network, start with trust → a decentralized identity layer (DIDs);

2) Agents may “speak different languages,” so agree on how to talk → a meta-protocol negotiation layer;

3) Only then can they exchange information and collaborate → an application collaboration layer.

As in Figure 10.3, ANP borrows from the Web (DNS, HTTP, semantic web) to rebuild a “discovery–trust–interconnect” substrate for agents.

Figure 10.3 ANP design philosophy

**(4) A unifying analogy and comparison**

The most intuitive way to understand the three protocols is to use three levels of human collaboration:

- MCP: using tools (computer, software, databases) → how to acquire capability
- A2A: division of labor among colleagues (you help me, I help you) → how to collaborate peer-to-peer
- ANP: the broader business society (find partners, establish trust, sign contracts) → how to interconnect on an open network

Technical comparison (abridged):

- Full names: Model Context Protocol; Agent-to-Agent Protocol; Agent Network Protocol
- Problems solved: agent↔tool; agent↔agent; agent networks
- Core units: Tools/Resources/Prompts; Task; DID + semantic descriptions
- Scope: one-to-one; one-to-one; many-to-many
- Discovery mechanism: list tools; Agent Card; semantic graph + DID
- Trust: in-app authorization; endpoint trust; decentralized identity (cryptography)
- Underlying protocols: JSON‑RPC 2.0; HTTP + JSON (SSE/Webhook); DID + JSON‑LD + multi‑protocol negotiation
- Proponents: Anthropic; Google; open-source community
- Maturity: high (de facto standard); medium (rapid evolution); early (exploratory)

**(5) How to choose? A quick decision tree**

Your need is?

- Let an AI app use external tools/data?
  → Use MCP

- Let your agent collaborate with another (known) agent?
  → Use A2A

- Build an open network where masses of agents can discover each other?
  → Use ANP

A practical note: these ecosystems are still early. MCP is the most mature—start there. A2A can be introduced as needed. ANP targets future large-scale open networks: worth tracking, but no need to rush for production. Favor implementations backed by major vendors and active maintenance.

### 10.1.4 HelloAgents Protocol Architecture

With the design principles clear, how do we implement and use them in HelloAgents? Our goal: make it simple to use these protocols while retaining flexibility for complex scenarios.

As shown in Figure 10.4, HelloAgents adopts a three-layer architecture: a protocol implementation layer, a tool wrapper layer, and an agent integration layer. This separation of concerns echoes the layered philosophies of the three protocols themselves.

Figure 10.4 HelloAgents communication protocol design

- Protocol implementation layer: concrete implementations of all three protocols. MCP is built on FastMCP; A2A builds on Google’s a2a‑sdk; ANP is a lightweight conceptual implementation for discovery/networking (there is an official implementation, AgentConnect, but given its pace of change, we simulate the concepts here).

- Tool wrapper layer: wraps protocol implementations into a unified Tool interface. MCPTool, A2ATool, and ANPTool all inherit from BaseTool and expose a consistent run() so agents can use them uniformly.

- Agent integration layer: all agents (ReActAgent, SimpleAgent, etc.) use protocol tools via the Tool System without worrying about underlying details.

### 10.1.5 Learning Objectives and Quick Start

This chapter’s structure:

```
hello_agents/
├── protocols/                          # Communication protocols
│   ├── mcp/                            # MCP (Model Context Protocol)
│   │   ├── client.py                   # MCP client (supports 5 transports)
│   │   ├── server.py                   # MCP server (FastMCP wrapper)
│   │   └── utils.py                    # Utilities (create_context/parse_context)
│   ├── a2a/                            # A2A (Agent-to-Agent Protocol)
│   │   └── implementation.py           # A2A server/client (a2a-sdk, optional)
│   └── anp/                            # ANP (Agent Network Protocol)
│       └── implementation.py           # ANP discovery/registration (conceptual)
└── tools/builtin/                      # Built-in tools
    └── protocol_tools.py               # MCPTool/A2ATool/ANPTool wrappers
```

This chapter is practice-oriented: the goal is to apply these protocols in your own projects. Given the early state of ecosystems, don’t reinvent the wheel. Prepare the environment:

```bash
# Install HelloAgents (Chapter 10 version)
pip install "hello-agents[protocol]==0.2.2"

# Install NodeJS (needed by some MCP Servers); see Additional-Chapter
```

A minimal experience of all three:

```python
from hello_agents.tools import MCPTool, A2ATool, ANPTool

# 1) MCP: tool access
mcp_tool = MCPTool()
result = mcp_tool.run({
    "action": "call_tool",
    "tool_name": "add",
    "arguments": {"a": 10, "b": 20}
})
print(f"MCP calculation result: {result}")  # Output: 30.0

# 2) ANP: service discovery
anp_tool = ANPTool()
anp_tool.run({
    "action": "register_service",
    "service_id": "calculator",
    "service_type": "math",
    "endpoint": "http://localhost:8080"
})
services = anp_tool.run({"action": "discover_services"})
print(f"Discovered services: {services}")

# 3) A2A: agent communication
a2a_tool = A2ATool("http://localhost:5000")
print("A2A tool created successfully")
```

Subsequent sections will dive into each protocol’s design, hands-on usage, and best practices.

## 10.2 MCP in Practice

Let’s go deep on MCP—how to enable agents to access external tools and resources.

### 10.2.1 Concept Introduction

**(1) MCP: the “USB‑C” for agents**

As noted in Section 10.1.3, agents often need to read local files, query databases, search GitHub, send Slack messages... Traditionally you write adapters for each service, and function call schemas differ wildly across LLM platforms, forcing rewrites when switching models. Like USB‑C unified device I/O, MCP unifies agent↔tool interaction—any model that supports MCP can access the same tools seamlessly.

**(2) Why a three-layer architecture?**

MCP uses Host, Client, and Server. See Figure 10.5: In Claude Desktop, you ask “What documents are on my desktop?”

Figure 10.5 MCP example

The responsibilities reflect separation of concerns:

- Host (Claude Desktop): user-facing UX; manages conversation; focuses on user experience.

- Client (inside the Host): connects to the MCP Server; sends/receives requests; one client per server; focuses on protocol communication.

- Server (e.g., filesystem MCP Server): executes actual operations and returns results; focuses on concrete functionality.

End-to-end: question → Host → model analysis → needs file info → Client connects → Server executes → results → model answers. The big win: developers write MCP Servers and ignore Host/Client implementation.

Why JSON‑RPC 2.0 underneath? Following “don’t reinvent the wheel”: lightweight, language-agnostic, supports requests plus notifications, and is stable.

**(3) MCP’s three core primitives**

MCP defines three core capabilities—Tools, Resources, and Prompts. Understanding them is understanding MCP.

Why distinguish them? Control boundaries. Side-effecting Tools require explicit authorization; read-only Resources are relatively safe.

Example Tool definition:

```json
{
  "name": "send_email",
  "description": "Send an email",
  "inputSchema": {
    "type": "object",
    "properties": {
      "to": {"type": "string"},
      "subject": {"type": "string"},
      "body": {"type": "string"}
    }
  }
}
```

**(4) How does an LLM decide which tool to use?**

Figure 10.6 shows the flow:

1) Tool discovery: after connecting, the client calls list_tools() to obtain tool descriptions (name, function, parameters).

2) Context construction: the client converts tool lists into LLM-friendly prompt formats, e.g.:
You can use these tools:
- read_file(path: str): read content at a path
- search_code(query: str, language: str): search a codebase

3) Model reasoning: the LLM analyzes the user’s request plus tool descriptions and decides whether and which tool to call.

4) Tool execution: the client invokes the chosen tool via the server.

5) Result integration: results are returned to the LLM to produce the final answer.

This is fully automated; the model relies entirely on the quality of tool descriptions—leading directly to best practices (see Section 10.2.5).

**(5) MCP and Function Calling: complementary, not competitive**

A common question: I already use Function Calling; why do I need MCP? From first principles and experience:

- Function Calling is the model’s capability (when to “make the call,” how to speak, how to parse).

- MCP is the standardized network—an engineering substrate that enables any phone to dial any other phone.

They are complementary: Function Calling is the “skill,” MCP is the “standard.” Below we’ll see how to use MCP in HelloAgents.

### 10.2.2 Using the MCP Client

HelloAgents provides full MCP client functionality based on FastMCP 2.0, with both async and sync APIs. For most apps, use async for better concurrency and long-running tasks.

**(1) Connect to an MCP server**

```python
import asyncio
from hello_agents.protocols import MCPClient

async def connect_to_server():
    # Method 1: connect to community file system server
    client = MCPClient([
        "npx", "-y",
        "@modelcontextprotocol/server-filesystem",
        "."
    ])

    async with client:
        tools = await client.list_tools()
        print(f"Available tools: {[t['name'] for t in tools]}")

    # Method 2: connect to your own Python MCP server
    client = MCPClient(["python", "my_mcp_server.py"])
    async with client:
        pass

asyncio.run(connect_to_server())
```

**(2) Discover available tools**

```python
async def discover_tools():
    client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

    async with client:
        tools = await client.list_tools()

        print(f"Server provides {len(tools)} tools:")
        for tool in tools:
            print(f"\nTool name: {tool['name']}")
            print(f"Description: {tool.get('description', 'No description')}")

            if 'inputSchema' in tool:
                schema = tool['inputSchema']
                if 'properties' in schema:
                    print("Parameters:")
                    for param_name, param_info in schema['properties'].items():
                        param_type = param_info.get('type', 'any')
                        param_desc = param_info.get('description', '')
                        print(f"  - {param_name} ({param_type}): {param_desc}")

asyncio.run(discover_tools())
```

**(3) Call tools**

```python
async def use_tools():
    client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

    async with client:
        result = await client.call_tool("read_file", {"path": "my_README.md"})
        print(f"File content:\n{result}")

        result = await client.call_tool("list_directory", {"path": "."})
        print(f"Current directory files: {result}")

        result = await client.call_tool("write_file", {
            "path": "output.txt",
            "content": "Hello from MCP!"
        })
        print(f"Write result: {result}")

asyncio.run(use_tools())
```

Safer call pattern:

```python
async def safe_tool_call():
    client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

    async with client:
        try:
            result = await client.call_tool("read_file", {"path": "nonexistent.txt"})
            print(result)
        except Exception as e:
            print(f"Tool call failed: {e}")

asyncio.run(safe_tool_call())
```

**(4) Access resources**

```python
# List resources
resources = client.list_resources()
print(f"Available resources: {[r['uri'] for r in resources]}")

# Read a resource
resource_content = client.read_resource("file:///path/to/resource")
print(f"Resource content: {resource_content}")
```

**(5) Use prompts**

```python
# List prompts
prompts = client.list_prompts()
print(f"Available prompts: {[p['name'] for p in prompts]}")

# Get a prompt
prompt = client.get_prompt("code_review", {"language": "python"})
print(f"Prompt content: {prompt}")
```

**(6) Example: GitHub MCP service**

```python
"""
GitHub MCP Service Example

Note: set environment variable:
    Windows: $env:GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
    Linux/macOS: export GITHUB_PERSONAL_ACCESS_TOKEN="your_token_here"
"""

from hello_agents.tools import MCPTool

github_tool = MCPTool(
    server_command=["npx", "-y", "@modelcontextprotocol/server-github"]
)

print("📋 Available tools:")
result = github_tool.run({"action": "list_tools"})
print(result)

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

### 10.2.3 Transport Methods Explained

A hallmark of MCP is transport agnosticism. The protocol runs over multiple channels. HelloAgents (FastMCP 2.0) supports five transport methods so you can choose per scenario.

**(1) Overview**

- Memory (for testing)
- Stdio (local processes)
- Stdio with args
- HTTP/SSE/StreamableHTTP (remote)

**(2) Usage examples**

```python
from hello_agents.tools import MCPTool

# 1) Memory transport (built-in demo server)
mcp_tool = MCPTool()

# 2) Stdio (local dev)
mcp_tool = MCPTool(server_command=["python", "examples/mcp_example_server.py"])

# 3) Stdio with args
mcp_tool = MCPTool(server_command=["python", "examples/mcp_example_server.py", "--debug"])

# 4) Stdio via npx (community servers)
mcp_tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

# 5) HTTP/SSE/StreamableHTTP
# For remote transports, prefer using MCPClient directly
```

(3) Memory transport

```python
from hello_agents.tools import MCPTool

mcp_tool = MCPTool()
print(mcp_tool.run({"action": "list_tools"}))

print(mcp_tool.run({
    "action": "call_tool",
    "tool_name": "add",
    "arguments": {"a": 10, "b": 20}
}))
```

**(4) Stdio**

```python
from hello_agents.tools import MCPTool

mcp_tool = MCPTool(server_command=["python", "my_mcp_server.py"])
mcp_tool = MCPTool(server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."])

print(mcp_tool.run({"action": "list_tools"}))

print(mcp_tool.run({
    "action": "call_tool",
    "tool_name": "read_file",
    "arguments": {"path": "README.md"}
}))
```

**(5) HTTP transport**

```python
import asyncio
from hello_agents.protocols import MCPClient

async def test_http_transport():
    client = MCPClient("http://api.example.com/mcp")

    async with client:
        tools = await client.list_tools()
        print(f"Remote server tools: {len(tools)}")

        result = await client.call_tool("process_data", {
            "data": "Hello, World!",
            "operation": "uppercase"
        })
        print(f"Remote processing result: {result}")

# asyncio.run(test_http_transport())
```

**(6) SSE transport**

```python
import asyncio
from hello_agents.protocols import MCPClient

async def test_sse_transport():
    client = MCPClient(
        "http://localhost:8080/sse",
        transport_type="sse"
    )

    async with client:
        result = await client.call_tool("stream_process", {
            "input": "Large data processing request",
            "stream": True
        })
        print(f"Streaming result: {result}")

# asyncio.run(test_sse_transport())
```

**(7) StreamableHTTP**

```python
import asyncio
from hello_agents.protocols import MCPClient

async def test_streamable_http_transport():
    client = MCPClient(
        "http://localhost:8080/mcp",
        transport_type="streamable_http"
    )

    async with client:
        tools = await client.list_tools()
        print(f"StreamableHTTP tools: {len(tools)}")

# asyncio.run(test_streamable_http_transport())
```

### 10.2.4 Using MCP Tools in Agents

Beyond direct clients, we want agents to automatically invoke MCP tools. HelloAgents provides an MCPTool wrapper to integrate MCP servers into the agent’s toolchain.

**(1) Automatic expansion**

MCPTool supports automatic expansion. When you add one MCPTool, it expands all server-provided tools into independent tools callable like any other.

Method 1: built-in demo server

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

agent = SimpleAgent(name="Assistant", llm=HelloAgentsLLM())

mcp_tool = MCPTool(name="calculator")
agent.add_tool(mcp_tool)
# ✅ MCP tool 'calculator' expanded into 6 independent tools

response = agent.run("Calculate 25 times 16")
print(response)  # 25 × 16 = 400
```

Expanded tools include:

- calculator_add
- calculator_subtract
- calculator_multiply
- calculator_divide
- calculator_greet
- calculator_get_system_info

Method 2: connect to external MCP servers

```python
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool

agent = SimpleAgent(name="File Assistant", llm=HelloAgentsLLM())

fs_tool = MCPTool(
    name="filesystem",
    description="Access local file system",
    server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
)
agent.add_tool(fs_tool)

custom_tool = MCPTool(
    name="custom_server",
    description="Custom business logic server",
    server_command=["python", "my_mcp_server.py"]
)
agent.add_tool(custom_tool)

response = agent.run("Please read the my_README.md file and summarize its main content")
print(response)
```

When using multiple MCP servers, give each MCPTool a unique name. This name prefixes the expanded tool names to avoid collisions (e.g., fs_read_file, fs_write_file). For writing your own MCP server, see Section 10.5.

**(2) How automatic expansion works**

```python
# User code
fs_tool = MCPTool(name="fs", server_command=[...])
agent.add_tool(fs_tool)

# Internally:
# 1) Connect and discover tools
# 2) Create wrappers: fs_read_text_file, fs_write_file, ...
# 3) Register with the agent

# Agent run:
# 1) Decide to call fs_read_text_file
# 2) Generate args
# 3) Convert to MCP payload:
#    {"action": "call_tool", "tool_name": "read_text_file", "arguments": {"path": "README.md"}}
# 4) Invoke server and return content
```

The system auto-converts types per schema (e.g., strings “25”, “16” to numbers).

**(3) Practical case: Intelligent Document Assistant**

```python
"""
Multi-Agent Collaborative Intelligent Document Assistant
- Agent1: GitHub search expert
- Agent2: Document generation expert
"""
from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.tools import MCPTool
from dotenv import load_dotenv

load_dotenv(dotenv_path="../HelloAgents/.env")

github_searcher = SimpleAgent(
    name="GitHub Search Expert",
    llm=HelloAgentsLLM(),
    system_prompt="""You are a GitHub search expert...
Keep it concise..."""
)
github_tool = MCPTool(
    name="gh",
    server_command=["npx", "-y", "@modelcontextprotocol/server-github"]
)
github_searcher.add_tool(github_tool)

document_writer = SimpleAgent(
    name="Document Generation Expert",
    llm=HelloAgentsLLM(),
    system_prompt="""You are a document generation expert...
Output a full Markdown report..."""
)
fs_tool = MCPTool(
    name="fs",
    server_command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
)
document_writer.add_tool(fs_tool)

search_task = "Search for GitHub repositories about 'AI agent', return the top 5 most relevant results"
search_results = github_searcher.run(search_task)

report_task = f"""
Based on the following GitHub search results, generate a Markdown format research report:
{search_results}
...requirements...
"""
report_content = document_writer.run(report_task)

with open("report.md", "w", encoding="utf-8") as f:
    f.write(report_content)
```

### 10.2.5 MCP Best Practices

- Write tool descriptions for models, not people. The LLM decides purely from the description.
  - Poor: “Query user”
  - Better: “Look up user details by user ID. Use when you need email, signup time, and other profile data.”

- Principle of least privilege. Expose only necessary tools; destructive operations should require authorization. This is why Tools (side effects) and Resources (read-only) are distinct.

- Prefer Resources to reduce hallucinations. Provide authoritative data as Resources rather than relying on model memory.

- Reuse mature community servers. Especially those with strong backing and active maintenance.

### 10.2.6 MCP Community Ecosystem

A major advantage of MCP is a rich ecosystem. Anthropic and the community have produced many MCP servers covering file systems, databases, APIs, and more. You can reuse instead of writing adapters from scratch.

Three key resources:

1) Awesome MCP Servers: https://github.com/punkpeye/awesome-mcp-servers

2) MCP Servers Website: https://mcpservers.org/

3) Official MCP Servers: https://github.com/modelcontextprotocol/servers

Interesting cases:

- Automated web testing (Playwright)
- Intelligent note assistant (Obsidian + Perplexity)
- Project management automation (Jira + GitHub)
- Content creation workflow (YouTube + Notion + Spotify)

## 10.3 A2A in Practice

### 10.3.1 Concept Introduction

From “tools” to “coworkers”: why MCP isn’t enough

MCP solves agent↔tool. But we increasingly need agent↔agent collaboration. Consider travel planning:

Lead agent → delegate → flight agent (searches, compares, decides)
           → delegate → hotel agent (understands needs, recommends)

The key difference: the other side isn’t a “tool” but another decision-making agent.

A2A’s metaphor is hiring an expert (see Section 10.1.3). It abstracts “review CV, assign task, clarify, report progress, deliver” into protocol mechanisms.

Core concept 1: Agent Card (the agent’s “business card”)

Every agent publishes a capability declaration at /.well-known/agent.json:

```json
{
  "name": "Flight Booking Agent",
  "description": "Search, compare, and book flights",
  "url": "https://flights.example.com/a2a",
  "capabilities": {"streaming": true, "pushNotifications": true},
  "skills": [{
    "id": "search_flights",
    "name": "Flight Search",
    "description": "Search flights by origin, destination, and date"
  }]
}
```

Why Agent Card? It’s the basis for dynamic discovery—agents discover and understand others at runtime without hardcoding, like reading an expert’s resume before hiring.

Core concept 2: Task and Artifact

A2A doesn’t “call a function”—it creates a task with a lifecycle:

submitted → working → input-required (agent may ask questions) → completed / failed / canceled

Why a “task” model? Collaboration is long-running and multi-turn. Tasks naturally support async execution, status tracking, and mid-course clarification—things request–response cannot express well.

Core concept 3: Task lifecycle

A2A defines standardized lifecycle states for task management: creation, negotiation, delegation, in-progress, completion, failure (Figure 10.7).

A2A request lifecycle (Figure 10.8) shows agent discovery, authentication, send message API, and streaming (SSE/webhooks).

Interaction modes:

- Synchronous request/response
- Streaming (SSE) for real-time progress
- Push notifications (Webhooks) for long-running tasks

MCP and A2A are complementary

An agent can use MCP to call tools (e.g., crunch numbers in a spreadsheet) and A2A to delegate to other agents (ask a colleague for help). In practice, both coexist:

User agent ←→ Financial agent (via A2A)
                  │
                  ▼
          Databases/Calculators/Reporting (via MCP)

### 10.3.2 A2A Protocol in Practice

Most A2A implementations are samples; even Python options can be cumbersome. Here we simulate the protocol concepts and implement partial functionality via a2a‑sdk.

**(1) Create a simple A2A agent (calculator)**
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
import time

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

**(3) Advanced: negotiation between agents**

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

### 10.3.5 A2A Best Practices

- Design a clear Agent Card: describe skills so others can judge “should I call you?”—same spirit as MCP’s “descriptions are for models.”

- Use streaming or push for long tasks: don’t make callers wait blindly; leverage SSE/Webhooks.

- Handle input-required gracefully: ask for missing info instead of guessing or failing outright.

## 10.4 ANP in Practice

### 10.4.1 Concept Introduction

From “known peers” to an “open network of strangers”: why ANP?

A2A solves P2P between known agents. As the number grows from a few to thousands, new issues appear (10.1.3’s “P2P dilemma”):

- How to discover unknown agents?
- How to trust them?
- How to communicate across different protocols?

Analogy: A2A is “how to talk after you have a phone number,” while ANP is “how to find the right agent in the wild and establish trust.”

ANP’s three-layer logic (order matters):

- Identity & crypto: decentralized identity (DID) → trust first
- Meta-protocol: agree on how to communicate → then interoperate
- Application layer: exchange and collaborate → finally do work

Core concepts:

- DID-based decentralized identity (cryptographic trust)
- Meta-protocol negotiation (agree on transport/format)
- Semantic, machine-readable agent descriptions (JSON‑LD / semantic web)

Figure 10.9 shows the overall flow. A typical “discover–verify–negotiate–collaborate” pipeline:

1) Discover: A finds “a financial analysis agent B” via a semantic index;

2) Verify: A fetches B’s DID document and validates signatures with B’s public key;

3) Negotiate: A and B agree on protocol and formats;

4) Collaborate: exchange messages and execute tasks.

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

print(f"✅ Registered {len(discovery.list_all_services())} compute nodes")

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

## 10.5 Building a Custom MCP Server

Beyond consuming existing MCP services, you’ll often need custom servers for your business.

### 10.5.1 Create Your First MCP Server

Why build a custom server?

- Encapsulate business logic
- Access private data securely
- Optimize performance for hot paths/low latency
- Extend functionality (proprietary models, special hardware)

Teaching case: Weather MCP server

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

## 10.6 A Unified View: How the Three Protocols Work Together

### 10.6.1 Why three protocols, not one?

They solve problems at different scales:

- MCP → single agent ↔ tools (micro: capability acquisition)
- A2A → agent ↔ agent (meso: peer collaboration)
- ANP → agent networks (macro: open interconnection)

Like human collaboration:
- MCP is “using tools”
- A2A is “division of labor”
- ANP is “forming a society”

### 10.6.2 A complete story of collaboration

Coexistence:

- ANP layer: Agent A discovers and verifies financial expert Agent B on an open network
- A2A layer: A assigns “analyze quarterly financials” to B; they negotiate and exchange progress
- MCP layer: B calls databases and calculators via MCP to complete the task

In HelloAgents, all three are abstracted as tools:

```python
from hello_agents.tools import MCPTool, A2ATool, ANPTool

agent.add_tool(MCPTool(...))   # micro: tool capabilities
agent.add_tool(A2ATool(...))   # meso: collaborate with agents
agent.add_tool(ANPTool(...))   # macro: discover partners on the network
```

### 10.6.3 Shared design kernel

Despite solving different problems, they share design principles:

- Standardization: unify interfaces to avoid fragmentation (MCP primitives / A2A Task / ANP DID)
- Dynamic discovery: runtime capability discovery (MCP list tools / A2A Agent Card / ANP semantic discovery)
- Separation of concerns: each protocol focuses on its layer
- Borrow from mature ecosystems: MCP↔USB‑C; A2A↔hiring experts; ANP↔the Web
- Designed for autonomy: assume the counterparty is a decision-making agent, not a passive executor

### 10.6.4 Selection and rollout advice

- Start with MCP: most mature, immediate value
- Add A2A as needed: when a single agent can’t carry all tasks and you need specialists
- Be cautious with ANP: aimed at large, open networks; unless you’re truly building an open ecosystem, don’t rush
- Don’t overdesign: often MCP alone suffices—don’t add complexity for its own sake

## 10.7 State of the Ecosystem and Future Trends

A deep pattern: the adoption speed of a protocol matches the urgency of the pain it solves.

### 10.7.1 MCP: from protocol to de facto standard

- Native in Anthropic Claude
- OpenAI announced MCP support (2025)—cross-vendor consensus
- Integrated into mainstream IDEs (VS Code, Cursor, Zed)
- Thousands of open-source MCP servers already exist

Why MCP is winning early:
- The pain is acute (M×N integration)
- Low barrier (JSON‑RPC; write a server in hours)
- Immediate value (tools deliver instant utility)
- Big tech backing (once multiple giants adopt, it becomes a standard)

Trends: remote MCP (HTTP/SSE) for SaaS servers, stronger OAuth patterns, npm-like registries.

### 10.7.2 A2A: a consortium-driven collaboration standard

Launched by Google in 2025, with 50+ companies (Salesforce, SAP, ServiceNow...) backing it; donated to a neutral foundation mid-2025.

Why a consortium? MCP benefits even with one-sided implementation; agent collaboration needs both sides on the same protocol—classic cold start. A broad alliance builds network effects.

Reality check: A2A still evolving fast; specs not fully frozen. Good to pilot and track; evaluate stability for production.

### 10.7.3 ANP: a visionary “agent internet” exploration

ANP is the most forward-looking and the earliest-stage: community-led, core specs (DID, meta-protocol, semantic desc) published, but lacking big commercial push.

Why slow adoption? Pain horizon:
- MCP solves “today’s pain” (tool integration)
- A2A solves “tomorrow’s pain” (multi-agent collaboration)
- ANP solves “the day after” (open, large-scale interconnection and trust)

Most applications are still “single agent + tools.” But the questions ANP asks are real and inevitable at scale. Its exploration has strategic value.

## 10.8 Summary

This chapter systematically introduced three core protocols for agent communication. More important than memorizing details is internalizing the common engineering mindset behind them.

Protocol positioning:
- MCP: the bridge between agents and tools; unify tool access; enhance a single agent’s capability
- A2A: dialogue between agents; task negotiation; suited for tight collaboration
- ANP: the “internet” of agents; discovery, trust, interconnect; suited for large, open networks

One-line memory:
MCP lets agents “use tools,” A2A lets agents “ask colleagues for help,” ANP lets agents “find and trust each other across the network.”

Five mindsets to internalize:
1) For any new tech, ask “what problem does it solve?”
2) Think from first principles—agents make autonomous decisions, so we need new protocols.
3) Understand “why it’s designed this way”—MCP’s primitives draw control boundaries; A2A’s tasks support long collaboration; ANP’s DID provides decentralized trust.
4) Embrace layering and composition—no single universal protocol; combine focused ones.
5) Use analogies to build intuition—USB‑C, hiring experts, the internet.

Suggested next steps:

- Hands-on:
  - Build your own MCP server
  - Create multi-agent collaboration systems
  - Combine MCP, A2A, and ANP effectively

- In-depth reading:
  - MCP docs: https://modelcontextprotocol.io
  - A2A docs: https://a2a-protocol.org/latest/
  - ANP docs: https://agent-network-protocol.com/guide/

- Community participation:
  - Contribute new MCP servers
  - Share your agent implementations
  - Join standards discussions; open issues; help HelloAgents with new examples

Congratulations on completing Chapter 10!
You now have the core knowledge of agent communication protocols. Keep going! 🚀

## Exercises

> **Note**: Some exercises do not have standard answers. The goal is to cultivate comprehensive understanding and practical ability.

1) MCP, A2A, ANP analysis:
   - Based on Section 10.1.3, analyze why MCP emphasizes “context sharing,” A2A emphasizes “conversational collaboration,” and ANP emphasizes “network topology.” What core problems does each solve?
   - Suppose you’re building an “intelligent customer service system” needing: (1) access to customer DB and order systems; (2) multiple specialized agents collaborating on complex issues; (3) large-scale concurrent users. Choose the best protocol for each and explain why.
   - Can they be combined? Design a scenario that uses MCP, A2A, and ANP together; draw the system architecture and explain each protocol’s role.

2) MCP deep dive (hands-on recommended):
   > **Note**: This is a hands-on practice question, actual operation is recommended
   
   - Extend the MCP server from Section 10.5.1 to add: (1) database query tool; (2) data visualization tool; (3) report generation tool. Require collaboration among tools for complex analysis.
   - Study Resources and Prompts from the MCP docs, then design a scenario that leverages Tools, Resources, and Prompts together.
   - MCP uses JSON‑RPC 2.0 over stdio. Analyze pros/cons. If you need remote servers over HTTP/WebSocket, how would you extend the implementation?

3) A2A collaboration (hands-on recommended):
   > **Note**: This is a hands-on practice question, actual operation is recommended
   
   - Extend the “research team” case in Section 10.3.3 by adding a “Reviewer” agent that evaluates papers and suggests revisions. Design the workflow and implement it.
   - If conflicts arise (two agents disagree), how to resolve? Extend A2A with “negotiation” and “voting” message types.
   - Compare A2A with multi-agent frameworks like AutoGen and CAMEL (Chapter 6). What’s their relationship? Can they replace each other? Design a way for A2A-based agents to communicate with AutoGen agents.

4) ANP large-scale networking:
   - Choose topologies (star/mesh/hierarchical) for different scenarios. As the network scales from 10 to 1000 agents, how should topology evolve?
   - Design an intelligent routing algorithm considering task types, agent capabilities, and network load.
   - In a distributed scheduling system, if a critical agent fails, how should the system respond? Design fault detection, failover, and state recovery.

5) Security and privacy:
   - In the MCP client implementation in Section 10.2.4, agents can call any tool provided by the MCP server. Please analyze: What security risks does this design have? If the MCP server provides dangerous operations (such as deleting files, executing system commands), how should a permission control mechanism be designed?
   - A2A and ANP protocols involve communication between multiple agents, which may contain sensitive information (such as user privacy data, business secrets). Please design an "end-to-end encryption" solution: ensure that messages are not eavesdropped or tampered with during transmission, while supporting agent identity authentication and access control.
   - In large-scale agent networks, malicious agents may send false information, launch denial-of-service attacks, or steal data from other agents. Please design a "trust evaluation system": dynamically evaluate the trustworthiness of each agent based on historical behavior, collaboration quality, community evaluation, and other factors, and adjust communication strategies accordingly.

## References

[1] Anthropic. (2024). *Model Context Protocol*. Retrieved October 7, 2025, from https://modelcontextprotocol.io/

[2] The A2A Project. (2025). *A2A Protocol: An open protocol for agent-to-agent communication*. Retrieved October 7, 2025, from https://a2a-protocol.org/

[3] Chang, G., Lin, E., Yuan, C., Cai, R., Chen, B., Xie, X., & Zhang, Y. (2025). *Agent Network Protocol technical white paper*. arXiv. https://doi.org/10.48550/arXiv.2508.00007

