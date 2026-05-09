"""
医疗领域 GAIA 评估数据集

包含 10 个真实世界医疗问题，覆盖 3 个难度级别：
- Level 1（3题）：单步知识检索，直接回答
- Level 2（4题）：1-3步推理，需要简单计算或多信息整合
- Level 3（3题）：多步推理，需要专业知识+计算+临床判断

答案设计故意包含 SMART MATCHER 可捕获的语义等价变体，
用于验证智能匹配算法在医疗领域的适用性。
"""

from typing import List, Dict, Any, Optional


MEDICAL_GAIA_QUESTIONS = [
    # ==================== Level 1: 单步知识检索 ====================
    {
        "task_id": "MED-001",
        "question": (
            "According to CDC guidelines, what is the recommended minimum duration "
            "of isolation for a person with mild COVID-19 symptoms (in days)?"
        ),
        "level": 1,
        "final_answer": "5 days",
        "alternative_answers": ["5", "five days", "five"],
        "domain": "infectious_disease",
        "tools": [],
        "steps": 0,
        "scoring_rubric": {
            "exact": "5 days",
            "partial": "contains 5 or five",
            "weight": 1.0,
        },
    },
    {
        "task_id": "MED-002",
        "question": (
            "What is the medical abbreviation 'NPO' derived from, and what does it "
            "instruct a patient to do?"
        ),
        "level": 1,
        "final_answer": "nil per os (nothing by mouth)",
        "alternative_answers": [
            "nil per os",
            "nothing by mouth",
            "nil per os meaning nothing by mouth",
        ],
        "domain": "medical_terminology",
        "tools": [],
        "steps": 0,
        "scoring_rubric": {
            "exact": "nil per os (nothing by mouth)",
            "partial": "contains nil per os AND nothing by mouth",
            "weight": 1.0,
        },
    },
    {
        "task_id": "MED-003",
        "question": (
            "What is the normal fasting blood glucose range for an adult without "
            "diabetes, in mg/dL?"
        ),
        "level": 1,
        "final_answer": "70 to 100 mg/dL",
        "alternative_answers": [
            "70-100 mg/dL",
            "70-100",
            "70 to 100",
            "70 mg/dL to 100 mg/dL",
        ],
        "domain": "clinical_laboratory",
        "tools": [],
        "steps": 0,
        "scoring_rubric": {
            "exact": "70 to 100 mg/dL",
            "partial": "contains 70 and 100",
            "weight": 1.0,
        },
    },
    # ==================== Level 2: 1-3 步推理 ====================
    {
        "task_id": "MED-004",
        "question": (
            "A patient weighs 154 pounds. The prescribed medication is administered "
            "at 5 mg per kilogram of body weight. What is the correct dosage in mg? "
            "(Round to the nearest whole number.)"
        ),
        "level": 2,
        "final_answer": "350 mg",
        "alternative_answers": ["350", "350mg", "350 milligrams"],
        "domain": "dosing_calculation",
        "tools": ["calculator"],
        "steps": 2,
        "scoring_rubric": {
            "exact": "350 mg",
            "partial": "contains 350",
            "weight": 1.0,
        },
    },
    {
        "task_id": "MED-005",
        "question": (
            "A 65-year-old male patient with atrial fibrillation is prescribed warfarin. "
            "His target INR range is 2.0-3.0. Today's INR result is 4.5. According to "
            "standard anticoagulation management guidelines, should the warfarin dose be "
            "increased, decreased, held, or kept the same? Provide the recommended action "
            "and the approximate time until next INR check."
        ),
        "level": 2,
        "final_answer": "hold warfarin, repeat INR in 24-48 hours",
        "alternative_answers": [
            "hold dose, recheck in 1-2 days",
            "withhold warfarin and recheck INR tomorrow",
            "hold warfarin, recheck in 24 hours",
        ],
        "domain": "anticoagulation",
        "tools": ["medical_knowledge"],
        "steps": 2,
        "scoring_rubric": {
            "exact": "hold warfarin, repeat INR in 24-48 hours",
            "partial": "contains hold AND (24 or 48 or 1-2 or tomorrow)",
            "weight": 1.0,
        },
    },
    {
        "task_id": "MED-006",
        "question": (
            "Calculate the BMI of a person who is 175 cm tall and weighs 82 kg. "
            "Classify the result according to WHO standards. "
            "Formula: BMI = weight(kg) / height(m)^2"
        ),
        "level": 2,
        "final_answer": "26.8 (overweight)",
        "alternative_answers": [
            "26.8 overweight",
            "BMI 26.8, overweight",
            "26.8, overweight",
        ],
        "domain": "clinical_calculation",
        "tools": ["calculator"],
        "steps": 2,
        "scoring_rubric": {
            "exact": "26.8 (overweight)",
            "partial": "contains 26.8 AND (overweight or pre-obese)",
            "weight": 1.0,
        },
    },
    {
        "task_id": "MED-007",
        "question": (
            "A 500 mL IV bag of normal saline needs to be infused over 4 hours. "
            "The IV set has a drop factor of 15 drops/mL. What is the required "
            "flow rate in drops per minute? (Round to the nearest whole number.)"
        ),
        "level": 2,
        "final_answer": "31 drops per minute",
        "alternative_answers": [
            "31",
            "31 drops/min",
            "31 gtts/min",
            "31 drops/minute",
        ],
        "domain": "iv_infusion",
        "tools": ["calculator"],
        "steps": 3,
        "scoring_rubric": {
            "exact": "31 drops per minute",
            "partial": "contains 31",
            "weight": 1.0,
        },
    },
    # ==================== Level 3: 多步推理 ====================
    {
        "task_id": "MED-008",
        "question": (
            "A 70 kg patient is prescribed dopamine at 5 mcg/kg/min. The pharmacy "
            "supplies dopamine 400 mg in 250 mL of D5W. Calculate the infusion rate "
            "in mL/hr. Then determine how many hours one full bag will last at this rate."
        ),
        "level": 3,
        "final_answer": "13.1 mL/hr, 19 hours",
        "alternative_answers": [
            "13.1 mL/hr, 19.1 hours",
            "13.1 mL per hour, 19 hours",
            "13.1 mL/hr, 19.1",
        ],
        "domain": "critical_care",
        "tools": ["calculator", "unit_conversion"],
        "steps": 4,
        "scoring_rubric": {
            "exact": "13.1 mL/hr, 19 hours",
            "partial": "contains 13.1 AND (19 or 19.1)",
            "weight": 1.0,
        },
    },
    {
        "task_id": "MED-009",
        "question": (
            "A 50-year-old female presents with acute onset of severe right lower quadrant "
            "abdominal pain, nausea, and low-grade fever (38.0 C). WBC count is elevated. "
            "Based on the Alvarado score system (MANTRELS criteria), calculate the score "
            "and state the recommended clinical action. "
            "MANTRELS criteria: Migration of pain (1), Anorexia (1), Nausea/Vomiting (1), "
            "Tenderness in RLQ (2), Rebound pain (1), Elevated temperature (1), "
            "Leukocytosis (2), Shift of WBC to left (1). Assume she has all symptoms "
            "except migration of pain."
        ),
        "level": 3,
        "final_answer": "Alvarado score of 8, recommend surgical consultation",
        "alternative_answers": [
            "score 8, surgery consult recommended",
            "8 points, surgical evaluation needed",
            "Alvarado 8, surgical consult",
        ],
        "domain": "clinical_scoring",
        "tools": ["calculator", "medical_knowledge"],
        "steps": 3,
        "scoring_rubric": {
            "exact": "Alvarado score of 8, recommend surgical consultation",
            "partial": "contains 8 AND (surgery or surgical or consult)",
            "weight": 1.0,
        },
    },
    {
        "task_id": "MED-010",
        "question": (
            "A 6-month-old infant with bronchiolitis has the following arterial blood "
            "gas results: pH 7.25, PaCO2 60 mmHg, PaO2 55 mmHg, HCO3 26 mEq/L. "
            "Interpret this ABG (acid-base status and oxygenation status). What is the "
            "primary acid-base disorder and what is the expected compensatory response? "
            "Is the compensation adequate?"
        ),
        "level": 3,
        "final_answer": "acute respiratory acidosis with hypoxemia, no metabolic compensation expected, adequate",
        "alternative_answers": [
            "acute respiratory acidosis, hypoxemia, compensation not yet expected",
            "respiratory acidosis, hypoxemia, no compensation",
            "acute respiratory acidosis, hypoxemic respiratory failure, no metabolic compensation",
        ],
        "domain": "abg_interpretation",
        "tools": ["medical_knowledge"],
        "steps": 4,
        "scoring_rubric": {
            "exact": "acute respiratory acidosis with hypoxemia, no metabolic compensation expected, adequate",
            "partial": "contains respiratory acidosis AND hypoxemia",
            "weight": 1.0,
        },
    },
]


