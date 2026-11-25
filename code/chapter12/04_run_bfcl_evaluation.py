"""
第十二章：BFCL一键评估脚本

本脚本提供完整的BFCL评估流程：
1. 自动检查和准备BFCL数据
2. 运行HelloAgents评估
3. 导出BFCL格式结果
4. 调用BFCL官方评估工具
5. 展示评估结果

使用方法（从本教程的 code 目录运行）：
    python chapter12/04_run_bfcl_evaluation.py

可选参数：
    --category: 评估类别（默认：simple_python）
    --samples: 样本数量（默认：5，设为0表示全部）
    --model-name: 模型名称（默认：HelloAgents）
"""

import sys
import subprocess
from pathlib import Path
import argparse
import json

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hello_agents import SimpleAgent, HelloAgentsLLM
from hello_agents.evaluation import BFCLDataset, BFCLEvaluator


# 函数调用系统提示词
FUNCTION_CALLING_SYSTEM_PROMPT = """你是一个专业的函数调用助手。

你的任务是：根据用户的问题和提供的函数定义，生成正确的函数调用。

输出格式要求：
1. 必须是纯JSON格式，不要添加任何解释文字
2. 使用JSON数组格式：[{"name": "函数名", "arguments": {"参数名": "参数值"}}]
3. 如果需要调用多个函数，在数组中添加多个对象
4. 如果不需要调用函数，返回空数组：[]

示例：
用户问题：查询北京的天气
可用函数：get_weather(city: str)
正确输出：[{"name": "get_weather", "arguments": {"city": "北京"}}]

注意：
- 只输出JSON，不要添加"好的"、"我来帮你"等额外文字
- 参数值必须与函数定义的类型匹配
- 参数名必须与函数定义完全一致
"""


def check_bfcl_data(bfcl_data_dir: Path) -> bool:
    """检查BFCL数据是否存在"""
    if not bfcl_data_dir.exists():
        print(f"\n❌ BFCL数据目录不存在: {bfcl_data_dir}")
        print("\n请在本教程的仓库根目录运行：")
        print("   git clone --depth 1 https://github.com/ShishirPatil/gorilla.git code/temp_gorilla")
        return False
    return True


def run_evaluation(category: str, max_samples: int, model_name: str) -> dict:
    """运行HelloAgents评估"""
    print("\n" + "="*60)
    print("步骤1: 运行HelloAgents评估")
    print("="*60)
    
    # BFCL数据目录
    bfcl_data_dir = project_root / "temp_gorilla" / "berkeley-function-call-leaderboard" / "bfcl_eval" / "data"
    
    # 检查数据
    if not check_bfcl_data(bfcl_data_dir):
        return None
    
    # 加载数据集
    print(f"\n📚 加载BFCL数据集...")
    dataset = BFCLDataset(bfcl_data_dir=str(bfcl_data_dir), category=category)

    # 创建智能体
    print(f"\n🤖 创建智能体...")
    llm = HelloAgentsLLM()
    agent = SimpleAgent(
        name=model_name,
        llm=llm,
        system_prompt=FUNCTION_CALLING_SYSTEM_PROMPT,
        enable_tool_calling=False
    )
    print(f"   智能体: {model_name}")
    print(f"   LLM: {llm.provider}")

    # 创建评估器
    evaluator = BFCLEvaluator(dataset=dataset, category=category)

    # 运行评估（传递max_samples参数）
    print(f"\n🔄 开始评估...")
    if max_samples > 0:
        print(f"   样本数量: {max_samples}")
        results = evaluator.evaluate(agent, max_samples=max_samples)
    else:
        print(f"   样本数量: 全部")
        results = evaluator.evaluate(agent, max_samples=None)
    
    # 显示结果
    print(f"\n📊 评估结果:")
    print(f"   准确率: {results['overall_accuracy']:.2%}")
    print(f"   正确数: {results['correct_samples']}/{results['total_samples']}")
    
    return results


def export_bfcl_format(results: dict, category: str, model_name: str) -> Path:
    """导出BFCL格式结果"""
    print("\n" + "="*60)
    print("步骤2: 导出BFCL格式结果")
    print("="*60)
    
    # 输出目录
    output_dir = project_root / "evaluation_results" / "bfcl_official"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 输出文件
    output_file = output_dir / f"BFCL_v4_{category}_result.json"
    
    # 创建评估器（用于导出）
    bfcl_data_dir = project_root / "temp_gorilla" / "berkeley-function-call-leaderboard" / "bfcl_eval" / "data"
    dataset = BFCLDataset(bfcl_data_dir=str(bfcl_data_dir), category=category)
    evaluator = BFCLEvaluator(dataset=dataset, category=category)
    
    # 导出
    evaluator.export_to_bfcl_format(results, output_file)
    
    return output_file


