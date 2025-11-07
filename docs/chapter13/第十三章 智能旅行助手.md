# 第十三章 智能旅行助手

在前面的章节中，我们从零开始构建了 HelloAgents 框架，实现了多种智能体范式、工具系统、记忆机制、协议通信和性能评估等核心功能。从本章开始，我们将进入一个全新的阶段：<strong>将所学知识融会贯通，构建完整的实用应用。</strong>

还记得在第一章中，我们构建的第一个智能体吗？那是一个简单的智能旅行助手，展示了`Thought-Action-Observation`循环的基本原理。本章的智能旅行助手将是一个完整的项目，包含以下核心功能：

<strong>（1）智能行程规划</strong>：用户输入目的地、日期、偏好等信息，系统自动生成包含景点、餐饮、酒店的完整行程计划。

<strong>（2）地图可视化</strong>：在地图上标注景点位置、绘制游览路线，让行程一目了然。

<strong>（3）预算计算</strong>：自动计算门票、酒店、餐饮、交通费用，显示预算明细。

<strong>（4）行程编辑</strong>：支持添加、删除、调整景点，实时更新地图。

<strong>（5）导出功能</strong>：支持导出为 PDF 或图片，方便保存和分享。



## 13.1 项目概述与架构设计

### 13.1.1 为什么需要智能旅行助手

规划一次旅行是一件既令人兴奋又令人头疼的事情。你需要在网上搜索景点信息，对比不同的攻略，查看天气预报，预订酒店，计算预算，规划路线。这个过程可能需要花费几个小时甚至几天的时间。而且即使花了这么多时间，你也不确定规划的行程是否合理，是否遗漏了什么重要的景点，预算是否准确。

传统的旅行规划方式有几个痛点。首先是<strong>信息分散</strong>。景点信息在旅游网站上，天气信息在天气网站上，酒店信息在预订网站上，你需要在多个网站之间切换，手动整合这些信息。其次是<strong>缺少个性化</strong>。大部分攻略都是通用的，不考虑你的个人偏好、预算限制、出行时间等因素。最后是<strong>难以调整</strong>。当你想修改行程时，可能需要重新规划整个行程，因为景点的顺序、时间安排、预算都是相互关联的。

AI 技术为解决这些问题提供了新的可能。想象一下，你只需要告诉系统"我想去北京玩 3 天，喜欢历史文化，预算中等"，系统就能自动为你生成一个完整的行程计划，包括每天去哪些景点、在哪里吃饭、住哪个酒店、需要多少预算。而且这个计划是可以调整的，你可以删除不喜欢的景点，调整游览顺序，系统会自动更新地图和预算。

这就是我们要构建的智能旅行助手。它不仅仅是一个技术演示，而是一个真正有用的应用。通过这个项目，你会学到如何将 AI 技术应用到实际问题中，如何设计多智能体系统，如何构建完整的 Web 应用。

### 13.1.2 技术架构概览

系统采用经典的<strong>前后端分离架构</strong>，分为四个层次，如图 13.1 所示：

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-1.png" alt="" width="85%"/>
  <p>图 13.1 智能旅行助手技术架构</p>
</div>

<strong>（1）前端层 (Vue3+TypeScript)</strong>：负责用户交互和数据展示，包括表单输入、结果展示、地图可视化。

<strong>（2）后端层 (FastAPI)</strong>：负责 API 路由、数据验证、业务逻辑。

<strong>（3）智能体层 (HelloAgents)</strong>：负责任务分解、工具调用、结果整合。包含 4 个专门的 Agent。

<strong>（4）外部服务层</strong>：提供数据和能力，包括高德地图 API、Unsplash API、LLM API。

数据流转过程如下：用户在前端填写表单 → 后端验证数据 → 调用智能体系统 → 智能体依次调用景点搜索、天气查询、酒店推荐、行程规划 Agent → 每个 Agent 通过 MCP 协议调用外部 API → 整合结果返回前端 → 前端渲染展示。

项目的结构参考如下，提供便于定位源码：
```
helloagents-trip-planner/
├── backend/                    # 后端代码
│   ├── app/
│   │   ├── agents/            # 智能体实现
│   │   ├── api/               # API路由
│   │   ├── models/            # 数据模型
│   │   ├── services/          # 服务层
│   │   └── config.py          # 配置文件
│   └── requirements.txt       # Python依赖
│
└── frontend/                   # 前端代码
    ├── src/
    │   ├── views/             # 页面组件
    │   ├── services/          # API服务
    │   ├── types/             # 类型定义
    │   └── router/            # 路由配置
    └── package.json           # npm依赖
```

详细的架构设计和数据流转将在后续章节中介绍。

### 13.1.3 快速体验：5 分钟运行项目

在深入学习实现细节之前，让我们先把项目跑起来，看看最终的效果。这样你会对整个系统有一个直观的认识。

<strong>环境要求：</strong>

- Python 3.10 或更高版本
- Node.js 16.0 或更高版本
- npm 8.0 或更高版本

<strong>获取 API 密钥：</strong>

你需要准备以下 API 密钥：

- LLM 的 API(OpenAI、DeepSeek 等)
- 高德地图 Web 服务 Key：访问 https://console.amap.com/ 注册并创建应用
- Unsplash Access Key：访问 https://unsplash.com/developers 注册并创建应用

将所有 API 密钥放入`.env`文件。

启动后端：

```bash
# 1. 进入后端目录
cd helloagents-trip-planner/backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑.env文件，填入你的API密钥

# 4. 启动后端服务
uvicorn app.api.main:app --reload
# 或者
python run.py
```

成功启动后，访问 http://localhost:8000/docs 可以看到 API 文档。

打开新的终端窗口：

```bash
# 1. 进入前端目录
cd helloagents-trip-planner/frontend

# 2. 安装依赖
npm install

# 3. 启动前端服务
npm run dev
```

成功启动后，访问 http://localhost:5173 即可使用应用。

体验核心功能：

首先需在首页表单中填写目的地城市、旅行日期、偏好、预算、交通及住宿类型等信息。点击“开始规划”按钮后，系统会显示加载进度条，并很快生成结果页面，如图 13.2 所示。

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-2.png" alt="" width="85%"/>
  <p>图 13.2 旅行助手规划进行页面</p>
</div>

随后加载成功，该页面会清晰展示行程概览、预算明细、景点地图、每日行程详情和天气信息，如图 13.3，13.4 所示。

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-3.png" alt="" width="85%"/>
  <p>图 13.3 旅行助手规划完成页面</p>
</div>

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-4.png" alt="" width="85%"/>
  <p>图 13.4 旅行助手规划完成页面</p>
</div>

如果用户需要个性化调整，可以点击“编辑行程”按钮，自由调整景点顺序或删除某个景点，如图 13.5 所示。规划完成后，通过“导出行程”下拉菜单，即可将最终方案轻松保存为图片或 PDF 文件，方便随时查阅。

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-5.png" alt="" width="85%"/>
  <p>图 13.5 旅行助手规划完成页面</p>
</div>

## 13.2 数据模型设计

### 13.2.1 Web 应用中的数据流转

在构建智能旅行助手时，我们需要解决一个核心问题：<strong>如何表示和传递旅行计划数据?</strong> 

我们需要理解一个完整的 Web 应用中数据是如何流转的。想象一下，当用户在浏览器中点击"开始规划"按钮时，会发生什么？

用户在前端填写的表单数据(目的地、日期、预算等)需要通过 HTTP 请求发送到后端服务器。后端接收到数据后，会调用智能体系统进行处理。智能体又会调用高德地图 API、Unsplash API 等外部服务获取数据。这些外部 API 返回的数据格式各不相同，有的用`lng`，有的用`lon`，有的用`longitude`。最后，后端需要将处理好的数据返回给前端，前端再渲染成用户看到的页面。

在这个过程中，数据经历了多次转换：前端表单 → HTTP 请求 → 后端 Python 对象 → 外部 API 响应 → 后端 Python 对象 → HTTP 响应 → 前端 TypeScript 对象 → 页面展示。如果没有统一的数据格式，每一步转换都可能出错。这就是为什么我们需要<strong>数据模型</strong>。

### 13.2.2 从字典到 Pydantic 模型

让我们从第一章的简单原型开始。在那个原型中，我们使用 Python 字典来表示景点数据：

```python
# 第一章的做法：使用字典
attraction = {
    "name": "故宫",
    "location": {"lng": 116.397128,"lat": 39.916527},
    "price": 60
}

# 访问数据
lng = attraction["location"]["lng"]
```

