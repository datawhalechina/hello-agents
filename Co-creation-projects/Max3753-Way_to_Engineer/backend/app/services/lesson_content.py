"""
课程内容 - 为每个课程提供丰富的Markdown内容
"""
from typing import Optional


def get_lesson_content(lesson_id: str, title: str, lesson_type: str, description: str) -> str:
    """根据课程ID返回对应的Markdown内容"""
    
    # 优先查找特定课程的内容
    custom = _get_custom_content(lesson_id, title)
    if custom:
        return custom
    
    # 通用模板
    return _get_generic_content(title, description, lesson_type)


def _get_custom_content(lesson_id: str, title: str) -> Optional[str]:
    """为特定课程ID返回个性化内容"""
    
    content_map = {
        # ======== 前端 - HTML/CSS ========
        "fe-html-01": """## 学习目标

- 理解 HTML 文档的基本结构
- 掌握 DOCTYPE、html、head、body 等核心标签
- 了解 meta 标签的常见用法

## HTML 文档的基本结构

每个 HTML 文档都遵循一个基本的骨架结构：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>文档标题</title>
</head>
<body>
    <!-- 页面可见内容 -->
    <h1>Hello, World!</h1>
    <p>这是我的第一个网页。</p>
</body>
</html>
```

### 各部分作用

| 标签 | 作用 |
|------|------|
| `<!DOCTYPE html>` | 声明文档类型为 HTML5 |
| `<html>` | 文档的根元素，所有内容包含在内 |
| `<head>` | 文档的元数据区（不可见） |
| `<body>` | 文档的内容区（用户可见） |

### `<head>` 中的常用标签

- **`<title>`** — 浏览器标签页显示的标题，对 SEO 也很重要
- **`<meta charset="UTF-8">`** — 设置字符编码，避免乱码
- **`<meta name="viewport">`** — 移动端适配声明
- **`<link>`** — 引入外部 CSS 文件
- **`<style>`** — 内嵌 CSS 样式

## 练习

创建一个包含以下内容的 HTML 文件：
1. 正确的文档结构声明
2. 设置标题为"我的第一个网页"
3. 在 body 中添加一个一级标题和一个段落

> 💡 **提示**：使用 VS Code 新建 `.html` 文件后，输入 `!` 并按 Tab 可以快速生成 HTML5 骨架。
""",
        
        "fe-html-02": """## 学习目标

- 掌握常用 HTML 标签的语义和用法
- 理解块级元素与行内元素的区别
- 学会使用列表、图片、链接等构建内容

## 常用标签

### 文本标签

```html
<!-- 标题 -->
<h1>一级标题</h1>
<h2>二级标题</h2>
<h3>三级标题</h3>

<!-- 段落与文本 -->
<p>这是一个段落。</p>
<strong>加重要内容</strong>
<em>强调文本</em>
<br> <!-- 换行 -->
```

### 列表

```html
<!-- 无序列表 -->
<ul>
    <li>苹果</li>
    <li>香蕉</li>
    <li>橘子</li>
</ul>

<!-- 有序列表 -->
<ol>
    <li>第一步：打开编辑器</li>
    <li>第二步：编写代码</li>
    <li>第三步：保存文件</li>
</ol>
```

### 链接与图片

```html
<!-- 链接 -->
<a href="https://example.com" target="_blank">打开示例网站</a>

<!-- 图片 -->
<img src="logo.png" alt="网站Logo" width="200">
```

> ⚠️ **注意**：`<a>` 的 `target="_blank"` 会在新标签页打开链接。`<img>` 的 `alt` 属性用于图片加载失败时的替代文本，对无障碍访问很重要。

## 块级 vs 行内元素

| 类别 | 特点 | 例子 |
|------|------|------|
| **块级元素** | 独占一行，可设置宽高 | `div`, `h1`-`h6`, `p`, `ul`, `ol` |
| **行内元素** | 不换行，宽高由内容决定 | `span`, `a`, `strong`, `em`, `img` |

## 练习

创建一个"我的兴趣爱好"页面，包含：
1. 一个二级标题
2. 一段自我介绍
3. 一个无序列表列出你的兴趣（至少3项）
4. 一张图片和指向你最喜欢网站的外部链接
""",
        
        "fe-css-01": """## 学习目标

- 理解 CSS 的作用和基本语法
- 掌握三种选择器：元素、类、ID
- 了解选择器的优先级规则

## CSS 基本语法

```css
选择器 {
    属性名: 属性值;
    属性名: 属性值;
}
```

### 引入 CSS 的方式

**1. 外部样式表（推荐）**

```html
<link rel="stylesheet" href="style.css">
```

**2. 内部样式表**

```html
<style>
    p {{ color: red; }}
</style>
```

**3. 行内样式（不推荐）**

```html
<p style="color: red;">这段文字是红色</p>
```

## 三种基本选择器

### 元素选择器

选中所有该类型的标签：

```css
p {{ color: #333; }}
h1 {{ font-size: 24px; }}
```

### 类选择器（`.`）

选中所有带有该 class 的元素，可重复使用：

```css
.highlight {{ background-color: yellow; }}
.card {{ border: 1px solid #ccc; }}
```

```html
<p class="highlight">这段有高亮背景</p>
<div class="card">这是一个卡片</div>
```

### ID 选择器（`#`）

**唯一**，一个页面中每个 ID 只能使用一次：

```css
#header {{ height: 60px; }}
#main-content {{ padding: 20px; }}
```

```html
<div id="header">页面头部</div>
```

## 优先级（权重）

当多个选择器冲突时，按权重决定：

| 选择器 | 权重 | 示例 |
|--------|------|------|
| 元素选择器 | 最低 | `p`、`h1` |
| 类选择器 | 中等 | `.card`、`.highlight` |
| ID选择器 | 最高 | `#header` |
| 行内样式 | 更高 | `style="..."` |
| `!important` | 最高（慎用） | `color: red !important` |

> 🧪 **实验**：给同一个元素同时设置类和 ID 样式，观察哪个生效。

## 练习

创建一个 HTML 页面并添加 CSS：
1. 用元素选择器设置全局字体
2. 用类选择器创建两个不同颜色的卡片
3. 用 ID 选择器设置页面标题的样式
""",

        "fe-css-02": """## 学习目标

- 理解盒模型的四个组成部分
- 掌握 width/height、padding、border、margin 的用法
- 学会使用 `box-sizing` 控制盒模型行为

## 盒模型

每个 HTML 元素都可以看作一个"盒子"，从内到外包含：

```
┌─────────────────────────────────┐
│          Margin (外边距)         │
│  ┌───────────────────────────┐  │
│  │      Border (边框)        │  │
│  │  ┌─────────────────────┐  │  │
│  │  │   Padding (内边距)   │  │  │
│  │  │  ┌───────────────┐  │  │  │
│  │  │  │   Content     │  │  │  │
│  │  │  │   (内容区域)   │  │  │  │
│  │  │  └───────────────┘  │  │  │
│  │  └─────────────────────┘  │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

### 代码示例

```css
.box {{
    width: 200px;
    padding: 20px;       /* 内容与边框之间的距离 */
    border: 2px solid #333;  /* 边框 */
    margin: 10px;        /* 盒子与其他元素的距离 */
}}
```

### 盒模型的计算

默认情况下（`box-sizing: content-box`）：

**实际宽度 = width + padding × 2 + border × 2**

这意味着 `width: 200px` 加上 `padding: 20px` 和 `border: 2px` 后，实际占用的宽度是 **244px**！

### `box-sizing: border-box`

推荐做法——让 width 包含 padding 和 border：

```css
* {{
    box-sizing: border-box;
}}
```

这样 `width: 200px` 就是最终渲染宽度，padding 和 border 向内压缩。

## display 属性

| 值 | 行为 |
|----|------|
| `block` | 块级，独占一行 |
| `inline` | 行内，不换行 |
| `inline-block` | 行内但可设宽高 |
| `none` | 隐藏元素，不占空间 |

## 练习

用 HTML + CSS 实现下图效果（描述：三个卡片并排，每个卡片有标题、文字、边框和间距）：
1. 三个 `div` 卡片横向排列
2. 每个卡片有 1px 边框、16px 内边距
3. 卡片之间用 margin 隔开
4. 使用 `box-sizing: border-box`
""",
        
        "fe-css-03": """## 学习目标

- 理解 Flexbox 的核心概念：主轴与交叉轴
- 掌握容器属性和项目属性
- 能使用 Flexbox 实现常见布局

## Flexbox 核心概念

Flexbox 是一种一维布局模型，适合在**一行或一列**中排列元素。

```css
.container {{
    display: flex;    /* 开启 Flexbox */
}}
```

### 主轴与交叉轴

- **主轴（main axis）** — `flex-direction` 决定的方向
- **交叉轴（cross axis）** — 与主轴垂直的方向

```
flex-direction: row;       → 主轴水平，从左到右
flex-direction: column;    → 主轴垂直，从上到下
```

## 容器属性

```css
.container {{
    display: flex;
    flex-direction: row;        /* row | column | row-reverse | column-reverse */
    justify-content: center;    /* 主轴对齐方式 */
    align-items: center;        /* 交叉轴对齐方式 */
    flex-wrap: wrap;            /* 是否换行 */
    gap: 16px;                  /* 项目间距（推荐） */
}}
```

### justify-content

```
flex-start   ┃ [项目1][项目2][项目3]
center       ┃    [项目1][项目2][项目3]
space-between ┃ [项目1]        [项目2]        [项目3]
space-around ┃  [项目1]    [项目2]    [项目3]
```

### align-items

```
stretch  ┃ 项目高度拉伸填满容器（默认）
center   ┃ 项目在交叉轴居中
flex-start ┃ 项目在交叉轴起始位置
```

## 项目属性

```css
.item {{
    flex: 1;              /* 分配剩余空间的比例 */
    align-self: center;   /* 单独对齐 */
    order: 2;             /* 排列顺序（越小越前） */
}}
```

## 常见布局示例

### 水平居中

```css
.parent {{
    display: flex;
    justify-content: center;
    align-items: center;
}}
```

### 两端对齐导航

```css
.nav {{
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
```

### 响应式卡片网格

```css
.grid {{
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
}}
.card {{
    flex: 1 1 300px;  /* 最小300px，自动换行 */
}}
```

## 练习

用 Flexbox 实现一个导航栏：
- 左侧是 Logo
- 中间是导航链接（首页、关于、服务、联系）
- 右侧是登录/注册按钮
- 垂直居中
""",

        # ======== 前端 - JavaScript ========
        "fe-js-01": """## 学习目标

- 理解 `let`、`const`、`var` 的区别
- 掌握 JavaScript 的基本数据类型
- 了解引用类型与基本类型的差异

## 变量声明

### `let` vs `const` vs `var`

| 关键字 | 可修改 | 作用域 | 推荐 |
|--------|--------|--------|------|
| `const` | ❌ 不可重新赋值 | 块级作用域 | **默认选择** |
| `let` | ✅ 可重新赋值 | 块级作用域 | 需要改变时使用 |
| `var` | ✅ 可重新赋值 | 函数作用域 | ❌ 避免使用 |

```javascript
const PI = 3.14159;
let count = 0;
count = 1;  // ✅ 可以

// 常见错误
const user = {{ name: 'Alice' }};
user.name = 'Bob';  // ✅ const 对象的内容可以修改
user = {{ name: 'Bob' }};  // ❌ 不能重新赋值
```

## 基本数据类型

| 类型 | 示例 | 说明 |
|------|------|------|
| `number` | `42`, `3.14` | 整数和浮点数 |
| `string` | `'hello'`, `"world"` | 文本 |
| `boolean` | `true`, `false` | 布尔值 |
| `null` | `null` | 空值 |
| `undefined` | `undefined` | 未定义 |
| `symbol` | `Symbol()` | 唯一标识符 |

```javascript
const name = 'Alice';
const age = 25;
const isStudent = true;
const score = null;
let grade;  // undefined

// typeof 运算符
console.log(typeof name);   // "string"
console.log(typeof age);    // "number"
```

### 动态类型

JavaScript 是动态类型语言，变量可以随时改变类型：

```javascript
let value = 'hello';
value = 42;       // 变成了 number
value = true;     // 变成了 boolean
```

### 类型转换

```javascript
// 隐式转换
const result = '5' - 2;    // 3 (字符串转数字)
const msg = '结果是: ' + 42;  // "结果是: 42"

// 显式转换
Number('42')     // 42
String(42)       // "42"
Boolean(0)       // false
Boolean('')      // false
Boolean('hello') // true
```

> ⚠️ **常见陷阱**：`'5' + 2` 结果是 `'52'`（字符串拼接），而 `'5' - 2` 结果是 `3`（数值减法）。

## 引用类型

对象和数组是引用类型，赋值传递的是引用：

```javascript
const a = {{ name: 'Alice' }};
const b = a;        // b 引用同一个对象
b.name = 'Bob';
console.log(a.name); // "Bob" — a 也被改了！
```

## 练习

1. 用 `const` 定义一个对象，包含你的姓名、年龄和爱好
2. 用 `let` 定义一个计数器，从 0 递增到 3
3. 分别使用 `typeof` 检查 `null`、`[]`、`{{}}` 的类型
""",

        "fe-js-02": """## 学习目标

- 掌握函数定义的多种方式
- 理解作用域和闭包的概念
- 了解箭头函数的特性

## 函数定义

### 函数声明 vs 函数表达式

```javascript
// 函数声明（会被提升）
function add(a, b) {{
    return a + b;
}}

// 函数表达式（不会被提升）
const multiply = function(a, b) {{
    return a * b;
}};
```

### 箭头函数

```javascript
// 基本语法
const add = (a, b) => a + b;
const square = x => x * x;  // 一个参数可省略括号
const greet = () => 'Hello!';

// 多行需要 {{}} 和 return
const sum = (a, b) => {{
    const result = a + b;
    return result;
}};
```

### 箭头函数 vs 普通函数

| 区别 | 普通函数 | 箭头函数 |
|------|----------|----------|
| `this` | 动态绑定 | 继承外层作用域 |
| `arguments` | 有 | 没有 |
| 作为构造函数 | ✅ | ❌ |

## 作用域

```javascript
const global = '全局变量';

function outer() {{
    const outerVar = '外部函数变量';
    
    function inner() {{
        const innerVar = '内部函数变量';
        console.log(global);   // ✅ 可访问
        console.log(outerVar); // ✅ 可访问
    }}
    
    console.log(innerVar); // ❌ 不可访问
}}
```

## 闭包

函数 + 其被创建时所在的作用域环境的组合：

```javascript
function createCounter() {{
    let count = 0;
    return function() {{
        count++;
        return count;
    }};
}}

const counter = createCounter();
console.log(counter()); // 1
console.log(counter()); // 2
console.log(counter()); // 3
```

> 💡 **用途**：数据私有化、函数工厂、模块模式

## 练习

1. 写一个箭头函数 `isEven(n)` 判断数字是否为偶数
2. 用闭包实现一个 `makeMultiplier(x)`，返回一个乘以 `x` 的函数
3. 比较普通函数和箭头函数中 `this` 的行为差异
""",

        # ======== 前端 - Vue ========
        "fe-vue-01": """## 学习目标

- 理解 Vue 3 的核心概念
- 掌握 `ref` 和 `reactive` 响应式 API
- 学会使用模板语法

## 什么是 Vue？

Vue 是一个用于构建用户界面的**渐进式框架**。核心特性：

- **声明式渲染** — 通过模板语法将数据绑定到 DOM
- **响应式系统** — 数据变化自动更新视图
- **组件化** — UI 拆分为独立的可复用组件

## 创建 Vue 应用

```javascript
import {{ createApp, ref }} from 'vue'

createApp({{
    setup() {{
        const count = ref(0)
        const increment = () => count.value++
        
        return {{ count, increment }}
    }}
}}).mount('#app')
```

```html
<div id="app">
    <p>计数: {{ "{{ count }}" }}</p>
    <button @click="increment">+1</button>
</div>
```

## 响应式 API

### `ref` — 基本响应式

```javascript
import {{ ref }} from 'vue'

const count = ref(0)
console.log(count.value) // 0

count.value = 1
```

> 在模板中使用时自动解包，不需要 `.value`

### `reactive` — 对象响应式

```javascript
import {{ reactive }} from 'vue'

const user = reactive({{
    name: 'Alice',
    age: 25
}})

user.age = 26  // 直接修改，无需 .value
```

### `computed` — 计算属性

```javascript
import {{ ref, computed }} from 'vue'

const price = ref(100)
const quantity = ref(2)
const total = computed(() => price.value * quantity.value)
```

## 模板语法

```html
<!-- 文本插值 -->
<p>{{ "{{ message }}" }}</p>

<!-- 属性绑定 -->
<img :src="imageUrl">

<!-- 事件绑定 -->
<button @click="handleClick">点击</button>

<!-- 条件渲染 -->
<p v-if="isVisible">可见</p>

<!-- 列表渲染 -->
<li v-for="(item, index) in items" :key="index">{{ "{{ item }}" }}</li>

<!-- 双向绑定 -->
<input v-model="username">
```

## 练习

创建一个简单的 Vue 应用：
1. 用 `ref` 定义用户名和年龄
2. 用 `computed` 计算是否成年（>=18）
3. 在模板中展示这些数据
""",

        # ======== 后端 - Python ========
        "be-py-01": """## 学习目标

- 回顾 Python 基础语法
- 理解列表推导式、装饰器等进阶用法
- 掌握 Python 常见最佳实践

## Python 基础回顾

```python
# 变量与类型
name: str = "Python"
version: float = 3.11

# 列表推导式
squares = [x**2 for x in range(10) if x % 2 == 0]

# 字典操作
user = {{"name": "Alice", "age": 25}}
print(user.get("name", "Unknown"))
```

## 装饰器

装饰器是一种在不修改原函数代码的情况下扩展其功能的方式：

```python
from functools import wraps

def log_calls(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[LOG] 调用 {{func.__name__}}")
        result = func(*args, **kwargs)
        print(f"[LOG] {{func.__name__}} 返回 {{result}}")
        return result
    return wrapper

@log_calls
def add(a, b):
    return a + b

add(3, 5)
# [LOG] 调用 add
# [LOG] add 返回 8
```

## 上下文管理器

```python
# 使用 with 语句
with open("file.txt", "r") as f:
    content = f.read()

# 自定义上下文管理器
from contextlib import contextmanager

@contextmanager
def timer():
    import time
    start = time.time()
    try:
        yield
    finally:
        elapsed = time.time() - start
        print(f"耗时: {{elapsed:.2f}}秒")

with timer():
    sum(range(1000000))
```

## 类型提示

```python
from typing import List, Optional, Dict

def process_users(users: List[Dict[str, str]]) -> List[str]:
    \"\"\"提取所有用户名\"\"\"
    return [u.get("name", "") for u in users]

def find_user(id: int) -> Optional[Dict[str, str]]:
    \"\"\"根据 ID 查找用户\"\"\"
    return None  # 未找到
```

## 练习

1. 编写一个装饰器 `@retry(max_attempts=3)`，让函数在抛出异常时自动重试
2. 写一个上下文管理器，用于测量代码块的执行时间
3. 使用类型提示定义一个函数签名，处理用户列表数据
""",

        "be-py-02": """## 学习目标

- 理解文件读写的基本模式
- 掌握异常处理的正确方式
- 学会使用标准库处理常见任务

## 文件操作

```python
# 推荐方式：使用 with 语句
with open("data.txt", "r", encoding="utf-8") as f:
    content = f.read()

# 逐行读取
with open("data.txt", "r") as f:
    for line in f:
        print(line.strip())

# 写入文件
with open("output.txt", "w") as f:
    f.write("Hello, World!\\n")
```

## 异常处理

```python
try:
    result = 10 / 0
except ZeroDivisionError as e:
    print(f"不能除以零: {{e}}")
except ValueError as e:
    print(f"值错误: {{e}}")
except Exception as e:
    print(f"未知错误: {{e}}")
else:
    print("没有发生异常")
finally:
    print("总是执行")
```

### 自定义异常

```python
class ValidationError(Exception):
    \"\"\"数据验证失败\"\"\"
    pass

def validate_age(age: int):
    if age < 0 or age > 150:
        raise ValidationError(f"无效年龄: {{age}}")
```

## 标准库常用模块

```python
import json
import os
import sys
from datetime import datetime, timedelta

# JSON 处理
data = {{"name": "Alice", "age": 25}}
json_str = json.dumps(data, ensure_ascii=False)
parsed = json.loads(json_str)

# 路径操作
path = os.path.join("data", "subdir", "file.txt")
print(os.path.exists(path))

# 日期时间
now = datetime.now()
tomorrow = now + timedelta(days=1)
print(now.strftime("%Y-%m-%d %H:%M:%S"))
```

## 练习

1. 读取一个 JSON 配置文件，解析其中的设置
2. 编写一个函数，安全地将字符串转换为整数，转换失败时返回 None
3. 使用 `os` 模块遍历一个目录下的所有 Python 文件
4. 使用 `datetime` 计算距离下个生日还有多少天
""",

        # ======== 后端 - API ========
        "be-api-01": """## 学习目标

- 理解 REST API 的核心原则
- 掌握 HTTP 方法、状态码的正确使用
- 学会设计资源导向的 URL

## REST 核心原则

REST（Representational State Transfer）是一种 API 设计风格：

1. **资源导向** — URL 表示资源（名词），而不是操作（动词）
2. **HTTP 方法表示操作** — GET/ POST/ PUT/ DELETE
3. **无状态** — 每个请求包含所有必要信息
4. **统一接口** — 一致的 URL 模式和响应格式

## HTTP 方法

| 方法 | 作用 | 幂等 | 请求体 |
|------|------|------|--------|
| GET | 获取资源 | ✅ | 通常无 |
| POST | 创建资源 | ❌ | 有 |
| PUT | 完整更新资源 | ✅ | 有 |
| PATCH | 部分更新资源 | ❌ | 有 |
| DELETE | 删除资源 | ✅ | 通常无 |

## 状态码

| 状态码 | 含义 | 使用场景 |
|--------|------|----------|
| 200 OK | 请求成功 | GET、PUT 成功 |
| 201 Created | 创建成功 | POST 创建资源 |
| 204 No Content | 成功无返回体 | DELETE 成功 |
| 400 Bad Request | 客户端请求错误 | 参数校验失败 |
| 404 Not Found | 资源不存在 | 查询不存在的 ID |
| 409 Conflict | 资源冲突 | 创建重复资源 |
| 500 Internal Server Error | 服务器错误 | 未预期的异常 |

## URL 设计

```python
# ✅ 好的设计（资源导向）
GET    /api/users              # 获取用户列表
GET    /api/users/{{id}}        # 获取单个用户
POST   /api/users              # 创建用户
PUT    /api/users/{{id}}        # 更新用户
DELETE /api/users/{{id}}        # 删除用户

# ✅ 查询参数用于过滤/排序/分页
GET /api/tasks?status=done&page=2&sort=created_at

# ✅ 子资源
GET /api/users/{{id}}/posts      # 用户的文章列表

# ❌ 不好的设计（动词在 URL 中）
GET    /api/getUser             # ❌
POST   /api/createUser          # ❌
POST   /api/deleteUser          # ❌
```

## FastAPI 快速开始

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float

@app.get("/items")
async def list_items():
    return [{{"id": 1, "name": "Item 1", "price": 9.99}}]

@app.post("/items")
async def create_item(item: Item):
    return {{"id": 2, **item.model_dump()}}
```

## 练习

1. 为一个"博客系统"设计 RESTful API 端点（文章、评论、标签）
2. 说明每个端点的 HTTP 方法、URL、请求参数和响应状态码
""",

        "be-api-02": """## 学习目标

- 掌握 FastAPI 路由和参数处理
- 理解请求体验证和响应模型
- 学会使用依赖注入

## FastAPI 路由进阶

### 路径参数与查询参数

```python
from fastapi import FastAPI, Query, Path

app = FastAPI()

@app.get("/users/{{user_id}}")
async def get_user(
    user_id: int = Path(..., title="用户ID"),
    include_details: bool = Query(False, title="是否包含详情")
):
    return {{"user_id": user_id, "details": include_details}}
```

### 请求体验证

```python
from pydantic import BaseModel, Field

class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[\\w.-]+@[\\w.-]+\\.\\w{{2,}}$")
    age: int = Field(ge=0, le=150)

@app.post("/users")
async def create_user(user: CreateUserRequest):
    return {{"message": "用户创建成功", "user": user}}
```

### 响应模型

```python
from typing import List
from pydantic import BaseModel

class UserResponse(BaseModel):
    id: int
    username: str
    email: str

@app.get("/users", response_model=List[UserResponse])
async def list_users():
    return [
        UserResponse(id=1, username="alice", email="alice@example.com")
    ]
```

## 依赖注入

```python
from fastapi import Depends, HTTPException

def get_current_user(token: str = Query(...)):
    if token != "secret":
        raise HTTPException(status_code=401, detail="未授权")
    return {{"id": 1, "username": "alice"}}

@app.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return user
```

## 错误处理

```python
from fastapi import HTTPException
from fastapi.responses import JSONResponse

@app.get("/items/{{item_id}}")
async def get_item(item_id: int):
    if item_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="无效的项目ID"
        )
    # ... 查找项目
    return {{"id": item_id, "name": "Sample Item"}}
```

## 练习

1. 创建一个 Todo 的 CRUD API（使用内存列表存储）
2. 添加参数校验（标题非空、状态只能是 pending/done）
3. 使用响应模型控制返回字段
""",
        
        # ======== 全栈 - Web基础 ========
        "fs-web-01": """## 学习目标

- 理解 HTTP 协议的基本原理
- 掌握请求-响应模型
- 了解浏览器如何加载网页

## HTTP 协议

HTTP（超文本传输协议）是 Web 的基础通信协议。

### 请求-响应模型

```
浏览器                         服务器
  │                              │
  ├── GET /index.html ──────────►│
  │                              ├── 查找文件
  │◄── 200 OK + HTML 内容 ──────┤
  │                              │
  ├── GET /style.css ───────────►│
  │◄── 200 OK + CSS 内容 ───────┤
  │                              │
  ├── GET /app.js ──────────────►│
  │◄── 200 OK + JS 内容 ────────┤
```

### HTTP 请求结构

```
GET /api/users HTTP/1.1
Host: example.com
Authorization: Bearer token123
Content-Type: application/json

{{"name": "Alice"}}
```

### HTTP 响应结构

```
HTTP/1.1 200 OK
Content-Type: application/json

{{"id": 1, "name": "Alice"}}
```

## 常见请求头

| 请求头 | 作用 |
|--------|------|
| `Authorization` | 认证信息 |
| `Content-Type` | 请求体格式 |
| `Accept` | 期望的响应格式 |
| `User-Agent` | 客户端标识 |

## 常见响应头

| 响应头 | 作用 |
|--------|------|
| `Content-Type` | 响应体格式 |
| `Set-Cookie` | 设置 Cookie |
| `Cache-Control` | 缓存策略 |
| `Access-Control-Allow-Origin` | CORS 设置 |

## 浏览器加载流程

1. 解析 HTML → 构建 DOM 树
2. 加载 CSS → 构建 CSSOM 树
3. 合并为渲染树（Render Tree）
4. 布局（Layout）→ 计算位置和大小
5. 绘制（Paint）→ 渲染到屏幕

> 💡 **关键**：CSS 会阻塞渲染，JavaScript 会阻塞解析。所以 `<script>` 标签通常放在 `</body>` 前。

## 练习

1. 用浏览器的开发者工具（F12）打开 Network 面板，访问一个网站，观察所有请求
2. 识别每个请求的类型（文档、样式、脚本、图片）
3. 查看一个 API 请求的请求头、响应头和响应体
""",
    }

    # 检查是否有匹配的内容
    if lesson_id in content_map:
        return content_map[lesson_id]
    
    return None


