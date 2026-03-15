# test_minimax_agent.py
"""
Test script for MiniMax LLM provider with HelloAgents SimpleAgent.

Before running, set your MiniMax API key:
    export MINIMAX_API_KEY=your-api-key-here

Usage:
    python test_minimax_agent.py
"""
from dotenv import load_dotenv
from hello_agents import ToolRegistry
from hello_agents.tools import CalculatorTool
from minimax_llm import MiniMaxLLM
from my_simple_agent import MySimpleAgent

# Load environment variables from .env file
load_dotenv()

# Create MiniMax LLM instance
llm = MiniMaxLLM()

# Test 1: Basic conversation with MiniMax
print("=== Test 1: Basic Conversation (MiniMax) ===")
basic_agent = MySimpleAgent(
    name="MiniMax Assistant",
    llm=llm,
    system_prompt="You are a helpful AI assistant powered by MiniMax. Answer concisely.",
)

response1 = basic_agent.run("Hello! What model are you, and what can you help me with?")
print(f"Response: {response1}\n")

# Test 2: Tool-augmented Agent with MiniMax
print("=== Test 2: Tool-Augmented Agent (MiniMax) ===")
tool_registry = ToolRegistry()
calculator = CalculatorTool()
tool_registry.register_tool(calculator)

enhanced_agent = MySimpleAgent(
    name="MiniMax Enhanced Assistant",
    llm=llm,
    system_prompt="You are an intelligent assistant with tool access. Use tools when needed.",
    tool_registry=tool_registry,
    enable_tool_calling=True,
)

response2 = enhanced_agent.run("Calculate 256 * 128 + 99")
print(f"Tool-augmented response: {response2}\n")

# Test 3: Streaming response
print("=== Test 3: Streaming Response (MiniMax) ===")
print("Streaming: ", end="")
for chunk in basic_agent.stream_run("Explain what an AI agent is in 2-3 sentences."):
    pass  # Content is printed in real-time by stream_run
print()

print("\n=== All MiniMax tests completed! ===")
