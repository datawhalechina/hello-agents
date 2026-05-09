import os

os.chdir(r"D:\学习\AI\hello_agents")
import sys

sys.path.insert(0, r"D:\学习\AI\hello_agents")

from tools.builtin.secure_terminal_tool import SecureTerminalTool

terminal = SecureTerminalTool(workspace=".")

# Test the dangerous command
command = "cmd /c del /f /q C:\\Windows\\System32\\config\\*"
print(f"Command: {command}")
print(f"Command lower: {command.lower()}")

# Test _classify_risk
import re

DANGEROUS_SUB_PATTERNS = [
    r"del\s+/[fq]\s+",
    r"format\s+",
    r"rd\s+/s\s+",
    r"rmdir\s+/s\s+",
]

command_lower = command.lower()
for pattern in DANGEROUS_SUB_PATTERNS:
    match = re.search(pattern, command_lower)
    print(f"Pattern {pattern}: {'MATCH' if match else 'NO MATCH'}")

# Test full run
result = terminal.run({"command": command})
print(f"\nResult:\n{result}")