这种方式在原型阶段很方便，但在实际项目中会遇到很多问题。首先是<strong>字段名不统一</strong>的问题。高德地图 API 返回的位置数据是`"116.397128，39.916527"`这样的字符串，需要手动分割成经纬度。而 Unsplash API 可能使用`longitude`和`latitude`。如果我们在代码中到处都用字典，就需要在每个地方都处理这些差异。

其次是<strong>类型安全</strong>的问题。假设我们不小心把`price`写成了字符串`"60"`，在 Python 中这不会立即报错，但在计算总预算时就会出问题。更糟糕的是，这种错误只能在运行时才能发现，而且错误信息可能很难定位。

最后是<strong>维护性</strong>的问题。当我们需要给景点添加新字段(比如`rating`评分)时，需要在代码的多个地方修改。如果遗漏了某个地方，就会导致数据不一致。

Pydantic 提供了一个解决方案。它是 Python 的数据验证库，可以让我们用类来定义数据结构，并自动处理验证、转换和序列化。让我们看一个简单的例子：

```python
from pydantic import BaseModel,Field

class Location(BaseModel):
    longitude: float = Field(...,description="经度")
    latitude: float = Field(...,description="纬度")

class Attraction(BaseModel):
    name: str
    location: Location
    ticket_price: int = 0

# 创建对象
attraction = Attraction(
    name="故宫",
    location=Location(longitude=116.397128,latitude=39.916527),
    ticket_price=60
)

# 类型安全的访问
lng = attraction.location.longitude  # IDE会提供代码补全
```

这样做有几个好处。首先，如果我们传入了错误的类型(比如把`ticket_price`设为字符串)，Pydantic 会立即抛出异常，告诉我们哪里出错了。其次，IDE 可以根据类型定义提供代码补全和类型检查，大大减少了拼写错误。最后，当我们需要修改数据结构时，只需要修改类定义，所有使用这个类的地方都会自动更新。

### 13.2.3 Pydantic 的核心概念

在深入设计我们的数据模型之前，让我们先了解 Pydantic 的几个核心概念。Pydantic 的基础是`BaseModel`类，所有的数据模型都需要继承这个类。每个字段都可以指定类型，Pydantic 会自动进行类型检查和转换。

字段定义使用`Field`函数，它可以指定默认值、描述、验证规则等。`...`表示这个字段是必填的，如果创建对象时没有提供这个字段，Pydantic 会抛出异常。我们也可以使用`Optional`来表示可选字段，或者直接提供默认值。

```python
from pydantic import BaseModel,Field
from typing import Optional,List

class Attraction(BaseModel):
    name: str = Field(...,description="景点名称")  # 必填
    rating: float = Field(default=0.0,ge=0,le=5)  # 默认值,范围验证
    visit_duration: int = Field(default=60,gt=0)  # 大于0
    description: Optional[str] = None  # 可选字段
```

Pydantic 还支持嵌套模型和列表。我们可以在一个模型中使用另一个模型作为字段类型,这样就可以构建复杂的数据结构。比如，一个景点包含位置信息，一个行程包含多个景点。

```python
class DayPlan(BaseModel):
    date: str
    attractions: List[Attraction]  # 景点列表
    hotel: Optional[Hotel] = None  # 可选的酒店信息
```

最强大的功能之一是<strong>自定义验证器</strong>。有时候外部 API 返回的数据格式不符合我们的要求，我们可以使用`field_validator`装饰器来自定义验证和转换逻辑。比如，高德地图返回的温度是`"16°C"`这样的字符串，我们需要把它转换成数字：

```python
from pydantic import field_validator

class WeatherInfo(BaseModel):
    temperature: int
    
    @field_validator('temperature',mode='before')
    def parse_temperature(cls,v):
        """解析温度字符串："16°C" -> 16"""
        if isinstance(v,str):
            v = v.replace('°C','').replace('℃','').strip()
            return int(v)
        return v
```

这个验证器会在创建对象之前自动执行，将字符串转换成整数。这样我们就不需要在代码的每个地方都手动处理温度格式了。

### 13.2.4 自底向上的模型设计

现在让我们开始设计智能旅行助手的数据模型。一个好的设计原则是<strong>自底向上</strong>：先定义最基础的模型，然后逐步组合成复杂的结构。这样做的好处是每个模型都很简单，容易理解和维护。

最基础的模型是<strong>位置信息</strong>。无论是景点、酒店还是餐厅，都需要位置信息。我们定义一个`Location`类来表示经纬度坐标：

```python
class Location(BaseModel):
    """位置信息(经纬度坐标)"""
    longitude: float = Field(...,description="经度",ge=-180,le=180)
    latitude: float = Field(...,description="纬度",ge=-90,le=90)
```

这里我们使用了范围验证(`ge`表示大于等于，`le`表示小于等于)，确保经纬度的值在合理范围内。

接下来是<strong>景点信息</strong>。一个景点包含名称、地址、位置、游览时间、描述、评分、图片和门票价格等信息。注意我们使用了`Location`作为字段类型，这就是嵌套模型：

```python
class Attraction(BaseModel):
    """景点信息"""
    name: str = Field(...,description="景点名称")
    address: str = Field(...,description="地址")
    location: Location = Field(...,description="经纬度坐标")
    visit_duration: int = Field(...,description="建议游览时间(分钟)",gt=0)
    description: str = Field(...,description="景点描述")
    category: Optional[str] = Field(default="景点",description="景点类别")
    rating: Optional[float] = Field(default=None,ge=0,le=5,description="评分")
    image_url: Optional[str] = Field(default=None,description="图片URL")
    ticket_price: int = Field(default=0,ge=0,description="门票价格(元)")
```

类似地，我们定义<strong>餐饮信息</strong>和<strong>酒店信息</strong>。这些模型的结构都很相似，都包含名称、地址、位置和费用等基本信息：

```python
class Meal(BaseModel):
    """餐饮信息"""
    type: str = Field(...,description="餐饮类型：breakfast/lunch/dinner/snack")
    name: str = Field(...,description="餐饮名称")
    address: Optional[str] = Field(default=None,description="地址")
    location: Optional[Location] = Field(default=None,description="经纬度坐标")
    description: Optional[str] = Field(default=None,description="描述")
    estimated_cost: int = Field(default=0,description="预估费用(元)")

class Hotel(BaseModel):
    """酒店信息"""
    name: str = Field(...,description="酒店名称")
    address: str = Field(default="",description="酒店地址")
    location: Optional[Location] = Field(default=None,description="酒店位置")
    price_range: str = Field(default="",description="价格范围")
    rating: str = Field(default="",description="评分")
    distance: str = Field(default="",description="距离景点距离")
    type: str = Field(default="",description="酒店类型")
    estimated_cost: int = Field(default=0,description="预估费用(元/晚)")
```

<strong>预算信息</strong>是一个特殊的模型，它不包含位置信息，而是包含各项费用的汇总：

```python
class Budget(BaseModel):
    """预算信息"""
    total_attractions: int = Field(default=0,description="景点门票总费用")
    total_hotels: int = Field(default=0,description="酒店总费用")
    total_meals: int = Field(default=0,description="餐饮总费用")
    total_transportation: int = Field(default=0,description="交通总费用")
    total: int = Field(default=0,description="总费用")
```

现在我们可以组合这些基础模型，构建<strong>单日行程</strong>。一个单日行程包含日期、描述、交通方式、住宿安排、酒店、景点列表和餐饮列表：

```python
class DayPlan(BaseModel):
    """单日行程"""
    date: str = Field(...,description="日期")
    day_index: int = Field(...,description="第几天(从0开始)")
    description: str = Field(...,description="当日行程描述")
    transportation: str = Field(...,description="交通方式")
    accommodation: str = Field(...,description="住宿安排")
    hotel: Optional[Hotel] = Field(default=None,description="酒店信息")
    attractions: List[Attraction] = Field(default_factory=list,description="景点列表")
    meals: List[Meal] = Field(default_factory=list,description="餐饮安排")
```

注意这里使用了`List[Attraction]`来表示景点列表，`default_factory=list`表示默认值是一个空列表。

<strong>天气信息</strong>需要特殊处理，因为高德地图返回的温度格式不规范。我们使用自定义验证器来处理：

```python
class WeatherInfo(BaseModel):
    """天气信息"""
    date: str = Field(...,description="日期")
    day_weather: str = Field(...,description="白天天气")
    night_weather: str = Field(...,description="夜间天气")
    day_temp: int = Field(...,description="白天温度(摄氏度)")
    night_temp: int = Field(...,description="夜间温度(摄氏度)")
    wind_direction: str = Field(...,description="风向")
    wind_power: str = Field(...,description="风力")
    
    @field_validator('day_temp','night_temp',mode='before')
    def parse_temperature(cls,v):
        """解析温度字符串："16°C" -> 16"""
        if isinstance(v,str):
            v = v.replace('°C','').replace('℃','').replace('°','').strip()
            try:
                return int(v)
            except ValueError:
                return 0  # 容错处理
        return v
```

