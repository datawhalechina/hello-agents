def twoSum(nums, target):
    # 我写的暴力解法，导师看看对不对
    for i in range(len(nums)):
        for j in range(len(nums)):
            # 防止自己加自己
            if i != j and nums[i] + nums[j] == target:
                return [i, j]
    return []