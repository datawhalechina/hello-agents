# 示例知识文档

## 线性规划

### 定义
线性规划（Linear Programming，LP）是数学规划的一个重要分支，用于在有限资源约束下求解最优解。

### 适用场景
- 资源分配问题
- 生产计划问题
- 运输问题
- 配送路线优化

### 数学模型
$$
\begin{aligned}
\min \quad & \sum_{i=1}^{n} c_i x_i \\
\text{s.t.} \quad & \sum_{j=1}^{n} a_{ij} x_j \leq b_i, \quad i=1,2,\ldots,m \\
& x_j \geq 0, \quad j=1,2,\ldots,n
\end{aligned}
$$

### Python实现
```python
from scipy.optimize import linprog

# 目标函数系数
c = [1, 2, 3]

# 不等式约束矩阵
A = [[-1, -1, 0],
     [0, -1, -1]]

# 不等式约束向量
b = [-1, -2]

# 变量范围
x_bounds = [(0, None), (0, None), (0, None)]

# 求解
result = linprog(c, A_ub=A, b_ub=b, bounds=x_bounds, method='highs')

print(f"最优解: {result.x}")
print(f"最优值: {result.fun}")
```

## 旅行商问题（TSP）

### 定义
旅行商问题（Traveling Salesman Problem，TSP）是组合优化中的经典问题：给定一组城市和每对城市之间的距离，求访问每个城市恰好一次并返回起点的最短路径。

### 适用场景
- 物流配送路线规划
- 电路板钻孔顺序优化
- 网络路由优化

### 数学模型
$$
\begin{aligned}
\min \quad & \sum_{i=1}^{n} \sum_{j=1}^{n} d_{ij} x_{ij} \\
\text{s.t.} \quad & \sum_{j=1, j \neq i}^{n} x_{ij} = 1, \quad i=1,2,\ldots,n \\
& \sum_{i=1, i \neq j}^{n} x_{ij} = 1, \quad j=1,2,\ldots,n \\
& x_{ij} \in \{0, 1\}, \quad i,j=1,2,\ldots,n
\end{aligned}
$$

### Python实现
```python
import numpy as np
from scipy.spatial.distance import pdist, squareform

# 城市坐标
cities = np.array([
    [0, 0],
    [1, 5],
    [5, 2],
    [6, 6],
    [8, 3]
])

# 计算距离矩阵
distances = squareform(pdist(cities))

# 使用最近邻算法求解
def nearest_neighbor(distances, start=0):
    n = len(distances)
    visited = [False] * n
    path = [start]
    visited[start] = True
    
    for _ in range(n - 1):
        current = path[-1]
        nearest = None
        nearest_dist = float('inf')
        
        for j in range(n):
            if not visited[j] and distances[current][j] < nearest_dist:
                nearest = j
                nearest_dist = distances[current][j]
        
        path.append(nearest)
        visited[nearest] = True
    
    return path

path = nearest_neighbor(distances)
print(f"路径: {path}")
print(f"总距离: {sum(distances[path[i]][path[i+1]] for i in range(len(path)-1))}")
```