最后，我们定义<strong>完整的旅行计划</strong>。这是最顶层的模型，包含了所有的信息：

```python
class TripPlan(BaseModel):
    """旅行计划"""
    city: str = Field(...,description="目的地城市")
    start_date: str = Field(...,description="开始日期")
    end_date: str = Field(...,description="结束日期")
    days: List[DayPlan] = Field(default_factory=list,description="每日行程")
    weather_info: List[WeatherInfo] = Field(default_factory=list,description="天气信息")
    overall_suggestions: str = Field(...,description="总体建议")
    budget: Optional[Budget] = Field(default=None,description="预算信息")
```

这样，我们就完成了整个数据模型的设计。从最基础的`Location`，到`Attraction`、`Meal`、`Hotel`，再到`DayPlan`，最后到`TripPlan`，形成了一个清晰的层次结构。

### 13.2.5 数据模型在 Web 应用中的应用

现在让我们看看这些数据模型如何在实际的 Web 应用中使用。在 FastAPI 中，Pydantic 模型可以直接用作请求和响应的类型定义。FastAPI 会自动进行数据验证、序列化和文档生成。

```python
from fastapi import FastAPI
from app.models.schemas import TripPlanRequest,TripPlan

app = FastAPI()

@app.post("/api/trip/plan",response_model=TripPlan)
async def create_trip_plan(request: TripPlanRequest) -> TripPlan:
    """
    创建旅行计划
    
    FastAPI自动：
    1. 验证请求数据(TripPlanRequest)
    2. 验证响应数据(TripPlan)
    3. 生成OpenAPI文档
    """
    trip_plan = await generate_trip_plan(request)
    return trip_plan
```

当用户发送 POST 请求到`/api/trip/plan`时，FastAPI 会自动将 JSON 数据转换成`TripPlanRequest`对象。如果数据格式不正确(比如缺少必填字段，或者类型不匹配)，FastAPI 会自动返回 400 错误，并告诉用户哪里出错了。

在前端，我们也需要定义对应的 TypeScript 类型。虽然 TypeScript 和 Python 是不同的语言，但数据结构是一样的：

```typescript
interface Location {
  longitude: number;
  latitude: number;
}

interface Attraction {
  name: string;
  address: string;
  location: Location;
  visit_duration: number;
  ticket_price: number;
}

interface TripPlan {
  city: string;
  start_date: string;
  end_date: string;
  days: DayPlan[];
}
```

这样，前后端就使用了统一的数据格式。当后端返回`TripPlan`对象时，前端可以直接使用，不需要任何转换。TypeScript 的类型检查也能帮助我们避免很多错误。

## 13.3 多智能体协作设计

### 13.3.1 为何需要多智能体

在第七章中，我们学习了如何使用 SimpleAgent 来构建智能体。SimpleAgent 的设计理念是简单直接：每次调用`run()`方法时，Agent 会分析用户的问题，决定是否需要调用工具，然后返回结果。这种设计在处理简单任务时非常有效，但当面对旅行规划这样的任务时，就会遇到一些问题。

如果用单个 Agent 来完成旅行规划。这个 Agent 需要做什么呢？首先，它要搜索景点信息，这需要调用高德地图的 POI 搜索工具。然后，它要查询天气信息，这需要调用天气查询工具。接着，它要搜索酒店信息，这又需要调用 POI 搜索工具。最后，它要把所有这些信息整合起来，生成一个完整的旅行计划。

这听起来很简单，但实际操作时会遇到第一个问题：<strong>工具调用的限制</strong>。SimpleAgent 每次`run()`调用只能执行一个工具。这意味着我们需要多次调用`run()`方法，每次调用处理一个任务。但这样做会带来一个新问题：如何在多次调用之间传递信息？第一次调用得到的景点信息，如何传递给第二次调用？我们需要手动管理这些中间结果，代码会变得很复杂。

当然，我们可以使用 ReactAgent 来解决这个问题。ReactAgent 可以在一次调用中执行多个工具，它会自动进行多轮思考和行动。但这又带来了新的问题：<strong>时间成本</strong>。ReactAgent 的每一轮思考都需要调用 LLM，如果需要调用三个工具，就需要至少三轮思考，这意味着至少三次 LLM 调用。而且这些调用是串行的，必须等前一个完成才能开始下一个，总时间会很长。

第二个问题是<strong>提示词的复杂度</strong>。如果我们要让一个 Agent 完成所有任务，就需要在提示词中详细描述每个任务的执行逻辑。比如：

```python
COMPLEX_PROMPT = """你是旅行规划助手。你需要：
1. 使用maps_text_search搜索景点，关键词根据用户偏好确定
2. 使用maps_weather查询天气,获取未来几天的天气预报
3. 使用maps_text_search搜索酒店,类型根据用户需求确定
4. 整合所有信息生成旅行计划,包括每天的景点、餐饮、住宿安排
注意：必须按顺序执行,每个工具只能调用一次,输出必须是JSON格式...
"""
```

这样的提示词有几个问题。首先是<strong>难以维护</strong>。如果我们想修改景点搜索的逻辑(比如增加评分筛选)，就需要修改整个提示词，很容易影响到其他部分。其次是<strong>容易出错</strong>。LLM 需要同时理解多个任务的要求，很容易搞混不同任务的格式和参数。最后是<strong>难以调试</strong>。当生成的计划不符合预期时，我们很难知道是哪个环节出了问题，是景点搜索不准确，还是天气查询失败，还是整合逻辑有问题？

面对这些问题，一个自然的想法是：能不能把复杂的任务分解成多个简单的任务，让不同的 Agent 各司其职？这就是多 Agent 协作的核心思想。

想象一下现实世界中的旅行社。当你去旅行社咨询旅行计划时，不会只有一个人为你服务。通常会有专门的景点顾问，负责推荐景点；有酒店顾问，负责预订酒店；还有行程规划师，负责把所有信息整合成完整的行程。每个人都专注于自己擅长的领域，最后由行程规划师把所有信息汇总。这种分工协作的方式，比让一个人做所有事情要高效得多。

### 13.3.2 Agent 角色设计

基于任务分解原则，我们设计了四个专门的 Agent，如图 13.6 所示:

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-6.png" alt="" width="85%"/>
  <p>图 13.6 多智能体协作流程</p>
</div>

- <strong>AttractionSearchAgent(景点搜索专家)</strong>专注于搜索景点信息。它只需要理解用户的偏好(比如"历史文化"、"自然风光")，然后调用高德地图的 POI 搜索工具，返回相关的景点列表。它的提示词很简单，只需要说明如何根据偏好选择关键词，如何调用工具。

- <strong>WeatherQueryAgent(天气查询专家)</strong>专注于查询天气信息。它只需要知道城市名称，然后调用天气查询工具，返回未来几天的天气预报。它的任务非常明确，几乎不会出错。

- <strong>HotelAgent(酒店推荐专家)</strong>专注于搜索酒店信息。它需要理解用户的住宿需求(比如"经济型"、"豪华型")，然后调用 POI 搜索工具，返回符合要求的酒店列表。

- <strong>PlannerAgent(行程规划专家)</strong>负责整合所有信息。它接收前三个 Agent 的输出，加上用户的原始需求(日期、预算等)，然后生成完整的旅行计划。它不需要调用任何外部工具，只需要专注于信息的整合和行程的安排。

现在让我们详细设计每个 Agent 的角色和提示词。设计提示词时，我们需要考虑几个关键问题：这个 Agent 需要什么输入？它应该产生什么输出？它需要调用什么工具？它可能遇到什么问题？

<strong>AttractionSearchAgent</strong>的任务是根据用户偏好搜索景点。它的输入是城市名称和用户偏好(比如"历史文化"、"自然风光")。它需要调用`amap_maps_text_search`工具，参数是关键词和城市。它的输出是景点列表，包含名称、地址、评分等信息。

```python
ATTRACTION_AGENT_PROMPT = """你是景点搜索专家。

**工具调用格式:**
`[TOOL_CALL:amap_maps_text_search:keywords=景点,city=城市名]`

**示例:**
- `[TOOL_CALL:amap_maps_text_search:keywords=景点,city=北京]`
- `[TOOL_CALL:amap_maps_text_search:keywords=博物馆,city=上海]`

**重要:**
- 必须使用工具搜索,不要编造信息
- 根据用户偏好({preferences})搜索{city}的景点
"""
```

