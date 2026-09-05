"""公共工具函数模块"""

import json
import re
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List


class JSONExtractor:
    """
    统一的 JSON 提取器
    
    从各种格式的 LLM 响应中提取 JSON 数据，支持：
    - 纯 JSON 响应
    - Markdown 代码块中的 JSON
    - Finish[...] 格式（ReAct 标准格式）
    - 混杂文本中的 JSON
    """
    
    @staticmethod
    def extract(
        response: str,
        required_fields: Optional[List[str]] = None,
        fallback_fields: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        从响应中提取 JSON
        
        Args:
            response: LLM 响应文本
            required_fields: 必需的字段列表，用于验证和优先选择
            fallback_fields: 当字段缺失时的默认值
            
        Returns:
            提取的 JSON 字典
            
        Raises:
            ValueError: 无法提取有效 JSON 时
        """
        if not response or not response.strip():
            raise ValueError("响应为空")
        
        # 初始化默认值
        fallback_fields = fallback_fields or {}
        required_fields = required_fields or []
        
        # 尝试多种提取方法
        extractors = [
            JSONExtractor._extract_from_finish,
            JSONExtractor._extract_direct_json,
            JSONExtractor._extract_from_markdown_json,
            JSONExtractor._extract_from_markdown,
            JSONExtractor._extract_from_braces,
        ]
        
        last_error = None
        for extractor in extractors:
            try:
                result = extractor(response)
                if result is not None:
                    # 应用默认值
                    for key, default_value in fallback_fields.items():
                        if key not in result:
                            result[key] = default_value
                    
                    # 如果有必需字段，优先选择包含这些字段的结果
                    if required_fields:
                        missing = [f for f in required_fields if f not in result]
                        if not missing:
                            return result
                    else:
                        return result
            except Exception as e:
                last_error = e
                continue
        
        # 尝试从历史记录中提取（用于 PlanAndSolve 等场景）
        try:
            result = JSONExtractor._extract_from_history(response)
            if result is not None:
                for key, default_value in fallback_fields.items():
                    if key not in result:
                        result[key] = default_value
                return result
        except Exception as e:
            last_error = e
        
        raise ValueError(f"响应中未找到有效的 JSON 数据: {last_error}")
    
    @staticmethod
    def _extract_from_finish(response: str) -> Optional[Dict[str, Any]]:
        """从 Finish[...] 格式中提取"""
        match = re.search(r"Finish\[(.*)\]", response, re.DOTALL)
        if match:
            content = match.group(1).strip()
            return JSONExtractor._parse_json_with_retry(content)
        return None
    
    @staticmethod
    def _extract_direct_json(response: str) -> Optional[Dict[str, Any]]:
        """直接解析 JSON"""
        stripped = response.strip()
        if stripped.startswith('{'):
            return JSONExtractor._parse_json_with_retry(stripped)
        return None
    
    @staticmethod
    def _extract_from_markdown_json(response: str) -> Optional[Dict[str, Any]]:
        """从 ```json 代码块中提取"""
        if "```json" not in response:
            return None
        
        json_start = response.find("```json") + 7
        json_end = response.find("```", json_start)
        if json_end == -1:
            return None
        
        json_str = response[json_start:json_end].strip()
        return JSONExtractor._parse_json_with_retry(json_str)
    
    @staticmethod
    def _extract_from_markdown(response: str) -> Optional[Dict[str, Any]]:
        """从普通 ``` 代码块中提取"""
        if "```" not in response:
            return None
        
        json_start = response.find("```") + 3
        json_end = response.find("```", json_start)
        if json_end == -1:
            return None
        
        json_str = response[json_start:json_end].strip()
        # 移除可能的语言标识符
        if json_str.startswith("json"):
            json_str = json_str[4:].strip()
        
        if json_str.startswith('{'):
            return JSONExtractor._parse_json_with_retry(json_str)
        return None
    
    @staticmethod
    def _extract_from_braces(response: str) -> Optional[Dict[str, Any]]:
        """从大括号中提取所有可能的 JSON 对象"""
        json_candidates = []
        i = 0
        
        while i < len(response):
            if response[i] == '{':
                brace_count = 0
                brace_start = i
                brace_end = i
                
                for j in range(i, len(response)):
                    if response[j] == '{':
                        brace_count += 1
                    elif response[j] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            brace_end = j + 1
                            break
                
                if brace_end > brace_start:
                    json_str = response[brace_start:brace_end]
                    try:
                        parsed = JSONExtractor._parse_json_with_retry(json_str)
                        if isinstance(parsed, dict):
                            json_candidates.append((parsed, len(parsed)))
                    except Exception:
                        pass
                    i = brace_end
                else:
                    i += 1
            else:
                i += 1
        
        if json_candidates:
            # 优先选择包含 'content' 字段的，否则选择字段最多的
            for parsed, _ in json_candidates:
                if 'content' in parsed and parsed.get('content'):
                    return parsed
            
            # 返回字段最多的
            return max(json_candidates, key=lambda x: x[1])[0]
        
        return None
    
    @staticmethod
    def _extract_from_history(response: str) -> Optional[Dict[str, Any]]:
        """从历史记录格式中提取（用于 PlanAndSolve 等场景）"""
        if "步骤" not in response and "结果" not in response:
            return None
        
        # 查找所有包含 JSON 的步骤结果
        json_matches = re.findall(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
        if not json_matches:
            json_matches = re.findall(r'(\{"column_title".*?"topics".*?\})', response, re.DOTALL)
        
        for json_str in json_matches:
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                continue
        
        return None
    
    @staticmethod
    def _parse_json_with_retry(json_str: str) -> Dict[str, Any]:
        """尝试多种方式解析 JSON"""
        # 方法1: 直接解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 方法2: 修复未转义的换行符
        fixed = json_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        try:
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass
        
        # 方法3: 提取并重新构建 JSON（针对内容字段）
        result = JSONExtractor._rebuild_json_from_fields(json_str)
        if result:
            return result
        
        raise json.JSONDecodeError("无法解析 JSON", json_str, 0)
    
    @staticmethod
    def _rebuild_json_from_fields(json_str: str) -> Optional[Dict[str, Any]]:
        """从字段中重新构建 JSON"""
        title_match = re.search(r'"title"\s*:\s*"([^"]*)"', json_str)
        level_match = re.search(r'"level"\s*:\s*(\d+)', json_str)
        word_count_match = re.search(r'"word_count"\s*:\s*(\d+)', json_str)
        needs_expansion_match = re.search(r'"needs_expansion"\s*:\s*(true|false)', json_str)
        
        # 提取 content（可能跨多行）
        content_match = re.search(r'"content"\s*:\s*"(.*?)"(?=\s*[,}])', json_str, re.DOTALL)
        if not content_match:
            content_match = re.search(r'"content"\s*:\s*"([^"]*(?:\\.[^"]*)*)"', json_str, re.DOTALL)
        
        # 如果没有找到任何字段，返回 None
        if not any([title_match, level_match, content_match]):
            return None
        
        result = {}
        if title_match:
            result['title'] = title_match.group(1)
        if level_match:
            result['level'] = int(level_match.group(1))
        if content_match:
            content = content_match.group(1)
            content = content.replace('\\n', '\n').replace('\\r', '\r').replace('\\t', '\t')
            result['content'] = content
        if word_count_match:
            result['word_count'] = int(word_count_match.group(1))
        else:
            result['word_count'] = len(result.get('content', ''))
        if needs_expansion_match:
            result['needs_expansion'] = needs_expansion_match.group(1) == 'true'
        else:
            result['needs_expansion'] = False
        
        result.setdefault('subsections', [])
        result.setdefault('metadata', {})
        
        return result


def parse_react_output(text: str) -> Tuple[Optional[str], Optional[str]]:
    """
    解析 ReAct Agent 的输出
    
    支持多种格式：
    - 标准 ReAct 格式: Thought: ... Action: ...
    - 中文格式: 思考: ... 行动: ...
    - Finish[...] 格式
    
    Args:
        text: LLM 的原始响应文本
        
    Returns:
        (thought, action) 元组
    """
    if not text or not text.strip():
        print("▸️  警告: LLM 返回了空响应")
        return None, None
    
    # 解析 Thought
    thought = None
    thought_end_pos = 0
    thought_patterns = [
        r"Thought:\s*(.*?)(?=\nAction:|\nFinish:|$)",  # 标准格式
        r"思考:\s*(.*?)(?=\n行动:|\n完成:|$)",  # 中文格式
    ]
    
    for pattern in thought_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            thought = match.group(1).strip()
            if thought:
                thought_end_pos = match.end()
                break
    
    # 解析 Action
    action = None
    action_patterns = [
        r"Action:\s*(.*?)(?=\nThought:|\nObservation:|\nFinish:|$)",  # 标准格式
        r"行动:\s*(.*?)(?=\n思考:|\n观察:|\n完成:|$)",  # 中文格式
        r"Finish\[(.*?)\]",  # Finish 格式
    ]
    
    for pattern in action_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            action = match.group(1).strip()
            if action:
                if pattern == r"Finish\[(.*?)\]":
                    action = f"Finish[{action}]"
                break
    
    # 尝试其他 Finish 格式
    if not action:
        finish_patterns = [
            r"Finish\s*\[(.*?)\]",
            r"完成\s*\[(.*?)\]",
            r"最终答案:\s*(.*?)(?=\n|$)",
        ]
        for pattern in finish_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                content = match.group(1).strip()
                if content:
                    action = f"Finish[{content}]"
                    break
    
    # 如果仍未找到 Action，检查是否有完整内容
    if not action:
        action = _try_extract_complete_content(text, thought, thought_end_pos)
    
    if not action:
        print(f"▸️  警告: 未能解析出 Action")
        print(f"   响应内容（前500字符）: {text[:500]}")
        print(f"   已解析的 Thought: {thought[:100] if thought else 'None'}...")
    
    return thought, action


def _try_extract_complete_content(
    text: str,
    thought: Optional[str],
    thought_end_pos: int
) -> Optional[str]:
    """
    尝试从响应中提取完整内容并包装为 Finish 格式
    
    Args:
        text: 原始文本
        thought: 已解析的 thought
        thought_end_pos: thought 结束位置
        
    Returns:
        包装后的 action 或 None
    """
    # 查找 JSON 内容
    json_match = None
    brace_start = text.find('{')
    if brace_start != -1:
        brace_end = text.rfind('}')
        if brace_end > brace_start:
            potential_json = text[brace_start:brace_end + 1]
            if '"content"' in potential_json or "'content'" in potential_json:
                json_match = re.search(r'\{.*?"content".*?\}', potential_json, re.DOTALL)
    
    # 确定要检查的文本
    if thought:
        remaining_text = text[thought_end_pos:].strip()
        if not remaining_text:
            remaining_text = thought
    else:
        remaining_text = text.strip()
    
    # 移除前缀
    remaining_text = re.sub(r'^(Action|Finish|行动|完成)[:：]\s*', '', remaining_text, flags=re.IGNORECASE)
    
    if not remaining_text and not json_match:
        return None
    
    # 使用 JSON 内容
    if json_match:
        remaining_text = json_match.group(0)
        json_str = remaining_text
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        json_complete = (open_braces == close_braces) and open_braces > 0
    else:
        json_complete = False
        json_match_check = re.search(r'\{.*?"content".*?\}', remaining_text, re.DOTALL)
        if json_match_check:
            json_str = json_match_check.group(0)
            open_braces = json_str.count('{')
            close_braces = json_str.count('}')
            json_complete = (open_braces == close_braces) and open_braces > 0
    
    # 检查完成标记
    has_ending = bool(re.search(
        r'(总结|结论|结语|小结|综上所述|总之|最后|end|conclusion)',
        remaining_text[-500:] if len(remaining_text) > 500 else remaining_text,
        re.IGNORECASE
    ))
    has_continuation = bool(re.search(
        r'(未完待续|待续|继续|to be continued|未完|待补充)',
        remaining_text,
        re.IGNORECASE
    ))
    
    content_length = len(remaining_text)
    is_substantial = content_length > 200
    
    # 判断是否完成
    is_complete = False
    completion_reason = []
    
    if json_complete:
        is_complete = True
        completion_reason.append("完整的 JSON 结构")
    elif has_ending:
        is_complete = True
        completion_reason.append("有结尾标记")
    elif is_substantial and not has_continuation:
        is_complete = True
        completion_reason.append("内容足够长且无未完标记")
    
    if is_complete:
        print(f"▸ 检测到完整正文内容（长度: {content_length} 字符），自动添加 Finish 前缀")
        print(f"   - 判断依据: {', '.join(completion_reason)}")
        return f"Finish[{remaining_text}]"
    else:
        print(f"▸️  检测到部分正文内容（长度: {content_length} 字符），但可能未完成")
        if has_continuation:
            print(f"   - 检测到'未完待续'标记，继续循环让模型完成写作")
        elif not is_substantial:
            print(f"   - 内容长度不足，继续循环让模型完成写作")
        return None


def get_current_timestamp() -> str:
    """获取当前时间戳（ISO 格式）"""
    return datetime.now().isoformat()

