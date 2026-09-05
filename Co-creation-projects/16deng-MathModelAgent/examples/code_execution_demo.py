"""
代码执行功能演示

展示如何使用CodeExecutor执行生成的代码
"""

import sys
sys.path.insert(0, '..')

from src.code_executor import CodeExecutor, SafeCodeExecutor


def demo_basic_execution():
    """演示基本代码执行"""
    print("=" * 60)
    print("演示1: 基本代码执行")
    print("=" * 60)
    
    executor = CodeExecutor()
    
    code = """
import numpy as np

# 创建数组
arr = np.array([1, 2, 3, 4, 5])
print(f"数组: {arr}")
print(f"均值: {arr.mean():.2f}")
print(f"标准差: {arr.std():.2f}")
"""
    
    result = executor.execute(code)
    
    print(f"执行成功: {result['success']}")
    print(f"输出:\n{result['stdout']}")
    if result['stderr']:
        print(f"错误:\n{result['stderr']}")


def demo_matplotlib():
    """演示Matplotlib绘图"""
    print("\n" + "=" * 60)
    print("演示2: Matplotlib绘图")
    print("=" * 60)
    
    executor = CodeExecutor()
    
    code = """
import numpy as np
import matplotlib.pyplot as plt

# 创建数据
x = np.linspace(0, 2 * np.pi, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# 绘制图形
plt.figure(figsize=(10, 6))
plt.plot(x, y1, label='sin(x)', linewidth=2)
plt.plot(x, y2, label='cos(x)', linewidth=2)
plt.title('Trigonometric Functions')
plt.xlabel('x')
plt.ylabel('y')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()

print("图表已生成！")
"""
    
    result = executor.execute(code)
    
    print(f"执行成功: {result['success']}")
    print(f"输出:\n{result['stdout']}")
    if result['figure']:
        print(f"图表: 已生成 (base64长度: {len(result['figure'])})")


def demo_data_analysis():
    """演示数据分析"""
    print("\n" + "=" * 60)
    print("演示3: 数据分析")
    print("=" * 60)
    
    executor = CodeExecutor()
    
    code = """
import pandas as pd
import numpy as np

# 创建示例数据
np.random.seed(42)
data = {
    '姓名': ['张三', '李四', '王五', '赵六', '钱七'],
    '年龄': np.random.randint(20, 40, 5),
    '成绩': np.random.uniform(60, 100, 5).round(2)
}
df = pd.DataFrame(data)

print("数据表:")
print(df)
print()
print("统计信息:")
print(df.describe())
"""
    
    result = executor.execute(code)
    
    print(f"执行成功: {result['success']}")
    print(f"输出:\n{result['stdout']}")


def demo_error_handling():
    """演示错误处理"""
    print("\n" + "=" * 60)
    print("演示4: 错误处理")
    print("=" * 60)
    
    executor = CodeExecutor()
    
    # 故意包含错误的代码
    code = """
import numpy as np

# 这行代码会出错（除以零）
arr = np.array([1, 2, 0, 4, 5])
result = 10 / arr
print(result)
"""
    
    result = executor.execute(code)
    
    print(f"执行成功: {result['success']}")
    print(f"输出:\n{result['stdout']}")
    if result['stderr']:
        print(f"错误信息:\n{result['stderr']}")


def demo_safe_executor():
    """演示安全代码执行器"""
    print("\n" + "=" * 60)
    print("演示5: 安全代码执行器")
    print("=" * 60)
    
    executor = SafeCodeExecutor()
    
    # 安全代码
    safe_code = """
print("这是安全的代码")
x = 1 + 2
print(f"计算结果: {x}")
"""
    
    result = executor.execute(safe_code)
    print(f"安全代码执行结果: {result['success']}")
    
    # 危险代码
    dangerous_code = """
import os
os.system("echo 这是危险的代码")
"""
    
    result = executor.execute(dangerous_code)
    print(f"危险代码执行结果: {result['success']}")
    if result.get('safety_warning'):
        print(f"安全警告: {result['safety_warning']}")


def demo_with_fix():
    """演示代码修复功能"""
    print("\n" + "=" * 60)
    print("演示6: 代码修复功能")
    print("=" * 60)
    
    executor = CodeExecutor()
    
    # 包含错误的代码
    code = """
import numpy as np

# 计算平均值（变量名错误）
arr = np.array([1, 2, 3, 4, 5])
average = np.mean(arr)
print(f"平均值: {average}")
"""
    
    def fix_callback(code, error):
        """简单的修复回调"""
        if "name 'np' is defined" in error:
            return code  # 无法修复
        return code
    
    result = executor.execute_with_fix(code, max_retries=2, fix_callback=fix_callback)
    
    print(f"执行成功: {result['success']}")
    print(f"尝试次数: {result.get('attempts', 1)}")
    print(f"输出:\n{result['stdout']}")


if __name__ == "__main__":
    print("MathModelAgent 代码执行功能演示")
    print("=" * 60)
    
    demo_basic_execution()
    demo_matplotlib()
    demo_data_analysis()
    demo_error_handling()
    demo_safe_executor()
    demo_with_fix()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