这个提示词很简洁，但包含了所有必要的信息。它明确说明了工具调用的格式，提供了具体的示例，还强调了两个重要原则：必须使用工具(不能编造)，要根据用户偏好搜索。

<strong>WeatherQueryAgent</strong>的任务更简单，只需要查询天气。它的输入是城市名称，输出是天气信息。

```python
WEATHER_AGENT_PROMPT = """你是天气查询专家。

**工具调用格式:**
`[TOOL_CALL:amap_maps_weather:city=城市名]`

请查询{city}的天气信息。
"""
```

<strong>HotelAgent</strong>的任务是搜索酒店。它的输入是城市名称和住宿类型，输出是酒店列表。

```python
HOTEL_AGENT_PROMPT = """你是酒店推荐专家。

**工具调用格式:**
`[TOOL_CALL:amap_maps_text_search:keywords=酒店,city=城市名]`

请搜索{city}的{accommodation}酒店。
"""
```

<strong>PlannerAgent</strong>是最复杂的，因为它需要整合所有信息。它的输入是用户需求和前三个 Agent 的输出，输出是完整的旅行计划(JSON 格式)。

```python
PLANNER_AGENT_PROMPT = """你是行程规划专家。

**输出格式:**
严格按照以下JSON格式返回:
{
  "city": "城市名称",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "days": [...],
  "weather_info": [...],
  "overall_suggestions": "总体建议",
  "budget": {...}
}

**规划要求:**
1. weather_info必须包含每天的天气
2. 温度为纯数字(不带°C)
3. 每天安排2-3个景点
4. 考虑景点距离和游览时间
5. 包含早中晚三餐
6. 提供实用建议
7. 包含预算信息
"""
```

### 13.3.3 Agent 协作流程

现在让我们看看这四个 Agent 如何协作完成旅行规划任务。整个流程可以分为五个步骤：

```python
class TripPlannerAgent:
    def __init__(self):
        self.attraction_agent = SimpleAgent(name="景点搜索"prompt=ATTRACTION_PROMPT)
        self.weather_agent = SimpleAgent(name="天气查询", prompt=WEATHER_PROMPT)
        self.hotel_agent = SimpleAgent(name="酒店推荐", prompt=HOTEL_PROMPT)
        self.planner_agent = SimpleAgent(name="行程规划", prompt=PLANNER_PROMPT)

    def plan_trip(self, request: TripPlanRequest) -> TripPlan:
        # 步骤1: 景点搜索
        attraction_response = self.attraction_agent.run(
            f"请搜索{request.city}的{request.preferences}景点"
        )

        # 步骤2: 天气查询
        weather_response = self.weather_agent.run(
            f"请查询{request.city}的天气"
        )

        # 步骤3: 酒店推荐
        hotel_response = self.hotel_agent.run(
            f"请搜索{request.city}的{request.accommodation}酒店"
        )

        # 步骤4: 整合生成计划
        planner_query = self._build_planner_query(
            request, attraction_response, weather_response, hotel_response
        )
        planner_response = self.planner_agent.run(planner_query)

        # 步骤5: 解析JSON
        trip_plan = self._parse_trip_plan(planner_response)
        return trip_plan
```

这个流程顺序执行四个步骤，每个步骤的输出作为下一个步骤的输入。注意我们使用了`TripPlanRequest`和`TripPlan`这两个 Pydantic 模型，这是在 13.2 节中定义的。

### 13.3.4 查询构建

PlannerAgent 需要整合所有信息，这个查询需要包含所有必要的信息，而且要组织得清晰有序，让 LLM 能够准确理解。

```python
def _build_planner_query(
    self,
    request: TripPlanRequest,
    attraction_response: str,
    weather_response: str,
    hotel_response: str
) -> str:
    """构建规划Agent的查询"""
    return f"""
请根据以下信息生成{request.city}的{request.days}日旅行计划:

**用户需求:**
- 目的地: {request.city}
- 日期: {request.start_date} 至 {request.end_date}
- 天数: {request.days}天
- 偏好: {request.preferences}
- 预算: {request.budget}
- 交通方式: {request.transportation}
- 住宿类型: {request.accommodation}

**景点信息:**
{attraction_response}

**天气信息:**
{weather_response}

**酒店信息:**
{hotel_response}

请生成详细的旅行计划,包括每天的景点安排、餐饮推荐、住宿信息和预算明细。
"""
```

通过这种多 Agent 协作的设计，我们把一个复杂的旅行规划任务分解成了四个简单的子任务。每个 Agent 都专注于自己擅长的领域，也为未来的功能扩展(比如添加餐厅推荐 Agent、交通规划 Agent)打下了良好的基础。

## 13.4 MCP 工具集成详解

### 13.4.1 为什么不直接调用 API

在 13.3 节中，我们设计了四个 Agent 来协作完成旅行规划任务。其中 AttractionSearchAgent、WeatherQueryAgent 和 HotelAgent 都需要调用高德地图的 API 来获取数据。一个自然的问题是：为什么不直接在 Agent 中调用高德地图的 HTTP API？

让我们先看看直接调用 API 会是什么样子。高德地图提供了 POI 搜索 API，我们需要构造 HTTP 请求，传递参数，解析响应：

```python
import requests

def search_poi(keywords: str,city: str,api_key: str):
    """直接调用高德地图POI搜索API"""
    url = "https://restapi.amap.com/v3/place/text"
    params = {
        "keywords": keywords,
        "city": city,
        "key": api_key,
        "output": "json"
    }
    response = requests.get(url,params=params)
    data = response.json()
    return data
```

这种方式看起来很简单，但在实际使用中会遇到几个问题。首先是<strong>Agent 无法自主调用</strong>。在我们的 HelloAgents 框架中，Agent 通过识别提示词中的工具调用标记(比如`[TOOL_CALL:tool_name:arg1=value1]`)来调用工具。如果我们直接在代码中调用 API，Agent 就失去了自主决策的能力，变成了一个简单的函数调用。

其次是<strong>参数传递复杂</strong>。高德地图的 API 有很多参数，比如 POI 搜索有`keywords`、`city`、`types`、`offset`、`page`等十几个参数。如果我们要让 Agent 能够灵活使用这些参数，就需要在提示词中详细说明每个参数的含义和格式，这会让提示词变得非常复杂。

第三是<strong>响应解析困难</strong>。高德地图 API 返回的是 JSON 格式的数据，结构比较复杂。我们需要编写代码来解析这些数据，提取我们需要的字段。如果 API 的响应格式发生变化，我们就需要修改解析代码。

最后是<strong>工具管理混乱</strong>。高德地图提供了十几个不同的 API(POI 搜索、天气查询、路线规划等)，如果我们为每个 API 都编写一个函数，然后手动注册到 Agent 的工具列表中，代码会变得很冗长。而且当我们想添加新的 API 时，需要修改多个地方。

### 13.4.2 高德地图 MCP 集成

MCP(Model Context Protocol)是 Anthropic 提出的标准化协议，用于连接 LLM 和外部工具。本节将介绍如何在项目中集成高德地图 MCP 服务器。我们的项目用的是`amap-mcp-server`，这是一个用 Node.js 实现的 MCP 服务器：

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-7.png" alt="" width="85%"/>
  <p>图 13.7 amap-mcp-server 工具</p>
</div>

高德地图 MCP 服务器提供了多种工具，主要分为以下类别，如表 13.1 所示:

<div align="center">
  <p>表 13.1 高德地图 MCP 工具分类</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-table-1.png" alt="" width="85%"/>
</div>

通过 MCP 协议，我们可以很方便地在 HelloAgents 中集成:

```python
from hello_agents.tools import MCPTool
from app.config import get_settings

settings = get_settings()

# 创建MCP工具
mcp_tool = MCPTool(
    name="amap_mcp",
    command="npx",
    args=["-y", "@sugarforever/amap-mcp-server"],
    env={"AMAP_API_KEY": settings.amap_api_key},
    auto_expand=True
)
```

这段代码做了什么呢？首先，`command`和`args`指定了如何启动 MCP 服务器。`npx -y @sugarforever/amap-mcp-server`会从 npm 仓库下载并运行`amap-mcp-server`这个包。`env`参数传递了环境变量，这里我们传递了高德地图的 API 密钥。