def copy_to_bfcl_result_dir(source_file: Path, model_name: str, category: str) -> Path:
    """复制结果文件到BFCL结果目录"""
    print("\n" + "="*60)
    print("步骤3: 准备BFCL官方评估")
    print("="*60)
    
    # BFCL结果目录
    # 注意：BFCL会将模型名中的"/"替换为"_"
    safe_model_name = model_name.replace("/", "_")
    result_dir = project_root / "result" / safe_model_name
    result_dir.mkdir(parents=True, exist_ok=True)
    
    # 目标文件
    target_file = result_dir / f"BFCL_v4_{category}_result.json"
    
    # 复制文件
    import shutil
    shutil.copy(source_file, target_file)
    
    print(f"\n✅ 结果文件已复制到:")
    print(f"   {target_file}")
    
    return target_file


def run_bfcl_official_eval(model_name: str, category: str) -> bool:
    """运行BFCL官方评估"""
    print("\n" + "="*60)
    print("步骤4: 运行BFCL官方评估")
    print("="*60)
    
    try:
        # 设置环境变量
        import os
        os.environ['PYTHONUTF8'] = '1'
        
        # 运行BFCL评估
        cmd = [
            "bfcl", "evaluate",
            "--model", model_name,
            "--test-category", category,
            "--partial-eval"
        ]
        
        print(f"\n🔄 运行命令: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=str(project_root),
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        # 显示输出
        if result.stdout:
            print(result.stdout)
        
        if result.returncode != 0:
            print(f"\n❌ BFCL评估失败:")
            if result.stderr:
                print(result.stderr)
            return False
        
        return True
        
    except FileNotFoundError:
        print("\n❌ 未找到bfcl命令")
        print("   请先安装: pip install bfcl-eval")
        return False
    except Exception as e:
        print(f"\n❌ 运行BFCL评估时出错: {e}")
        return False


def show_results(model_name: str, category: str):
    """展示评估结果"""
    print("\n" + "="*60)
    print("步骤5: 展示评估结果")
    print("="*60)
    
    # CSV文件
    csv_file = project_root / "score" / "data_non_live.csv"
    
    if csv_file.exists():
        print(f"\n📊 评估结果汇总:")
        with open(csv_file, 'r', encoding='utf-8') as f:
            content = f.read()
            print(content)
    else:
        print(f"\n⚠️ 未找到评估结果文件: {csv_file}")
    
    # 详细评分文件
    safe_model_name = model_name.replace("/", "_")
    score_file = project_root / "score" / safe_model_name / "non_live" / f"BFCL_v4_{category}_score.json"
    
    if score_file.exists():
        print(f"\n📝 详细评分文件:")
        print(f"   {score_file}")
        
        # 读取并显示准确率
        with open(score_file, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            summary = json.loads(first_line)
            print(f"\n🎯 最终结果:")
            print(f"   准确率: {summary['accuracy']:.2%}")
            print(f"   正确数: {summary['correct_count']}/{summary['total_count']}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="BFCL一键评估脚本")
    parser.add_argument("--category", default="simple_python", help="评估类别")
    parser.add_argument("--samples", type=int, default=5, help="样本数量（0表示全部）")
    parser.add_argument("--model-name", default="Qwen/Qwen3-8B",
                       help="模型名称（必须是BFCL支持的模型，运行'bfcl models'查看）")
    
    args = parser.parse_args()
    
    print("="*60)
    print("BFCL一键评估脚本")
    print("="*60)
    print(f"\n配置:")
    print(f"   评估类别: {args.category}")
    print(f"   样本数量: {args.samples if args.samples > 0 else '全部'}")
    print(f"   模型名称: {args.model_name}")
    
    # 步骤1: 运行评估
    results = run_evaluation(args.category, args.samples, args.model_name)
    if not results:
        return
    
    # 步骤2: 导出BFCL格式
    output_file = export_bfcl_format(results, args.category, args.model_name)
    
    # 步骤3: 复制到BFCL结果目录
    copy_to_bfcl_result_dir(output_file, args.model_name, args.category)
    
    # 步骤4: 运行BFCL官方评估
    if not run_bfcl_official_eval(args.model_name, args.category):
        print("\n⚠️ BFCL官方评估失败，但HelloAgents评估已完成")
        return
    
    # 步骤5: 展示结果
    show_results(args.model_name, args.category)
    
    print("\n" + "="*60)
    print("✅ 评估完成！")
    print("="*60)


if __name__ == "__main__":
    main()