def _get_generic_content(title: str, description: str, lesson_type: str) -> str:
    """为没有个性化内容的课程生成通用内容"""
    
    type_headers = {
        "theory": "📖 理论学习",
        "practice": "💻 实践练习",
        "quiz": "❓ 知识测验",
        "project": "🚀 项目实战",
    }
    
    type_content = {
        "theory": """
## 概述

**{title}** — {description}

### 学习要点

请跟随导师在对话中学习本课程的核心概念。导师将为你提供：

1. 详细的概念讲解和原理解析
2. 实际代码示例和最佳实践
3. 常见陷阱和注意事项

### 学习建议

- 在 Chat 中发送"开始学习 {title}"，导师会引导你学习
- 遇到不理解的概念，随时追问
- 完成学习后点击"完成课程"标记进度
""",
        "practice": """
## 概述

**{title}** — {description}

### 练习内容

这是一个实践课程，请在 Chat 中向导师请求练习任务。

### 完成标准

- [ ] 理解练习要求
- [ ] 独立完成代码实现
- [ ] 验证代码正确运行
- [ ] 与导师讨论你的实现方案

### 提示

> 完成练习后，可以让导师 review 你的代码并提供改进建议。
""",
        "quiz": """
## 概述

**{title}** — {description}

### 测验说明

本课程包含知识测验，检验你对前面所学内容的理解。

请在 Chat 中让导师为你生成测验题目。

### 准备

- 复习相关课程内容
- 准备好回答概念题和代码题
""",
        "project": """
## 概述

**{title}** — {description}

### 项目要求

这是一个实战项目，综合运用所学知识完成一个完整的功能模块。

请在 Chat 中让导师为你分配项目任务并提供指导。

### 交付标准

- [ ] 功能完整可用
- [ ] 代码结构清晰
- [ ] 包含错误处理
- [ ] 有必要的注释
""",
    }
    
    header = type_headers.get(lesson_type, "📖 学习内容")
    body = type_content.get(lesson_type, type_content["theory"])
    
    return f"""## {header}

{body}
"""
