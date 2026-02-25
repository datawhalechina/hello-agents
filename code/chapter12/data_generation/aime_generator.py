"""
AIME数学题目生成器

使用HelloAgents框架生成AIME风格的数学题目
"""

import json
import os
import time
import random
from typing import List, Dict, Any, Optional
from datetime import datetime
from tqdm import tqdm
from hello_agents import SimpleAgent
from hello_agents import HelloAgentsLLM
from datasets import load_dataset


class AIMEGenerator:
    """AIME题目生成器"""
    
    # AIME题目生成提示词（英文）
    GENERATION_PROMPT = """You are a professional mathematics competition problem designer, skilled in creating AIME (American Invitational Mathematics Examination) style problems.

AIME Problem Characteristics:
1. Answer: An integer between 0 and 999
2. Topics: Algebra, Geometry, Number Theory, Combinatorics, Probability, etc.
3. Style: Requires multi-step reasoning, but no advanced theory
4. Difficulty: Medium to hard (similar to AIME problems 6-9)

Please generate an AIME-style mathematics problem, including:
1. Problem statement (clear and complete)
2. Answer (an integer between 0 and 999)
3. Detailed solution (including all reasoning steps)
4. Topic classification (Algebra/Geometry/Number Theory/Combinatorics/Probability)

Please output in the following JSON format, avoid using special escape characters in JSON:
```json
{
    "problem": "Problem statement in English",
    "answer": 123,
    "solution": "Detailed solution steps in English",
    "topic": "Algebra"
}
```
"""
    
    def __init__(
        self,
        llm: HelloAgentsLLM = None,
        delay_seconds: float = 1.0,
        use_reference_examples: bool = True,
        reference_dataset: str = "TianHongZXY/aime-1983-2025"
    ):
        """
        初始化生成器

        Args:
            llm: LLM实例（可选）
            delay_seconds: 每次生成之间的延迟（秒），避免API速率限制
            use_reference_examples: 是否使用真题作为参考样例
            reference_dataset: 参考数据集名称，默认使用TianHongZXY/aime-1983-2025（900+道题）
        """
        # 如果没有提供llm，创建默认的HelloAgentsLLM
        if llm is None:
            self.llm = HelloAgentsLLM()
        else:
            self.llm = llm

        self.agent = SimpleAgent(
            name="AIME Generator",
            llm=self.llm,
            system_prompt="你是一位专业的数学竞赛题目设计专家。"
        )
        self.delay_seconds = delay_seconds
        self.use_reference_examples = use_reference_examples
        self.reference_examples = []

        # 加载参考样例
        if use_reference_examples:
            try:
                print(f"📚 加载AIME真题数据集: {reference_dataset}")
                # 尝试不同的split
                try:
                    dataset = load_dataset(reference_dataset, split="train")
                except Exception:
                    dataset = load_dataset(reference_dataset, split="test")

                # 加载所有题目作为参考
                self.reference_examples = list(dataset)
                print(f"   ✓ 已加载 {len(self.reference_examples)} 道参考题目")

                # 统计年份分布（如果有year字段）
                year_counts = {}
                for item in self.reference_examples:
                    year = item.get('year')
                    if year:
                        year_counts[year] = year_counts.get(year, 0) + 1

                if year_counts:
                    year_range = f"{min(year_counts.keys())}-{max(year_counts.keys())}"
                    print(f"   ℹ️  年份范围: {year_range}")

            except Exception as e:
                print(f"   ⚠️ 加载参考样例失败: {e}")
                print(f"   ℹ️  将使用默认提示词生成")
                self.use_reference_examples = False
    
    def generate_single(self, max_retries: int = 3) -> Dict[str, Any]:
        """
        生成单个题目

        Args:
            max_retries: 最大重试次数

        Returns:
            题目数据
        """
        # 构建提示词
        prompt = self._build_prompt()

        for attempt in range(max_retries):
            try:
                response = self.agent.run(prompt)
                return self._parse_response(response)
            except Exception as e:
                if attempt < max_retries - 1:
                    tqdm.write(f"⚠️ 生成失败（尝试 {attempt + 1}/{max_retries}），{self.delay_seconds}秒后重试...")
                    time.sleep(self.delay_seconds)
                else:
                    tqdm.write(f"❌ 生成失败，已达最大重试次数: {e}")
                    return self._get_default_problem()

    def _build_prompt(self) -> str:
        """构建生成提示词"""
        if not self.use_reference_examples or not self.reference_examples:
            return self.GENERATION_PROMPT

        # 随机选择一个参考样例
        example = random.choice(self.reference_examples)
        example_problem = example.get('problem', 'Example problem')
        example_answer = example.get('answer', 0)

        # 构建带参考样例的提示词（英文）
        prompt = f"""You are a professional mathematics competition problem designer, skilled in creating AIME (American Invitational Mathematics Examination) style problems.

【Reference Example】(For style reference only, please generate a completely different problem)
Problem: {example_problem}
Answer: {example_answer}

AIME Problem Characteristics:
1. Answer: An integer between 0 and 999
2. Topics: Algebra, Geometry, Number Theory, Combinatorics, Probability, etc.
3. Style: Requires multi-step reasoning, but no advanced theory
4. Difficulty: Medium to hard (similar to AIME problems 6-9)

Please generate a **completely different** AIME-style mathematics problem, including:
1. Problem statement (clear and complete, different from the reference)
2. Answer (an integer between 0 and 999, different from the reference)
3. Detailed solution (including all reasoning steps)
4. Topic classification (Algebra/Geometry/Number Theory/Combinatorics/Probability)

Please output in the following JSON format, avoid using special escape characters in JSON:
```json
{{
    "problem": "Problem statement in English",
    "answer": 123,
    "solution": "Detailed solution steps in English",
    "topic": "Algebra"
}}
```

Important Notes:
- **Must generate a completely different problem from the reference**
- You can reference the style, but do not copy the content
- Ensure the problem is creative and original
"""
        return prompt

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """解析LLM响应（支持LaTeX数学公式）"""
        import re

        # 提取JSON部分
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            json_str = response.strip()

        # 使用json.loads的strict=False来处理转义字符
        # 但这还不够，我们需要更智能的处理
        try:
            problem_data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # 如果解析失败，尝试修复常见的LaTeX转义问题
            # 方法：先将字符串中的单个反斜杠替换为双反斜杠（但保留已经转义的）
            # 这样LaTeX的 \frac 会变成 \\frac，在JSON中是合法的

            # 使用正则表达式：找到所有未转义的反斜杠（不是\\的\）
            # 并将其替换为\\
            fixed_json_str = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', json_str)

            try:
                problem_data = json.loads(fixed_json_str)
            except json.JSONDecodeError:
                # 如果还是失败，打印错误信息并抛出
                print(f"❌ JSON解析失败:")
                print(f"原始响应: {response[:500]}...")
                print(f"提取的JSON: {json_str[:500]}...")
                raise

        # 验证必需字段
        if "problem" not in problem_data or "answer" not in problem_data:
            raise ValueError("缺少必需字段: problem 或 answer")

        # 验证答案范围
        answer = int(problem_data.get("answer", 0))
        if not (0 <= answer <= 999):
            print(f"⚠️ 答案超出范围: {answer}，调整为0-999范围内")
            answer = max(0, min(999, answer))
            problem_data["answer"] = answer

        # 确保有默认值
        problem_data.setdefault("solution", "No solution provided")
        problem_data.setdefault("topic", "Uncategorized")

        return problem_data

    def _get_default_problem(self) -> Dict[str, Any]:
        """获取默认题目（生成失败时使用）"""
        return {
            "problem": "生成失败，请重新生成",
            "answer": 0,
            "solution": "N/A",
            "topic": "未知"
        }
    
    def generate_batch(
        self,
        num_problems: int = 30,
        checkpoint_path: str = None
    ) -> List[Dict[str, Any]]:
        """
        批量生成题目

        Args:
            num_problems: 生成题目数量
            checkpoint_path: 检查点文件路径（用于保存进度）

        Returns:
            题目列表
        """
        print(f"\n🎯 开始生成AIME题目")
        print(f"   目标数量: {num_problems}")
        print(f"   生成模型: {self.llm.model}")
        print(f"   延迟设置: {self.delay_seconds}秒/题")

        # 尝试从检查点恢复
        problems = []
        start_index = 0

        if checkpoint_path and os.path.exists(checkpoint_path):
            print(f"\n📂 发现检查点文件，尝试恢复...")
            try:
                with open(checkpoint_path, 'r', encoding='utf-8') as f:
                    problems = json.load(f)
                start_index = len(problems)
                print(f"   ✓ 已恢复 {start_index} 个题目，从第 {start_index + 1} 个继续")
            except Exception as e:
                print(f"   ⚠️ 恢复失败: {e}，从头开始")
                problems = []
                start_index = 0

        # 生成题目（使用tqdm显示进度）
        with tqdm(total=num_problems, initial=start_index, desc="生成AIME题目", unit="题") as pbar:
            last_call_time = 0  # 上次API调用的时间

            for i in range(start_index, num_problems):
                # 计算距离上次调用的时间
                if last_call_time > 0:
                    elapsed = time.time() - last_call_time
                    # 如果距离上次调用不足delay_seconds，则等待
                    if elapsed < self.delay_seconds:
                        wait_time = self.delay_seconds - elapsed
                        tqdm.write(f"⏳ 等待 {wait_time:.1f} 秒以避免速率限制...")
                        time.sleep(wait_time)

                # 记录开始时间
                start_time = time.time()

                # 生成题目
                problem = self.generate_single()
                problem["id"] = f"gen_aime_{i + 1}"
                problem["generated_at"] = datetime.now().isoformat()

                # 记录结束时间
                last_call_time = time.time()
                generation_time = last_call_time - start_time

                problems.append(problem)

                # 更新进度条描述
                pbar.set_postfix({
                    "主题": problem.get('topic', 'N/A'),
                    "答案": problem.get('answer', 'N/A'),
                    "耗时": f"{generation_time:.1f}s"
                })
                pbar.update(1)

                # 保存检查点
                if checkpoint_path:
                    try:
                        with open(checkpoint_path, 'w', encoding='utf-8') as f:
                            json.dump(problems, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        tqdm.write(f"⚠️ 保存检查点失败: {e}")

        print(f"\n✅ 生成完成！共 {len(problems)} 个题目")
        return problems
    
    def save_problems(
        self,
        problems: List[Dict[str, Any]],
        output_path: str
    ):
        """保存题目到文件"""
        # 确保目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(problems, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 题目已保存: {output_path}")
    
    def generate_and_save(
        self,
        num_problems: int = 30,
        output_dir: str = "data_generation/generated_data"
    ) -> str:
        """生成并保存题目"""
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 清理旧的检查点文件
        for file in os.listdir(output_dir):
            if file.startswith("checkpoint_") and file.endswith(".json"):
                old_checkpoint = os.path.join(output_dir, file)
                try:
                    os.remove(old_checkpoint)
                    print(f"🗑️  已删除旧检查点文件: {file}")
                except Exception as e:
                    print(f"⚠️ 删除旧检查点失败: {e}")

        # 设置检查点路径
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_path = os.path.join(output_dir, f"checkpoint_{timestamp}.json")

        # 生成题目（带检查点）
        problems = self.generate_batch(num_problems, checkpoint_path=checkpoint_path)

        # 保存题目
        output_path = os.path.join(output_dir, f"aime_generated_{timestamp}.json")
        self.save_problems(problems, output_path)

        # 生成统计报告
        self._generate_statistics_report(problems, output_dir, timestamp)

        # 删除检查点文件
        if os.path.exists(checkpoint_path):
            try:
                os.remove(checkpoint_path)
                print(f"\n🗑️  已删除检查点文件")
            except Exception as e:
                print(f"\n⚠️ 删除检查点文件失败: {e}")

        return output_path
    
    def _generate_statistics_report(
        self,
        problems: List[Dict[str, Any]],
        output_dir: str,
        timestamp: str
    ):
        """生成统计报告"""
        # 统计主题分布
        topics = {}
        answers = []

        for problem in problems:
            topic = problem.get("topic", "未知")
            topics[topic] = topics.get(topic, 0) + 1

            if "answer" in problem:
                answers.append(problem["answer"])
        
        # 生成报告
        report = f"""# AIME题目生成统计报告

## 基本信息

- **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **题目数量**: {len(problems)}

## 主题分布

| 主题 | 数量 | 占比 |
|------|------|------|
"""
        
        for topic, count in sorted(topics.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(problems) * 100
            report += f"| {topic} | {count} | {percentage:.1f}% |\n"

        if answers:
            report += f"""
## 答案分析

- **平均答案**: {sum(answers) / len(answers):.2f}
- **最小答案**: {min(answers)}
- **最大答案**: {max(answers)}
- **答案范围**: {min(answers)}-{max(answers)}
"""
        
        report += f"""
## 题目列表

| ID | 主题 | 答案 |
|-----|------|------|
"""

        for problem in problems[:10]:  # 只显示前10个
            report += f"| {problem.get('id', 'N/A')} | {problem.get('topic', 'N/A')} | {problem.get('answer', 'N/A')} |\n"
        
        if len(problems) > 10:
            report += f"\n*（仅显示前10个题目，完整列表请查看JSON文件）*\n"
        
        report += f"""
---

*报告生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        
        # 保存报告
        report_path = os.path.join(output_dir, f"generation_report_{timestamp}.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📊 统计报告已保存: {report_path}")


if __name__ == "__main__":
    # 创建生成器
    generator = AIMEGenerator()
    
    # 生成30个题目
    output_path = generator.generate_and_save(num_problems=30)
    
    print(f"\n✅ 完成！生成的题目保存在: {output_path}")

