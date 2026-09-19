import json
import re

def parse_json_from_response(content):
    """
    Attempts to parse JSON from a string, handling code blocks if present.
    Also handles common LLM JSON errors like unescaped quotes.
    """
    try:
        content = content.strip()
        
        # 1. Try to extract JSON from markdown code blocks
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
        if json_match:
            content = json_match.group(1)
        else:
            # 2. If no code blocks, try to find the first outer-most JSON object or array
            # Find the first '{' or '['
            start_idx = -1
            end_idx = -1
            stack = []
            
            for i, char in enumerate(content):
                if char in '{[':
                    if start_idx == -1:
                        start_idx = i
                    stack.append(char)
                elif char in '}]':
                    if stack:
                        last = stack[-1]
                        if (last == '{' and char == '}') or (last == '[' and char == ']'):
                            stack.pop()
                            if not stack:
                                end_idx = i + 1
                                break
            
            if start_idx != -1 and end_idx != -1:
                content = content[start_idx:end_idx]

        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Standard JSON parse failed: {e}. Attempting cleanup...")
        
        try:
            import dirtyjson
            return dirtyjson.loads(content)
        except Exception:
            pass

        # Cleanup: remove trailing commas, comments
        try:
            # Remove single-line comments // ...
            content = re.sub(r'//.*', '', content)
            # Remove trailing commas before } or ]
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            
            return json.loads(content)
        except Exception:
            pass
            
        print(f"Failed to parse JSON content: {content[:200]}...")
        return None