**注意：**本文档中部分示例使用 `npx` 启动 MCP（Model Context Protocol）服务。而在本节代码仓中，我们实际采用的是 `uvx` 方式。需要说明的是，`npx` 和 `uvx` 在设计理念上高度一致，区别仅在于所处的生态系统，`npx` 面向 JavaScript/Node.js（包来自 npm），而`uvx` 面向 Python（包来自 PyPI）。两种方式并无优劣之分，请大家在使用时按需进行选择。

当我们创建`MCPTool`对象时，它会在后台启动 MCP 服务器进程，并通过标准输入输出(stdin/stdout)与服务器通信。这是 MCP 协议的一个特点：使用进程间通信而不是 HTTP，这样更高效，也更容易管理。

最关键的是`auto_expand=True`这个参数。当设置为 True 时，`MCPTool`会自动查询 MCP 服务器提供了哪些工具，然后为每个工具创建一个独立的 Tool 对象。这就是为什么我们只创建了一个`MCPTool`，但 Agent 却获得了 16 个工具。让我们看看这个过程：

```python
# 创建一个MCPTool
mcp_tool = MCPTool(..., auto_expand=True)
agent.add_tool(mcp_tool)

# Agent实际上获得了16个工具！
print(list(agent.tools.keys()))
# ['amap_maps_text_search', 'amap_maps_weather', ...]
```

如图 13.8 所示，假设用户想搜索北京的景点，AttractionSearchAgent 接收到查询"请搜索北京的历史文化景点"。Agent 分析这个查询，决定调用`amap_maps_text_search`工具，参数是`keywords=景点，city=北京`。

<div align="center">
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-8.png" alt="" width="85%"/>
  <p>图 13.8 MCP 工具调用流程</p>
</div>

Agent 生成工具调用标记：`[TOOL_CALL:amap_maps_text_search:keywords=景点，city=北京]`。HelloAgents 框架解析这个标记，提取工具名称和参数，然后调用对应的 Tool 对象。

Tool 对象是`MCPTool`自动创建的，它会把调用请求发送给 MCP 服务器。具体来说，它会构造一个 JSON-RPC 格式的消息，通过 stdin 发送给服务器进程：

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "amap_maps_text_search",
    "arguments": {
      "keywords": "景点",
      "city": "北京"
    }
  }
}
```

MCP 服务器接收到这个消息，解析参数，然后调用高德地图的 HTTP API。它会构造 HTTP 请求，添加 API 密钥，发送请求，接收响应。

高德地图 API 返回 JSON 格式的数据，包含景点列表、地址、坐标等信息。MCP 服务器解析这些数据，提取关键字段，然后构造响应消息，通过 stdout 返回给`MCPTool`：

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "找到以下景点：\n1. 故宫博物院 - 地址：东城区景山前街4号\n2. 天坛公园 - 地址：东城区天坛路\n..."
      }
    ]
  }
}
```

`MCPTool`接收到响应，提取文本内容，返回给 Agent。Agent 把这个结果作为工具调用的输出，继续生成最终的回复。

这个流程看起来很复杂，但对于 Agent 来说，它只需要知道有一个叫`amap_maps_text_search`的工具，可以搜索景点。所有的底层细节都被 MCP 协议和`MCPTool`封装起来了。

### 13.4.3 共享 MCP 实例

在我们的多 Agent 系统中，有三个 Agent 都需要使用高德地图的工具。那么每个 Agent 应该创建自己的`MCPTool`实例，还是共享同一个实例？

如果每个 Agent 都创建一个`MCPTool`实例，这意味着会有三个服务器进程同时运行。每个进程都会独立地调用高德地图 API，这可能会超过 API 的速率限制。而且多个进程会占用更多的内存和 CPU 资源。

更好的做法是让所有 Agent 共享同一个`MCPTool`实例。这样只需要启动一个 MCP 服务器进程，所有的 API 调用都通过这个进程进行。这不仅节省资源，还可以更好地控制 API 调用频率。

在代码中，我们在`TripPlannerAgent`的构造函数中创建一个`MCPTool`实例，然后把它添加到每个子 Agent 的工具列表中：

```python
class TripPlannerAgent:
    def __init__(self):
        settings = get_settings()
        self.llm = HelloAgentsLLM()

        # 创建共享的MCP工具实例(只创建一次)
        self.mcp_tool = MCPTool(
            name="amap_mcp",
            command="npx",
            args=["-y", "@sugarforever/amap-mcp-server"],
            env={"AMAP_API_KEY": settings.amap_api_key},
            auto_expand=True
        )

        # 创建多个Agent,共享同一个MCP工具
        self.attraction_agent = SimpleAgent(
            name="AttractionSearchAgent",
            llm=self.llm,
            system_prompt=ATTRACTION_AGENT_PROMPT
        )
        self.attraction_agent.add_tool(self.mcp_tool)  # 共享

        self.weather_agent = SimpleAgent(
            name="WeatherQueryAgent",
            llm=self.llm,
            system_prompt=WEATHER_AGENT_PROMPT
        )
        self.weather_agent.add_tool(self.mcp_tool)  # 共享

        self.hotel_agent = SimpleAgent(
            name="HotelAgent",
            llm=self.llm,
            system_prompt=HOTEL_AGENT_PROMPT
        )
        self.hotel_agent.add_tool(self.mcp_tool)  # 共享
```

这样，三个 Agent 都可以使用高德地图的 16 个工具，但底层只有一个 MCP 服务器进程在运行。当我们调用`TripPlannerAgent`的`plan_trip`方法时，三个 Agent 会依次调用工具，所有的请求都通过同一个 MCP 服务器发送到高德地图 API。

### 13.4.4 Unsplash 图片 API 集成

除了高德地图，我们还需要为景点获取图片，让旅行计划更加生动直观。我们使用 Unsplash API 来搜索景点图片。需要注意的是，Unsplash 是国外的服务，而且是为数不多可以免费使用的图片 API，所以搜索结果可能不够准确。在实际项目中，可以考虑使用必应、百度或高德的 POI 图片 API，但这些服务通常需要付费。

Unsplash API 的集成比较简单，我们创建一个`UnsplashService`类来封装 API 调用：

```python
# backend/app/services/unsplash_service.py
import requests
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)

class UnsplashService:
    """Unsplash图片服务"""

    def __init__(self, access_key: str):
        self.access_key = access_key
        self.base_url = "https://api.unsplash.com"

    def search_photos(self, query: str, per_page: int = 10) -> List[Dict]:
        """搜索图片"""
        try:
            url = f"{self.base_url}/search/photos"
            params = {
                "query": query,
                "per_page": per_page,
                "client_id": self.access_key
            }

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            # 提取图片URL
            photos = []
            for result in results:
                photos.append({
                    "url": result["urls"]["regular"],
                    "description": result.get("description", ""),
                    "photographer": result["user"]["name"]
                })

            return photos

        except Exception as e:
            logger.error(f"搜索图片失败: {e}")
            return []

    def get_photo_url(self, query: str) -> Optional[str]:
        """获取单张图片URL"""
        photos = self.search_photos(query, per_page=1)
        return photos[0].get("url") if photos else None
```

这个服务类提供了两个方法：`search_photos`搜索多张图片，`get_photo_url`获取单张图片的 URL。我们在 API 路由中使用这个服务，为每个景点获取图片：
```python
# backend/app/api/routes/trip.py
from app.services.unsplash_service import UnsplashService

unsplash_service = UnsplashService(settings.unsplash_access_key)

@router.post("/plan", response_model=TripPlan)
async def create_trip_plan(request: TripPlanRequest) -> TripPlan:
    # 生成旅行计划
    trip_plan = trip_planner_agent.plan_trip(request)

    # 为每个景点获取图片
    for day in trip_plan.days:
        for attraction in day.attractions:
            if not attraction.image_url:
                image_url = unsplash_service.get_photo_url(
                    f"{attraction.name} {trip_plan.city}"
                )
                attraction.image_url = image_url

    return trip_plan
```

注意我们没有把 Unsplash 封装成 Tool 或 MCP 工具，而是直接在 API 路由中调用。这是因为图片搜索不需要 Agent 的智能决策，只是一个简单的数据增强步骤。如果你想让 Agent 能够自主决定是否需要图片，或者选择不同的图片来源，可以考虑把它封装成 Tool。

## 13.5 前端开发详解

### 13.5.1 前后端分离的 Web 架构

在开始前端开发之前，我们需要理解现代 Web 应用的架构模式。在早期的 Web 开发中，前端和后端是混在一起的，比如 PHP、JSP 这样的技术，HTML 模板和业务逻辑代码写在同一个文件里。这种方式在小项目中很方便，但在大型项目中会遇到很多问题：前端和后端开发者需要频繁协调，代码难以复用，测试困难。

