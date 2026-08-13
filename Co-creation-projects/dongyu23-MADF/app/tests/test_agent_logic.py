import pytest
from unittest.mock import patch
from hello_agents import SimpleAgent
from app.agent.agent import ParticipantAgent
from app.agent.memory import SharedMemory

def test_memory_operations():
    mem = SharedMemory(n_participants=3)
    # Check initial state (it's not empty string, contains headers)
    initial_str = mem.get_context_str()
    assert "【过往总结】" in initial_str
    assert "(暂无)" in initial_str
    
    mem.add_message("Alice", "Hi")
    # get_context_str returns "Alice: Hi" in format
    assert "Alice: Hi" in mem.get_context_str()
    
    mem.add_message("Bob", "Hello")
    mem.add_message("Charlie", "Hey")

def test_agent_initialization():
    persona = {
        "name": "Socrates",
        "bio": "Philosopher",
        "title": "Thinker",
        "theories": ["Method"],
        "stance": "Neutral",
        "system_prompt": "Be wise."
    }
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="Truth")
    assert isinstance(agent, SimpleAgent)
    assert agent.name == "Socrates"
    # System prompt is taken from persona['system_prompt'] directly
    assert "Be wise." in agent.system_prompt
    assert "Truth" in agent.theme
    assert "Method" in agent.theories

def test_agent_think_listen():
    persona = {"name": "Socrates", "bio": "B", "title": "T", "theories": [], "stance": "S", "system_prompt": "P"}
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="T")
    
    # Mock response for "listen"
    with patch.object(agent, "run", return_value='{"decision":"LISTEN","inner_monologue":"I should listen"}'):
        thought = agent.think("Context")
    assert thought["action"] == "listen"

def test_agent_think_speak():
    persona = {"name": "Socrates", "bio": "B", "title": "T", "theories": [], "stance": "S", "system_prompt": "P"}
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="T")
    
    # Mock response for "speak"
    with patch.object(agent, "run", return_value='{"decision":"APPLY_SPEAK","inner_monologue":"I will speak"}'):
        thought = agent.think("Context")
    assert thought["action"] == "apply_to_speak"

def test_agent_speak_stream():
    persona = {"name": "Socrates", "bio": "B", "title": "T", "theories": [], "stance": "S", "system_prompt": "P"}
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="T")
    
    thought = {"action": "speak", "thought": "T", "target": "All", "previous": "P", "mind": "M", "benefit": "B"}
    
    with patch.object(agent, "stream_run", return_value=iter(["Hel", "lo"])):
        chunks = list(agent.speak(thought, "Context"))
    assert chunks == ["Hel", "lo"]

def test_agent_think_error_handling():
    persona = {"name": "Socrates", "bio": "B", "title": "T", "theories": [], "stance": "S", "system_prompt": "P"}
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="T")
    
    with patch.object(agent, "run", return_value=""):
        thought = agent.think("Context")
    assert thought is None

def test_parse_think_response_chinese_apply():
    persona = {"name": "Socrates", "bio": "B", "title": "T", "theories": [], "stance": "S", "system_prompt": "P"}
    agent = ParticipantAgent("Socrates", persona, n_participants=3, theme="T")
    content = """决策：申请发言
内心独白：我有新观点要补充
引用理论：博弈论
前序观点：上一位观点过于理想化
预期贡献：提供现实约束条件"""
    thought = agent._parse_think_response(content)
    assert thought["action"] == "apply_to_speak"
