"""
智能答案匹配器（Smart Answer Matcher）

GAIA 准精确匹配的增强版本，通过多策略级联匹配处理语义等价的答案。

匹配策略（按优先级从高到低）：
1. quasi_exact      — GAIA 官方准精确匹配（快速通道）
2. numeric_equiv    — 数值等价（科学计数法、中文数字、分数）
3. unit_conversion  — 单位换算（"2h30m" ↔ "150 minutes"）
4. math_eval        — 数学表达式求值（"π/2" ↔ "1.5708"）
5. semantic_equiv   — 语义嵌入相似度（基于 token 的 Jaccard + 关键词）
6. llm_judge        — LLM 兜底裁决
"""

from typing import Dict, Any, List, Optional, Tuple
import re
import math
import json
from dataclasses import dataclass


@dataclass
class MatchResult:
    match: bool
    method: str = "none"
    confidence: float = 0.0
    details: str = ""


class SmartAnswerMatcher:
    """智能答案匹配器"""

    # 中文数字映射
    CN_NUM_MAP = {
        "零": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": 10,
        "百": 100,
        "千": 1000,
        "万": 10000,
        "亿": 100000000,
        "兩": 2,
    }

    # 常见单位换算表：全部归一化到 SI 基准单位
    UNIT_CONVERSIONS = {
        # 时间 → 秒
        "s": 1,
        "sec": 1,
        "secs": 1,
        "second": 1,
        "seconds": 1,
        "min": 60,
        "mins": 60,
        "minute": 60,
        "minutes": 60,
        "h": 3600,
        "hr": 3600,
        "hrs": 3600,
        "hour": 3600,
        "hours": 3600,
        "d": 86400,
        "day": 86400,
        "days": 86400,
        # 长度 → 米
        "m": 1,
        "meter": 1,
        "meters": 1,
        "metre": 1,
        "metres": 1,
        "cm": 0.01,
        "centimeter": 0.01,
        "centimeters": 0.01,
        "mm": 0.001,
        "millimeter": 0.001,
        "millimeters": 0.001,
        "km": 1000,
        "kilometer": 1000,
        "kilometers": 1000,
        "inch": 0.0254,
        "inches": 0.0254,
        "in": 0.0254,
        "ft": 0.3048,
        "foot": 0.3048,
        "feet": 0.3048,
        "yard": 0.9144,
        "yards": 0.9144,
        "mile": 1609.344,
        "miles": 1609.344,
        # 质量 → 克
        "g": 1,
        "gram": 1,
        "grams": 1,
        "kg": 1000,
        "kilogram": 1000,
        "kilograms": 1000,
        "mg": 0.001,
        "milligram": 0.001,
        "milligrams": 0.001,
        "lb": 453.592,
        "lbs": 453.592,
        "pound": 453.592,
        "pounds": 453.592,
        "oz": 28.3495,
        "ounce": 28.3495,
        "ounces": 28.3495,
        # 体积 → 升
        "l": 1,
        "liter": 1,
        "liters": 1,
        "litre": 1,
        "litres": 1,
        "ml": 0.001,
        "milliliter": 0.001,
        "milliliters": 0.001,
        "gal": 3.78541,
        "gallon": 3.78541,
        "gallons": 3.78541,
        "cup": 0.236588,
        "cups": 0.236588,
        "tsp": 0.00492892,
        "teaspoon": 0.00492892,
        "teaspoons": 0.00492892,
        "tbsp": 0.0147868,
        "tablespoon": 0.0147868,
        "tablespoons": 0.0147868,
        # 温度用特殊处理
        "c": None,
        "celsius": None,
        "f": None,
        "fahrenheit": None,
        "k": None,
        "kelvin": None,
    }

    # 单位正则模式
    UNIT_PATTERN = re.compile(
        r"^(-?\d+(?:\.\d+)?)\s*("
        + "|".join(re.escape(u) for u in UNIT_CONVERSIONS)
        + r")$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        llm=None,
        use_semantic: bool = True,
        use_llm_judge: bool = True,
        semantic_threshold: float = 0.85,
        llm_judge_threshold: float = 0.6,
    ):
        self.llm = llm
        self.use_semantic = use_semantic
        self.use_llm_judge = use_llm_judge and llm is not None
        self.semantic_threshold = semantic_threshold
        self.llm_judge_threshold = llm_judge_threshold

    def match(self, prediction: str, ground_truth: str) -> MatchResult:
        """多策略级联匹配，任一通过即返回成功

        Args:
            prediction: 预测答案
            ground_truth: 标准答案

        Returns:
            MatchResult: 匹配结果
        """
        if not prediction or not ground_truth:
            return MatchResult(match=False, method="empty_input")

        # 1. 准精确匹配（快速通道）
        if self._quasi_exact_match(prediction, ground_truth):
            return MatchResult(match=True, method="quasi_exact", confidence=1.0)

        # 2. 数值等价
        result = self._numeric_equivalence(prediction, ground_truth)
        if result.match:
            return result

        # 3. 单位换算等价
        result = self._unit_conversion_match(prediction, ground_truth)
        if result.match:
            return result

        # 4. 数学表达式等价
        result = self._math_expression_equiv(prediction, ground_truth)
        if result.match:
            return result

        # 5. 语义等价
        if self.use_semantic:
            result = self._semantic_equivalence(prediction, ground_truth)
            if result.match:
                return result

        # 6. LLM Judge 兜底
        if self.use_llm_judge:
            result = self._llm_judge(prediction, ground_truth)
            if result.match:
                return result

        return MatchResult(match=False, method="no_match", confidence=0.0)

    # ==================== 策略 1：准精确匹配 ====================

    def _quasi_exact_match(self, a: str, b: str) -> bool:
        """GAIA 官方准精确匹配"""
        return self._normalize_answer(a) == self._normalize_answer(b)

    def _normalize_answer(self, answer: str) -> str:
        if not answer:
            return ""
        answer = answer.strip()
        if "," in answer:
            parts = [self._normalize_single(p.strip()) for p in answer.split(",")]
            parts.sort()
            return ",".join(parts)
        return self._normalize_single(answer)

    def _normalize_single(self, answer: str) -> str:
        answer = answer.strip().lower()
        articles = ["the", "a", "an"]
        words = answer.split()
        if words and words[0] in articles:
            words = words[1:]
            answer = " ".join(words)
        answer = (
            answer.replace("$", "").replace("%", "").replace("€", "").replace("£", "")
        )
        answer = re.sub(r"(\d),(\d)", r"\1\2", answer)
        answer = " ".join(answer.split())
        answer = answer.rstrip(".,;:!?")
        return answer

    # ==================== 策略 2：数值等价 ====================

    def _numeric_equivalence(self, a: str, b: str) -> MatchResult:
        """数值等价检测"""
        na = self._parse_number(a)
        nb = self._parse_number(b)
        if na is not None and nb is not None:
            if math.isclose(na, nb, rel_tol=1e-6):
                return MatchResult(
                    match=True,
                    method="numeric_equiv",
                    confidence=0.99,
                    details=f"{na} ≈ {nb}",
                )
        return MatchResult(match=False)

    def _parse_number(self, s: str) -> Optional[float]:
        """从字符串中解析数值"""
        s = s.strip().lower()

        # 直接浮点数
        try:
            return float(s)
        except ValueError:
            pass

        # 科学计数法
        sci = re.match(r"^(-?\d+(?:\.\d+)?)[eE]\s*([+-]?\d+)$", s)
        if sci:
            try:
                return float(sci[1]) * (10 ** float(sci[2]))
            except ValueError:
                pass

        # 分数
        frac = re.match(r"^(-?\d+)/(\d+)$", s)
        if frac:
            try:
                return int(frac[1]) / int(frac[2])
            except (ValueError, ZeroDivisionError):
                pass

        # 中文数字
        cn_val = self._chinese_to_number(s)
        if cn_val is not None:
            return float(cn_val)

        # 百分数
        pct = re.match(r"^(-?\d+(?:\.\d+)?)%$", s)
        if pct:
            try:
                return float(pct[1]) / 100.0
            except ValueError:
                pass

        return None

    def _chinese_to_number(self, s: str) -> Optional[int]:
        """中文数字转整数"""
        s = s.strip()
        if not s:
            return None
        if not all(c in self.CN_NUM_MAP for c in s):
            return None
        result = 0
        current = 0
        for c in s:
            val = self.CN_NUM_MAP[c]
            if val >= 10:
                if current == 0:
                    current = 1
                result += current * val
                current = 0
            else:
                current = current * 10 + val
        result += current
        return result

    # ==================== 策略 3：单位换算等价 ====================

    def _unit_conversion_match(self, a: str, b: str) -> MatchResult:
        """单位换算等价检测"""
        va, ua = self._parse_with_unit(a)
        vb, ub = self._parse_with_unit(b)

        # 温度特殊处理
        if va is not None and ua is not None and vb is not None and ub is not None:
            temp_result = self._temperature_conversion(va, ua, vb, ub)
            if temp_result is not None:
                return temp_result

            # 常规单位换算
            base_a = self._to_base_unit(va, ua)
            base_b = self._to_base_unit(vb, ub)
            if base_a is not None and base_b is not None:
                if math.isclose(base_a, base_b, rel_tol=1e-4):
                    return MatchResult(
                        match=True,
                        method="unit_conversion",
                        confidence=0.98,
                        details=f"{va}{ua} = {base_a} base",
                    )

        # 复合时间："2 hours 30 minutes" → 基准秒数
        ca = self._parse_composite_time(a)
        cb = self._parse_composite_time(b)
        if ca is not None and cb is not None:
            if math.isclose(ca, cb, rel_tol=1e-4):
                return MatchResult(
                    match=True, method="unit_conversion_composite", confidence=0.98
                )

        # 混合：复合时间 vs 简单单位
        if ca is not None and vb is not None and ub is not None:
            cb_base = self._to_base_unit(vb, ub)
            if cb_base is not None and math.isclose(ca, cb_base, rel_tol=1e-4):
                return MatchResult(
                    match=True, method="unit_conversion_mixed", confidence=0.98
                )
        if cb is not None and va is not None and ua is not None:
            ca_base = self._to_base_unit(va, ua)
            if ca_base is not None and math.isclose(ca_base, cb, rel_tol=1e-4):
                return MatchResult(
                    match=True, method="unit_conversion_mixed", confidence=0.98
                )

        return MatchResult(match=False)

    def _parse_with_unit(self, s: str) -> Tuple[Optional[float], Optional[str]]:
        """从字符串中提取数值和单位"""
        s = s.strip().lower()

        # 匹配 "数字 单位"
        m = self.UNIT_PATTERN.match(s)
        if m:
            return float(m[1]), m[2].lower()

        # 匹配 "数字   单位"（多个空格）
        parts = re.split(r"\s+", s)
        if len(parts) == 2:
            try:
                val = float(parts[0])
                unit = parts[1].rstrip(".")
                if unit in self.UNIT_CONVERSIONS:
                    return val, unit
            except ValueError:
                pass

        # 匹配 "$数字" 或 "数字km" 等紧凑格式
        compact = re.match(r"^[\$€£]?\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z°%]+)$", s)
        if compact:
            unit = compact[2].lower()
            if unit in self.UNIT_CONVERSIONS:
                return float(compact[1]), unit

        return None, None

    def _to_base_unit(self, value: float, unit: str) -> Optional[float]:
        """将值转换为基准单位"""
        unit = unit.lower()
        factor = self.UNIT_CONVERSIONS.get(unit)
        if factor is not None:
            return value * factor
        return None

    def _parse_composite_time(self, s: str) -> Optional[float]:
        """解析复合时间表达式（如 "2 hours 30 minutes"）为秒数

        注意：'m' 在 UNIT_CONVERSIONS 中是 "meter"，但复合时间中 'm' 可能是 "minute"。
        这里使用专用的时间单位映射。
        """
        _TIME_FACTORS = {
            "h": 3600,
            "hr": 3600,
            "hrs": 3600,
            "hour": 3600,
            "hours": 3600,
            "m": 60,
            "min": 60,
            "mins": 60,
            "minute": 60,
            "minutes": 60,
            "s": 1,
            "sec": 1,
            "secs": 1,
            "second": 1,
            "seconds": 1,
            "d": 86400,
            "day": 86400,
            "days": 86400,
        }
        total_seconds = 0.0
        pattern = re.compile(
            r"(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m(?!i)|seconds?|secs?|s(?!e)|d|days?)",
            re.IGNORECASE,
        )
        matches = pattern.findall(s)
        if not matches:
            return None
        for val_str, unit in matches:
            val = float(val_str)
            unit_lower = unit.lower().rstrip(".")
            factor = _TIME_FACTORS.get(unit_lower)
            if factor is not None:
                total_seconds += val * factor
            else:
                return None
        return total_seconds

    def _temperature_conversion(
        self, va: float, ua: str, vb: float, ub: str
    ) -> Optional[MatchResult]:
        """温度单位换算"""
        temp_map = {
            "c": "celsius",
            "celsius": "celsius",
            "f": "fahrenheit",
            "fahrenheit": "fahrenheit",
            "k": "kelvin",
            "kelvin": "kelvin",
        }
        ua_norm = temp_map.get(ua.lower())
        ub_norm = temp_map.get(ub.lower())
        if not ua_norm or not ub_norm:
            return None
        if ua_norm == ub_norm:
            if math.isclose(va, vb, rel_tol=1e-4):
                return MatchResult(
                    match=True, method="unit_conversion", confidence=0.98
                )
            return None

        def to_celsius(val, unit):
            if unit == "celsius":
                return val
            elif unit == "fahrenheit":
                return (val - 32) * 5 / 9
            elif unit == "kelvin":
                return val - 273.15

        ca = to_celsius(va, ua_norm)
        cb = to_celsius(vb, ub_norm)
        if math.isclose(ca, cb, rel_tol=1e-4):
            return MatchResult(
                match=True,
                method="unit_conversion",
                confidence=0.98,
                details=f"temperature: {va}{ua} = {ca:.2f}°C, {vb}{ub} = {cb:.2f}°C",
            )
        return None

    # ==================== 策略 4：数学表达式等价 ====================

    def _math_expression_equiv(self, a: str, b: str) -> MatchResult:
        """数学表达式等价（尝试安全 eval 求值）"""
        if self._math_value_match(a, b):
            return MatchResult(match=True, method="math_eval", confidence=0.95)
        return MatchResult(match=False)

    def _safe_eval_math(self, expr: str) -> Optional[float]:
        """安全的数学表达式求值"""
        expr = expr.strip().lower()
        # 替换常见数学常量（使用单词边界避免误替换）
        expr = expr.replace("π", str(math.pi))
        expr = re.sub(r"\bpi\b", str(math.pi), expr)
        expr = re.sub(r"\be\b", str(math.e), expr)

        allowed_names = {
            k: v for k, v in math.__dict__.items() if not k.startswith("_")
        }
        allowed_names.update({"abs": abs, "round": round, "int": int, "float": float})

        try:
            code = compile(expr, "<string>", "eval")
            for name in code.co_names:
                if name not in allowed_names:
                    return None
            result = eval(code, {"__builtins__": {}}, allowed_names)
            return float(result)
        except Exception:
            return None

    def _math_value_match(self, a: str, b: str) -> bool:
        """尝试将两边都解释为数值（直接或通过数学表达式），再比较"""
        # 先尝试直接解析数值
        va = self._parse_number(a) if not self._looks_like_math(a) else None
        vb = self._parse_number(b) if not self._looks_like_math(b) else None

        # 如果有数学表达式，安全求值
        try:
            if va is None:
                va = self._safe_eval_math(a)
            if vb is None:
                vb = self._safe_eval_math(b)
        except Exception:
            pass

        if va is not None and vb is not None:
            return math.isclose(va, vb, rel_tol=1e-4)
        return False

    def _looks_like_math(self, s: str) -> bool:
        """判断是否看起来像数学表达式（包含运算符或函数调用）"""
        ops = {
            "+",
            "-",
            "*",
            "/",
            "**",
            "(",
            ")",
            "pi",
            "sin",
            "cos",
            "tan",
            "sqrt",
            "log",
            "exp",
        }
        return any(op in s.lower() for op in ops)

    # ==================== 策略 5：语义等价 ====================

    def _semantic_equivalence(self, a: str, b: str) -> MatchResult:
        """基于 token 重叠和关键词的语义等价检测"""
        # 归一化后计算 Jaccard 相似度
        a_norm = self._normalize_answer(a)
        b_norm = self._normalize_answer(b)

        set_a = set(a_norm.split())
        set_b = set(b_norm.split())
        if not set_a or not set_b:
            return MatchResult(match=False)

        jaccard = len(set_a & set_b) / len(set_a | set_b)

        # 如果 a 或 b 是另一个的子串，高置信度
        if a_norm in b_norm or b_norm in a_norm:
            return MatchResult(
                match=True, method="semantic_equiv_substring", confidence=0.95
            )

        # 高 Jaccard 相似度
        if jaccard >= self.semantic_threshold:
            return MatchResult(
                match=True,
                method="semantic_equiv_jaccard",
                confidence=jaccard,
                details=f"jaccard={jaccard:.3f}",
            )

        # 数字答案的语义检查："about 42" ≈ "42"
        num_a = self._parse_number(a_norm)
        num_b = self._parse_number(b_norm)
        if num_a is not None and num_b is not None:
            if math.isclose(num_a, num_b, rel_tol=1e-4):
                return MatchResult(
                    match=True,
                    method="semantic_equiv_number",
                    confidence=0.9,
                    details=f"{num_a} ≈ {num_b}",
                )

        # 对于短文本（<=3个词），降低阈值
        if len(set_a) <= 3 and len(set_b) <= 3:
            if jaccard >= 0.5:
                return MatchResult(
                    match=True, method="semantic_equiv_short", confidence=jaccard
                )

        return MatchResult(match=False)

    # ==================== 策略 6：LLM Judge 兜底 ====================

    def _llm_judge(self, a: str, b: str) -> MatchResult:
        """LLM 作为最终仲裁者"""
        if not self.llm:
            return MatchResult(match=False)

        prompt = (
            "You are an evaluator determining if two answers are semantically equivalent. "
            'Respond with ONLY a JSON object: {"equivalent": true/false, "reason": "..."}\n\n'
            f"Answer A: {a}\n"
            f"Answer B: {b}\n\n"
            "Are these answers semantically equivalent (same meaning, different wording)?"
        )

        try:
            response = self.llm.invoke(
                [
                    {
                        "role": "system",
                        "content": "You are a strict but fair answer equivalence judge.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
            )

            result = json.loads(response.strip())
            if result.get("equivalent"):
                return MatchResult(
                    match=True,
                    method="llm_judge",
                    confidence=0.85,
                    details=result.get("reason", ""),
                )
        except Exception:
            pass

        return MatchResult(match=False)

    # ==================== 批量匹配 ====================

    def match_batch(self, pairs: List[Tuple[str, str]]) -> List[MatchResult]:
        """批量匹配"""
        return [self.match(p, g) for p, g in pairs]

    def match_dict(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """对评估结果字典进行智能匹配增强"""
        enhanced = []
        stats = {
            m: 0
            for m in [
                "quasi_exact",
                "numeric_equiv",
                "unit_conversion",
                "math_eval",
                "semantic_equiv",
                "llm_judge",
                "no_match",
            ]
        }

        for r in results:
            pred = r.get("predicted", "")
            expected = r.get("expected", "")
            result = self.match(pred, expected)
            r["smart_match"] = result.match
            r["smart_method"] = result.method
            r["smart_confidence"] = result.confidence
            enhanced.append(r)
            if result.method in stats:
                stats[result.method] += 1
            else:
                stats[result.method] = 1

        return {
            "enhanced_results": enhanced,
            "match_statistics": stats,
            "total_samples": len(results),
            "smart_match_rate": sum(1 for r in enhanced if r["smart_match"])
            / len(enhanced)
            if enhanced
            else 0,
            "improvement": self._compute_improvement(results, enhanced),
        }

    def _compute_improvement(self, original: List[Dict], enhanced: List[Dict]) -> Dict:
        """计算相比原始准精确匹配的改进"""
        orig_correct = sum(1 for r in original if r.get("exact_match", False))
        new_correct = sum(1 for r in enhanced if r.get("smart_match", False))
        return {
            "original_correct": orig_correct,
            "new_correct": new_correct,
            "additional_correct": new_correct - orig_correct,
            "improvement_pct": ((new_correct - orig_correct) / orig_correct * 100)
            if orig_correct > 0
            else float("inf"),
        }