现代 Web 应用普遍采用<strong>前后端分离</strong>的架构。后端只负责提供 API 接口，返回 JSON 格式的数据。前端是一个独立的应用，通过 HTTP 请求调用后端 API，获取数据后渲染页面。这种架构有几个明显的优势：前端和后端可以独立开发、独立部署、独立测试；前端可以是 Web 应用、移动应用或桌面应用，都使用同一套后端 API；前端可以使用现代的框架和工具链，提供更好的用户体验。

在我们的智能旅行助手项目中，后端是用 Python 和 FastAPI 实现的，提供了一个核心 API 接口`POST /api/trip/plan`，接收旅行需求，返回旅行计划。前端是用 Vue 3 和 TypeScript 实现的，是一个单页应用(SPA)，用户在浏览器中填写表单，点击"开始规划"按钮，前端发送 HTTP 请求到后端，等待响应，然后渲染结果页面。整个过程中，页面不会刷新，用户体验很流畅。

前端技术栈的选择需要考虑几个因素：开发效率、性能、生态系统、学习曲线。如表 13.2 所示，该项目选择了以下技术栈：

<div align="center">
  <p>表 13.2 前端技术栈</p>
  <img src="https://raw.githubusercontent.com/datawhalechina/Hello-Agents/main/docs/images/13-figures/13-table-2.png" alt="" width="85%"/>
</div>

项目的目录结构是这样的：
```
frontend/
├── src/
│   ├── views/              # 页面组件
│   │   ├── Home.vue        # 首页(表单)
│   │   └── Result.vue      # 结果页
│   ├── services/           # API服务
│   │   └── api.ts
│   ├── types/              # 类型定义
│   │   └── index.ts
│   ├── router/             # 路由配置
│   │   └── index.ts
│   ├── App.vue
│   └── main.ts
├── package.json
├── vite.config.ts
└── tsconfig.json
```

其中`views`目录存放页面组件，`services`目录存放 API 调用逻辑，`types`目录存放 TypeScript 类型定义，`router`目录存放路由配置。

### 13.5.2 类型定义

在 13.2 节中，我们在后端使用 Pydantic 定义了数据模型，比如`Location`、`Attraction`、`DayPlan`、`TripPlan`等。在前端，我们需要定义对应的 TypeScript 类型。

让我们看看如何定义这些类型。首先是最基础的`Location`类型，表示经纬度坐标：

```typescript
// frontend/src/types/index.ts
export interface Location {
  longitude: number
  latitude: number
}
```

这个类型定义和后端的 Pydantic 模型完全对应。注意 TypeScript 使用`interface`关键字定义类型，字段类型用冒号分隔，不需要默认值。

接下来是`Attraction`类型，表示景点信息：

```typescript
export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number
  description: string
  category?: string
  rating?: number
  image_url?: string
  ticket_price?: number
}
```

注意这里使用了`Location`类型作为字段类型，这就是嵌套类型。问号`?`表示可选字段，对应后端 Pydantic 模型中的`Optional`。

类似地，我们定义`Meal`、`Hotel`、`Budget`、`WeatherInfo`等类型。最后是顶层的`TripPlan`类型：

```typescript
export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget?: Budget
}
```

还有请求类型`TripPlanRequest`，对应后端的请求模型：

```typescript
export interface TripPlanRequest {
  city: string
  start_date: string
  end_date: string
  days: number
  preferences: string
  budget: string
  transportation: string
  accommodation: string
}
```

这些类型定义有什么用呢？首先，当我们调用 API 时，TypeScript 会检查我们传递的数据是否符合`TripPlanRequest`类型。如果我们不小心把`days`写成了字符串，TypeScript 会立即报错。其次，当我们接收 API 响应时，TypeScript 会检查响应数据是否符合`TripPlan`类型。如果后端返回的数据结构发生变化，前端会立即发现。最后，IDE 可以根据类型定义提供代码补全，我们输入`tripPlan.`时，IDE 会自动列出所有可用的字段。

### 13.5.3 API 服务封装

有了类型定义，我们就可以封装 API 调用了。我们创建一个`api.ts`文件，使用 Axios 来发送 HTTP 请求：

```typescript
import axios from 'axios'
import type { TripPlanRequest,TripPlan } from '../types'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 120000, // 2分钟超时
  headers: {
    'Content-Type': 'application/json'
  }
})
```

这里我们创建了一个 Axios 实例，配置了基础 URL、超时时间和请求头。为什么超时时间设置为 2 分钟？因为生成旅行计划需要调用多个 Agent，每个 Agent 都要调用 LLM 和外部 API，整个过程可能需要 10-30 秒。如果超时时间太短，请求会被中断。

接下来我们添加拦截器。拦截器可以在请求发送前和响应接收后执行一些通用逻辑，比如日志记录、错误处理、认证等：

```typescript
// 请求拦截器
api.interceptors.request.use(
  config => {
    console.log('发送请求：',config)
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    console.log('收到响应：',response)
    return response
  },
  error => {
    console.error('请求失败：',error)
    return Promise.reject(error)
  }
)
```

最后我们定义 API 函数，这是前端调用后端的唯一入口：

```typescript
// 生成旅行计划
export const generateTripPlan = async (request: TripPlanRequest): Promise<TripPlan> => {
  const response = await api.post<TripPlan>('/trip/plan',request)
  return response.data
}
```

注意这个函数的类型签名：参数是`TripPlanRequest`类型，返回值是`Promise<TripPlan>`类型。这意味着 TypeScript 会检查调用者传递的参数是否符合要求，也会检查返回值的使用是否正确。

### 13.5.4 Home 表单设计

Home 页面是用户的入口，包含一个表单，让用户填写旅行需求。我们使用 Vue 3 的 Composition API 来组织代码：

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { generateTripPlan } from '@/services/api'
import type { TripPlanRequest } from '@/types'

const router = useRouter()
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const formData = ref<TripPlanRequest>({
  city: '',
  start_date: '',
  end_date: '',
  days: 3,
  preferences: '历史文化',
  budget: '中等',
  transportation: '公共交通',
  accommodation: '经济型酒店'
})
</script>
```

这里我们使用`ref`来创建响应式变量。`formData`是表单数据，类型是`TripPlanRequest`。`loading`表示是否正在加载，`loadingProgress`表示加载进度，`loadingStatus`表示加载状态文本。

表单提交的逻辑是这样的：

```typescript
const handleSubmit = async () => {
  loading.value = true
  loadingProgress.value = 0
  
  // 模拟进度更新
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
      if (loadingProgress.value <= 30) loadingStatus.value = '🔍 正在搜索景点...'
      else if (loadingProgress.value <= 50) loadingStatus.value = '🌤️ 正在查询天气...'
      else if (loadingProgress.value <= 70) loadingStatus.value = '🏨 正在推荐酒店...'
      else loadingStatus.value = '📋 正在生成行程计划...'
    }
  },500)
  
  try {
    const response = await generateTripPlan(formData.value)
    clearInterval(progressInterval)
    loadingProgress.value = 100
    router.push({ name: 'result',state: { tripPlan: response } })
  } catch (error) {
    clearInterval(progressInterval)
    message.error('生成计划失败,请重试')
  } finally {
    loading.value = false
  }
}
```

这段代码做了几件事。首先，设置`loading`为 true，显示加载状态。然后，启动一个定时器，每 500 毫秒更新一次进度条和状态文本。这是一个模拟的进度，因为我们无法准确知道后端的处理进度。但这样可以让用户知道系统正在工作，而不是卡住了。

接着，调用`generateTripPlan`函数发送 API 请求。这是一个异步操作，我们使用`await`等待响应。如果请求成功，清除定时器，设置进度为 100%，然后跳转到结果页面，并把旅行计划数据传递过去。如果请求失败，显示错误消息。最后，无论成功还是失败，都设置`loading`为 false，隐藏加载状态。

模板部分使用 Ant Design Vue 的组件：

```vue
<template>
  <div class="home-container">
    <div class="page-header">
      <h1 class="page-title">✈️ 智能旅行助手</h1>
      <p class="page-subtitle">基于AI的个性化旅行规划</p>
    </div>
    
    <a-card class="form-card">
      <a-form :model="formData" @finish="handleSubmit">
        <a-form-item label="目的地城市" name="city" :rules="[{ required: true }]">
          <a-input v-model:value="formData.city" placeholder="如：北京" />
        </a-form-item>
        
        <!-- 更多表单项... -->
        
        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" :loading="loading">
            开始规划
          </a-button>
        </a-form-item>
        
        <!-- 加载进度条 -->
        <a-form-item v-if="loading">
          <a-progress :percent="loadingProgress" status="active" />
          <p>{{ loadingStatus }}</p>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>
