import os
import json

def test_user_memory_tool():
    from src.agents.helper_agent import UserMemoryTool
    tool = UserMemoryTool(memory_file="test_memory.json")
    
    # Test get
    res = tool.run({"action": "get"})
    assert "beginner" in res or "level" in res
    
    # Test update
    res = tool.run({"action": "update", "level": "intermediate", "record": "hello_world"})
    assert res == "记忆更新成功"
    
    # Test get again
    res = tool.run({"action": "get"})
    assert "intermediate" in res
    assert "hello_world" in res
    
    # cleanup
    file_path = os.path.join(os.path.dirname(__file__), "../../data/test_memory.json")
    if os.path.exists(file_path):
        os.remove(file_path)
    print("UserMemoryTool test passed!")

if __name__ == "__main__":
    test_user_memory_tool()
