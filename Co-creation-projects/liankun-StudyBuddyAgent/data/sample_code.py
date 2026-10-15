"""示例代码：供 StudyBuddy 讲解与点评使用"""


def fibonacci(n):
    # 递归实现，存在重复计算问题
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def find_max(nums):
    # 未处理空列表的情况
    max_num = nums[0]
    for num in nums:
        if num > max_num:
            max_num = num
    return max_num


if __name__ == "__main__":
    print(fibonacci(10))
    print(find_max([3, 7, 2, 9, 4]))