```

注意`v-model:value`指令，它实现了双向数据绑定。当用户在输入框中输入内容时，`formData.city`会自动更新。当`formData.city`的值改变时，输入框的内容也会自动更新。

### 13.5.5 Result 页面展示

Result 页面是整个应用的核心，展示生成的旅行计划。这个页面包含几个部分：行程概览、预算明细、地图可视化、每日行程详情、天气信息。

首先是地图可视化。我们使用高德地图 JS API 在地图上标注景点位置：

```typescript
import AMapLoader from '@amap/amap-jsapi-loader'

const initMap = async () => {
  const AMap = await AMapLoader.load({
    key: 'your_amap_web_key',
    version: '2.0'
  })
  
  map = new AMap.Map('amap-container',{
    zoom: 12,
    center: [116.397128,39.916527]
  })
  
  // 添加景点标记
  tripPlan.value.days.forEach((day) => {
    day.attractions.forEach((attraction,index) => {
      const marker = new AMap.Marker({
        position: [attraction.location.longitude,attraction.location.latitude],
        title: attraction.name,
        label: { content: `${index + 1}`,direction: 'top' }
      })
      map.add(marker)
    })
  })
}
```

这段代码首先加载高德地图 SDK，然后创建地图实例，最后遍历所有景点，为每个景点创建一个标记(Marker)。标记的位置是景点的经纬度坐标，这些坐标是从后端的`Attraction`对象中获取的。

导出功能使用`html2canvas`和`jsPDF`库。`html2canvas`可以把 DOM 元素转换成 Canvas，然后我们可以把 Canvas 导出为图片或 PDF：

```typescript
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'

// 导出为图片
const exportAsImage = async () => {
  const element = document.getElementById('trip-plan-content')
  const canvas = await html2canvas(element,{ scale: 2 })
  const link = document.createElement('a')
  link.download = `${tripPlan.value.city}旅行计划.png`
  link.href = canvas.toDataURL()
  link.click()
}

// 导出为PDF
const exportAsPDF = async () => {
  const element = document.getElementById('trip-plan-content')
  const canvas = await html2canvas(element,{ scale: 2 })
  const imgData = canvas.toDataURL('image/png')
  const pdf = new jsPDF('p','mm','a4')
  const imgWidth = 210
  const imgHeight = (canvas.height * imgWidth) / canvas.width
  pdf.addImage(imgData,'PNG',0,0,imgWidth,imgHeight)
  pdf.save(`${tripPlan.value.city}旅行计划.pdf`)
}
```

通过这些前端技术，我们实现了一个完整的 Web 应用。用户可以在浏览器中填写表单，提交请求，等待 AI 生成旅行计划，然后查看详细的行程安排，在地图上看到景点位置，还可以导出为图片或 PDF。整个过程流畅自然，这就是现代 Web 应用的魅力。

## 13.6 功能实现详解

本节介绍智能旅行助手的核心功能实现，包括预算计算、加载进度条、行程编辑、导出功能和侧边导航。

### 13.6.1 预算计算功能

在规划旅行时，预算是一个非常重要的考虑因素。用户需要知道这次旅行大概要花多少钱，钱都花在哪里。我们的智能旅行助手提供了自动预算计算功能，将费用分为四大类：景点门票、酒店住宿、餐饮和交通。

预算计算的逻辑在哪里实现呢？我们选择在后端的 PlannerAgent 中实现。为什么不在前端计算？因为预算的估算需要基于景点的门票价格、酒店的价格范围、餐饮的标准等信息，这些信息都是 PlannerAgent 在生成行程时已经获取的。如果在前端计算，就需要重复这些逻辑，而且可能不准确。

在 PlannerAgent 的提示词中，我们明确要求 LLM 生成预算信息：

```python
PLANNER_AGENT_PROMPT = """
你是行程规划专家。

**输出格式：**
严格按照以下JSON格式返回：
{
  ...
  "budget": {
    "total_attractions": 180,
    "total_hotels": 1200,
    "total_meals": 480,
    "total_transportation": 200,
    "total": 2060
  }
}

**规划要求：**
...
7. 包含预算信息,根据景点门票、酒店价格、餐饮标准和交通方式估算
"""
```

LLM 会根据行程中的景点、酒店、餐饮安排，估算每一项的费用。比如，如果行程中包含故宫(门票 60 元)、天坛(门票 15 元)、颐和园(门票 30 元)，那么景点门票总费用就是 105 元。如果是 3 天 2 晚的行程，酒店是经济型(每晚 300 元)，那么酒店总费用就是 600 元。

在前端，我们使用 Ant Design Vue 的 Statistic 组件来展示预算信息。这个组件专门用于展示统计数据,支持数字动画、前缀后缀、自定义样式等：

```vue
<a-card v-if="tripPlan.budget" title="💰 预算明细">
  <a-row :gutter="16">
    <a-col :span="6">
      <a-statistic title="景点门票" :value="tripPlan.budget.total_attractions" suffix="元" />
    </a-col>
    <a-col :span="6">
      <a-statistic title="酒店住宿" :value="tripPlan.budget.total_hotels" suffix="元" />
    </a-col>
    <a-col :span="6">
      <a-statistic title="餐饮费用" :value="tripPlan.budget.total_meals" suffix="元" />
    </a-col>
    <a-col :span="6">
      <a-statistic title="交通费用" :value="tripPlan.budget.total_transportation" suffix="元" />
    </a-col>
  </a-row>
  <a-divider />
  <a-row>
    <a-col :span="24" style="text-align: center;">
      <a-statistic
        title="预估总费用"
        :value="tripPlan.budget.total"
        suffix="元"
        :value-style="{ color: '#cf1322',fontSize: '32px',fontWeight: 'bold' }"
      />
    </a-col>
  </a-row>
</a-card>
```

这段代码使用了栅格布局(`a-row`和`a-col`)，将四项费用并排显示。每项费用使用一个`a-statistic`组件，显示标题和数值。最后用一个分隔线(`a-divider`)隔开，下面显示总费用，使用红色大字体突出显示。

注意`v-if="tripPlan.budget"`这个条件渲染。因为预算信息是可选的(在 Pydantic 模型中定义为`Optional[Budget]`)，如果 LLM 没有生成预算信息，这个卡片就不会显示。这体现了前端对数据的容错处理。

### 13.6.2 加载进度条

生成旅行计划是一个耗时的操作。后端需要依次调用 AttractionSearchAgent、WeatherQueryAgent、HotelAgent 和 PlannerAgent，每个 Agent 都要调用 LLM 和外部 API。整个过程可能需要 10-30 秒。如果用户点击"开始规划"按钮后，页面没有任何反馈，用户会以为系统卡住了，可能会刷新页面或重复点击。

为了提升用户体验，我们添加了加载进度条和状态提示。现在只是模拟进度，可以让用户知道系统正在工作。

```typescript
const loading = ref(false)
const loadingProgress = ref(0)
const loadingStatus = ref('')

const handleSubmit = async () => {
  loading.value = true
  loadingProgress.value = 0

  // 模拟进度更新
  const progressInterval = setInterval(() => {
    if (loadingProgress.value < 90) {
      loadingProgress.value += 10
      if (loadingProgress.value <= 30) loadingStatus.value = '🔍 正在搜索景点...'
      else if (loadingProgress.value <= 50) loadingStatus.value = '🌤️ 正在查询天气...'
      else if (loadingProgress.value <= 70) loadingStatus.value = '🏨 正在推荐酒店...'
      else loadingStatus.value = '📋 正在生成行程计划...'
    }
  }, 500)

  try {
    const response = await generateTripPlan(formData.value)
    clearInterval(progressInterval)
    loadingProgress.value = 100
    loadingStatus.value = '✅ 完成！'
    router.push({ name: 'result', state: { tripPlan: response } })
  } catch (error) {
    clearInterval(progressInterval)
    message.error('生成计划失败')
  } finally {
    loading.value = false
  }
}
```

### 13.6.3 行程编辑功能

AI 生成的旅行计划虽然很智能，但可能不完全符合用户的个人需求。比如，用户可能不喜欢某个景点，想删除它；或者想调整景点的游览顺序。我们提供了行程编辑功能，让用户可以自定义行程。

编辑功能的核心是<strong>状态管理</strong>。我们需要维护两个状态：当前的行程计划和原始的行程计划。当用户进入编辑模式时，我们保存原始计划的副本。如果用户取消编辑，就恢复原始计划。如果用户保存修改，就更新当前计划：

```typescript
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)