class MedicalGAIADataset:
    """医疗领域 GAIA 数据集

    包含 10 个覆盖 3 个难度级别的真实世界医疗问题：
    - Level 1 (MED-001~003): 单步知识检索
    - Level 2 (MED-004~007): 1-3 步推理 + 计算
    - Level 3 (MED-008~010): 多步推理 + 临床决策

    设计特点：
    1. 部分标准答案故意使用语义等价变体（如 "5 days" vs "five days"），
       用于验证 SmartAnswerMatcher 的数值/语义匹配能力
    2. 需要单位换算的题目（MED-004: lb→kg, MED-008: mcg↔mg）测试单位
       换算匹配
    3. 临床评分（MED-009 Alvarado）测试多步推理+结构化答案匹配
    """

    def __init__(self, level: Optional[int] = None):
        self.level = level
        self.data: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        self.data = []
        for item in MEDICAL_GAIA_QUESTIONS:
            standardized = self._standardize_item(item)
            self.data.append(standardized)
        if self.level is not None:
            self.data = [d for d in self.data if d.get("level") == self.level]

    def _standardize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "task_id": item.get("task_id", ""),
            "question": item.get("question", ""),
            "level": item.get("level", 1),
            "final_answer": item.get("final_answer", ""),
            "alternative_answers": item.get("alternative_answers", []),
            "domain": item.get("domain", ""),
            "file_name": item.get("file_name", ""),
            "tools": item.get("tools", []),
            "steps": item.get("steps", 0),
            "scoring_rubric": item.get("scoring_rubric", {}),
        }

    def load(self) -> List[Dict[str, Any]]:
        print("✅ 医疗GAIA数据集加载完成")
        print("   领域: 医疗临床")
        print(f"   级别: {self.level or '全部 (1-3)'}")
        print(f"   样本数: {len(self.data)}")
        print(
            f"   级别分布: L1={sum(1 for d in self.data if d['level'] == 1)}, "
            f"L2={sum(1 for d in self.data if d['level'] == 2)}, "
            f"L3={sum(1 for d in self.data if d['level'] == 3)}"
        )
        return self.data

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "total_samples": len(self.data),
            "level_distribution": {
                1: sum(1 for d in self.data if d.get("level") == 1),
                2: sum(1 for d in self.data if d.get("level") == 2),
                3: sum(1 for d in self.data if d.get("level") == 3),
            },
            "domains": list(set(d.get("domain", "") for d in self.data)),
            "domain_count": {
                domain: sum(1 for d in self.data if d.get("domain") == domain)
                for domain in set(d.get("domain", "") for d in self.data)
            },
        }

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)