// 进入编辑模式
const toggleEditMode = () => {
  editMode.value = true
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
}
```

注意这里使用了`JSON.parse(JSON.stringify(...))`来深拷贝对象。为什么不直接赋值？因为 JavaScript 中对象是引用类型，如果直接赋值，`originalPlan`和`tripPlan`会指向同一个对象，修改一个会影响另一个。深拷贝可以创建一个完全独立的副本。

移动景点的逻辑是交换数组中两个元素的位置：

```typescript
// 移动景点
const moveAttraction = (dayIndex: number,attractionIndex: number,direction: 'up' | 'down') => {
  const attractions = tripPlan.value.days[dayIndex].attractions
  const newIndex = direction === 'up' ? attractionIndex - 1 : attractionIndex + 1
  
  if (newIndex >= 0 && newIndex < attractions.length) {
    [attractions[attractionIndex],attractions[newIndex]] = 
    [attractions[newIndex],attractions[attractionIndex]]
  }
}
```

这里使用了 ES6 的解构赋值语法来交换两个元素。`[a,b] = [b,a]`是一个很优雅的交换方式，不需要临时变量。

删除景点使用数组的`splice`方法：

```typescript
// 删除景点
const deleteAttraction = (dayIndex: number,attractionIndex: number) => {
  tripPlan.value.days[dayIndex].attractions.splice(attractionIndex,1)
}
```

保存修改时，我们需要重新初始化地图，因为景点的位置可能发生了变化：

```typescript
// 保存修改
const saveChanges = () => {
  editMode.value = false
  message.success('修改已保存')
  initMap()  // 重新初始化地图
}

// 取消编辑
const cancelEdit = () => {
  if (originalPlan.value) {
    tripPlan.value = originalPlan.value
  }
  editMode.value = false
}
```

在模板中，我们根据`editMode`的值显示不同的 UI。编辑模式下，每个景点旁边会显示上移、下移、删除按钮：

```vue
<div v-if="editMode" class="edit-buttons">
  <a-button size="small" @click="moveAttraction(dayIndex,index,'up')">上移</a-button>
  <a-button size="small" @click="moveAttraction(dayIndex,index,'down')">下移</a-button>
  <a-button size="small" danger @click="deleteAttraction(dayIndex,index)">删除</a-button>
</div>
```

### 13.6.4 导出功能

用户生成了满意的旅行计划后，可能想保存下来或分享给朋友。我们提供了两种导出方式：导出为图片和导出为 PDF。

导出功能的核心是`html2canvas`库。这个库可以把 DOM 元素转换成 Canvas，然后我们可以把 Canvas 导出为图片。但这里有一个技术难点：地图是用 Canvas 渲染的，而`html2canvas`在处理嵌套 Canvas 时存在兼容性问题。

我们尝试了多种解决方案，包括将地图 Canvas 转换成图片后再导出，但由于高德地图的 Canvas 渲染机制和跨域限制，这个方案并没有完全解决问题。在实际项目中，可能需要考虑以下替代方案：

1. <strong>使用高德地图的静态地图 API</strong>：调用`maps_staticmap`工具生成静态地图图片，替代动态地图
2. <strong>分开导出</strong>：地图和行程内容分开导出，最后在后端合并
3. <strong>使用截图服务</strong>：使用 Puppeteer 等无头浏览器在服务端截图
4. <strong>简化导出内容</strong>：导出时隐藏地图，只导出文字内容

目前的实现中，我们采用了简化方案，在导出时暂时隐藏地图部分，只导出行程的文字内容和景点信息。虽然这不是最理想的方案，但可以保证导出功能的可用性。

导出为图片的逻辑很简单：

```typescript
import html2canvas from 'html2canvas'

const exportAsImage = async () => {
  const element = document.getElementById('trip-plan-content')
  if (!element) return
  
  const canvas = await html2canvas(element,{
    backgroundColor: '#ffffff',
    scale: 2,
    useCORS: true
  })
  
  const link = document.createElement('a')
  link.download = `${tripPlan.value.city}旅行计划.png`
  link.href = canvas.toDataURL('image/png')
  link.click()
  message.success('导出成功！')
}
```

`scale: 2`表示使用 2 倍分辨率，这样导出的图片更清晰。`useCORS: true`允许跨域加载图片，这对于景点图片(来自 Unsplash)很重要。

导出为 PDF 需要额外的步骤：先转换成 Canvas，再转换成图片，最后添加到 PDF 中：

```typescript
import jsPDF from 'jspdf'

const exportAsPDF = async () => {
  // 先截取地图
  await captureMapImage()
  
  const element = document.getElementById('trip-plan-content')
  if (!element) return
  
  const canvas = await html2canvas(element,{
    backgroundColor: '#ffffff',
    scale: 2,
    useCORS: true,
    allowTaint: true
  })
  
  // 恢复地图
  restoreMap()
  
  const pdf = new jsPDF('p','mm','a4')
  const imgData = canvas.toDataURL('image/png')
  const imgWidth = 210  // A4宽度
  const imgHeight = (canvas.height * imgWidth) / canvas.width
  
  pdf.addImage(imgData,'PNG',0,0,imgWidth,imgHeight)
  pdf.save(`${tripPlan.value.city}旅行计划.pdf`)
  message.success('导出成功！')
}
```

这里需要计算图片的高度，保持宽高比。A4 纸的宽度是 210mm，我们根据 Canvas 的宽高比计算出对应的高度。

### 13.6.5 侧边导航与锚点跳转

Result 页面的内容很多，包括行程概览、预算明细、地图、每日行程、天气信息等。如果用户想快速跳转到某个部分，需要滚动很长的距离。我们提供了侧边导航和锚点跳转功能，让用户可以快速定位。

侧边导航使用 Ant Design Vue 的 Menu 组件：

```vue
<a-menu
  v-model:selectedKeys="[activeSection]"
  mode="inline"
  @click="scrollToSection"
>
  <a-menu-item key="overview">📋 行程概览</a-menu-item>
  <a-menu-item key="budget">💰 预算明细</a-menu-item>
  <a-menu-item key="map">🗺️ 地图</a-menu-item>
  <a-menu-item key="days">📅 每日行程</a-menu-item>
  <a-menu-item key="weather">🌤️ 天气</a-menu-item>
</a-menu>
```

点击菜单项时，调用`scrollToSection`函数：

```typescript
const activeSection = ref('overview')

// 滚动到指定区域
const scrollToSection = ({ key }: { key: string }) => {
  activeSection.value = key
  const element = document.getElementById(key)
  if (element) {
    element.scrollIntoView({ behavior: 'smooth',block: 'start' })
  }
}
```

`scrollIntoView`是浏览器原生的 API，可以让元素滚动到可视区域。`behavior: 'smooth'`表示平滑滚动，而不是瞬间跳转。`block: 'start'`表示元素的顶部对齐到可视区域的顶部。

在页面的各个部分，我们需要添加对应的 id：

```vue
<div id="overview">
  <!-- 行程概览内容 -->
</div>

<div id="budget">
  <!-- 预算明细内容 -->
</div>

<div id="map">
  <!-- 地图内容 -->
</div>
```

这样，当用户点击侧边导航的某个菜单项时，页面会平滑滚动到对应的部分。

通过这些功能的实现，我们的智能旅行助手不仅能够生成旅行计划，还提供了丰富的交互功能：预算计算让用户了解费用，加载进度条让等待不再焦虑，行程编辑让计划更符合个人需求，导出功能让计划可以分享和保存，侧边导航让长页面易于浏览。这些功能的组合，构成了一个完整、易用、实用的 Web 应用。

## 13.7 结语

恭喜你完成了第十三章的学习！

通过本章，你不仅学会了如何构建一个完整的智能旅行助手应用，更重要的是掌握了：

1. <strong>系统设计思维</strong>： 如何将复杂问题分解为多个简单任务
2. <strong>工程实践能力</strong>： 如何将理论知识转化为可运行的代码
3. <strong>全栈开发能力</strong>： 如何整合前后端技术栈
4. <strong>AI 应用开发</strong>： 如何利用 LLM 构建实用的应用

这个项目是一个起点，而不是终点。你可以基于这个项目：

- 添加更多功能
- 优化用户体验
- 扩展到其他领域(如智能购物助手、智能学习助手等)
- 部署到生产环境，服务真实用户

最好的学习方式是实践。不要只是阅读代码，而是要动手修改、扩展、优化。每一次实践都会让你对多 Agent 系统有更深的理解。

祝你在 AI 应用开发的道路上越走越远！

