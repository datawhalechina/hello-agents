# Web Agent 科普与实战——让 AI 学会"上网"

## 引言：当 AI 学会浏览网页

想象一下这样的场景：你对着 AI 说"帮我在主流旅行网站上找出下周二从北京飞新加坡、价格在 3000 元以内的三个直飞航班，对比之后用我保存的信用卡订下最划算的那个"——然后 AI 真的打开了一个浏览器，自主导航预订流程，处理路上的各种弹窗与验证页，填写乘客信息，最终把订单确认号交到你手上。

这并不是科幻，而是 **Web Agent（网页智能体）** 正在成为现实。如果说 Extra06 介绍的 GUI Agent 教会了 AI 如何操作手机和桌面应用，那么本章要介绍的就是它在网页世界的近亲——以浏览器为主要行动表面的智能体。

Web 之所以值得拥有一章独立的篇幅，有两个理由。第一，**世界上最有价值的数据与工作流，大部分都跑在网页上**——比手机 App 或桌面软件多得多。第二，**Web 是一个独立的技术问题**：它的感知、行动和可靠性挑战和移动/桌面 GUI Agent 有本质区别。你没法把 Mobile-Agent-v3 直接接到 Chrome 上就当作 Web Agent，这条路走不通。

本章的承诺是，读完之后你将：

- 理解 Web Agent 与传统 RPA、通用 GUI Agent 的本质区别
- 掌握三种主流感知策略（DOM、视觉、混合），并理解为什么生产级系统普遍走混合路线
- 通过 SDK 调用，以及作为工具集成进第七章构建的 **HelloAgents** 框架，亲手使用一个生产级的 Web Agent 服务——**TinyFish**
- 学会诊断和绕开常见的反爬机制
- 知道什么时候 **不应该** 使用托管型 Web Agent

---

## 第一部分：Web Agent 技术科普

### 1.1 什么是 Web Agent？

**Web Agent** 是一类以网页浏览器为主要行动表面的自主智能体。它通过 DOM、可访问性树和屏幕截图的某种组合来感知页面，用大语言模型推理下一步该做什么，然后在真实浏览器实例里执行动作——点击、输入、滚动、跳转。

关键词是 **自主**。一个用 Playwright 写死的爬虫脚本不是 Web Agent，它只是一段脆弱的程序，目标网站稍微改一下按钮位置就崩了。而 Web Agent 是在运行时根据自己 "看到" 的内容动态决定下一步动作的。

#### 1.1.1 Web Agent vs RPA vs GUI Agent

这条技术血缘很重要。我们把三者放在一起对比：

| 维度 | 传统 RPA（Selenium、UiPath） | GUI Agent（Mobile-Agent、AutoGLM） | Web Agent（Browser-Use、TinyFish） |
| --- | --- | --- | --- |
| **主要表面** | Web 或桌面 | 移动 + 桌面，以截图为主 | 网页浏览器 |
| **感知方式** | DOM 选择器（XPath、CSS） | 视觉（VLM 解析截图） | DOM + 可访问性树 + 视觉（混合） |
| **动作机制** | 固定脚本 | 基于坐标的点击 | 选择器、坐标和语义目标的混合 |
| **能否适应 UI 变化** | 不能——立即失效 | 能——视觉具备语义弹性 | 能——多种锚定信号 |
| **跨平台能力** | 有限 | 天然跨平台 | Web 本身就是跨平台 |
| **认证 / 会话处理** | 手动 | 有限 | 一等公民 |
| **反爬意识** | 几乎没有 | 不涉及 | 至关重要 |

两个最关键的点：

1. **Web Agent 不是 "限定在 Chrome 上的 GUI Agent"**。它会利用 DOM、可访问性树和网络层的结构化信息——这些信息要么不存在于移动/桌面环境，要么 GUI Agent 选择不用。生产级 Web Agent 一定是混合的：视觉负责理解布局，DOM/AX-tree 负责精准定位，根据动作的具体情况切换。
2. **Web 有它独有的对手**。Cloudflare、DataDome、PerimeterX、指纹识别、行为生物特征分析——这些在手机/桌面 GUI Agent 上都不存在。一个不考虑反爬的 Web Agent 在生产环境就是一个返回空结果的 Web Agent。

#### 1.1.2 为什么 Web Agent 在 2024–2026 突然爆发？

三股力量在同一时间汇合：

1. **多模态大模型能同时读懂截图和 DOM**。GPT-4o、Claude Sonnet 4、Gemini 2.5、Qwen-VL——它们对 UI 元素的视觉定位能力都已经足够强，能够在没有专门视觉训练的情况下驱动浏览器。
2. **无头浏览器基础设施成熟**。Playwright 和 Chrome DevTools Protocol（CDP）让我们能够廉价地在全球任何地方启动一个真实的 Chromium 实例，并加上隐身补丁、代理路由、远程控制。
3. **真实痛点足够大**。世界上一半的数据躺在没有 API 的网页背后——价格、库存、政府公开档案、新闻档案、各种厂商给企业部署的内部仪表盘。把这些工作流自动化的经济价值是巨大的，而只有 Web Agent 能填上这个空白。

我们还正好赶上各大 AI 实验室开始直接把这个能力产品化的时刻——Anthropic 的 Computer Use、OpenAI 的 Operator、Google 的 Project Mariner。"Web Agent" 正在迅速成为每个 AI 原生产品都会接入的基础能力。

### 1.2 核心技术架构

和所有 GUI Agent 一样，Web Agent 也是一个 **感知 → 推理 → 行动** 的闭环。但每一层都有 Web 特有的微妙之处。

#### 1.2.1 感知层：三种策略，各有致命弱点

业界有三种主流的感知策略，每一种都有另两种正好能补足的弱点：

**策略 A——基于 DOM**：解析页面的 HTML 和可访问性树。又快又准，能直接告诉你元素的类型、文本内容、选择器。**失败场景**：页面是 Canvas 渲染的 SPA（Google Docs、Figma 等），或者站点故意混淆 DOM，或者有意义的内容渲染进了爬虫读不到的 Shadow DOM。

**策略 B——基于视觉**：截屏 → 输入视觉大模型 → 模型识别要点击的元素并输出坐标。**失败场景**：模型把小字读错，元素位置幻觉，4K 页面上有些东西它就是看不到。而且成本高——每一步都要调一次 VLM 推理。

**策略 C——混合（生产环境的赢家）**：用视觉做布局理解和上下文推理（"这三个搜索框里，哪个才是我要的？"），再用 DOM 或可访问性树做精确定位（"这是要点击的具体元素"）。所有认真的生产级 Web Agent——Operator、Computer Use、Browser-Use、TinyFish——最终都走向了混合路线。

业界为什么会收敛到这一点？经验数据说话：在常见的生产工作流上，经过混合方案 + 隐身浏览器 + 反爬加固的成熟系统，成功率已经稳定在 90% 左右；而纯视觉、未加固的方案在 WebArena 这类对抗性学术基准上往往只有 30–40%。注意这两个数字衡量的是 **不同的东西**——学术基准刻意构造长链路、刁钻场景；生产系统是在真实业务流上做了大量针对性调优。但两条曲线都在显示同一件事：混合方案在工程上明显占优。

#### 1.2.2 推理层：记忆、反思和状态问题

Web 在推理层最大的挑战是 **状态突变**。页面会在你眼皮底下变：

- 无限滚动会随着你滚到底部不断加载新内容
- 页面加载两秒后冒出一个模态框，把你想点的按钮挡住了
- 点完 "加入购物车" 后页面重渲染，你之前那份 DOM 快照立即失效
- 登录流程会经过三个中间页才把你送到 dashboard

一个合格的 Web Agent 需要具备：

- **任务分解** —— 把 "帮我找周六价格 3000 以下的航班" 拆成一系列具体步骤
- **反思** —— 注意到一个动作没有产生预期效果，并能恢复
- **记忆** —— 翻到第二页时记住第一页搜索结果的内容
- **状态追踪** —— 区分 "按钮消失因为我点击了它" 和 "按钮消失因为页面崩了"

这正是第四章的 **ReAct 范式** 大放异彩的舞台。Web Agent 本质上就是一个 ReAct 循环，其中动作空间是 `{click, type, scroll, navigate, wait, extract}`，观察是下一个页面状态。

#### 1.2.3 行动层：Web 上独特的难点

动作空间乍看和移动 GUI Agent 类似——点击、输入、滚动。但 Web 层多出了：

- **会话状态**：cookies、localStorage、sessionStorage 需要跨动作保持（或刻意清空）
- **导航历史**：后退、前进、新标签页、切换标签
- **文件下载与上传**：不走 DOM
- **iframe 与 Shadow DOM 遍历**：一个网页不是一个文档，而是文档的树
- **网络层关注点**：你点完 "提交" 后，可能要等一个 XHR 完成才算 "做完"

只用坐标的 Web Agent 会碰上以上每一个限制。这就是混合方案成为生产标准的原因。

### 1.3 Web 独有的那些难题

下面这些问题，Extra06 没有也无法覆盖，因为它们在移动和桌面上根本不存在：

**反爬机制**。Cloudflare、DataDome、PerimeterX、Akamai Bot Manager。它们盯着你的 TLS 指纹、浏览器 JavaScript 对象签名、鼠标移动模式、操作时序。一个朴素的 Playwright 脚本几秒钟就被拦下了。生产级 Web Agent 需要 **隐身浏览器**（打了补丁、看起来和真实用户浏览器无法区分的 Chromium），通常还要搭配住宅 IP 代理。

**认证与会话保持**。OAuth 流程、二次验证、会话 cookie、"记住我" token、登录时的验证码。一个登不进去的 Web Agent 只能看到公开网页。带加密凭据库（vault）的方案是新兴模式。

**动态内容与竞态条件**。无限滚动、懒加载图片、800ms 后才出现的模态框、阻塞点击的动画。智能体必须知道页面什么时候算 "就绪"，而 "就绪" 没有清晰的定义。

**JS 重型 SPA**。当你访问一个现代 React 或 Vue 站点时，初始 HTML 基本是空的——真正的 DOM 是 JavaScript 在三秒后渲染出来的。朴素的爬虫看不到任何内容。

**网络、地理与限流**。有些内容被地理限制，有些接口按 IP 做限流，有些站点会在检测到 "太多" 来自同一来源的请求时静默降级响应。

**成本与延迟**。每一步动作都是一次 LLM 调用 + 一次浏览器往返。10 步的自动化任务可能要 30–60 秒，光 LLM 的 token 成本就是 0.10–1.00 美元。这正是业界拼命追求更小、更快、专门为 Web 微调的模型的原因。

### 1.4 2026 年的全景图：四类玩家的对比

2026 年的 Web Agent 生态系统大致可以分为四类，每一类的存在都对应一个真实的取舍：

| 类别 | 代表项目 | 优势 | 弱点 |
| --- | --- | --- | --- |
| **原始浏览器自动化** | Playwright、Puppeteer、Selenium | 快、可重复、免费、完全可控 | 没有 AI、脆弱，每次 UI 变动都要修脚本 |
| **开源 AI Web Agent** | Browser-Use、Skyvern、WebVoyager、AgentE | 免费、可魔改、完全透明 | 自己部署，自己处理反爬、代理、基础设施、可观测性 |
| **Computer-use API** | Anthropic Computer Use、OpenAI Operator、Google Project Mariner | 通用推理能力强、模型前沿 | 贵、UX 有立场、没有内建反爬或地理路由，常常以桌面为主而非纯 Web |
| **托管型 Web 自动化 API** | **TinyFish**、Browserbase、Apify、Bright Data | 隐身浏览器 + 代理 + 智能体循环一揽子打包，几分钟就能跑通；自带可观测性 | 有厂商依赖、对内部智能体循环控制更少、按任务计费 |

诚实的判断：每个类别都赢在不同的轴上。你是研究员、想研究 Agent 行为？用开源。你是个人开发者、爬一个没反爬的小站？纯 Playwright 就够了。你在为产品做功能、需要在真实世界（包含反爬）的站点上"开箱即用"？托管 API 能为你省下几周时间。

第二部分我们将用 TinyFish 来做实战练习——它的 API 设计在这一类里是最干净的，并且把智能体循环明确暴露出来，方便学习。

### 1.5 真实世界中的应用场景

下面是 Web Agent 已经在生产环境落地的（不完全）列表：

- **电商监控**：价格、库存、对手商品、评价聚合
- **B2B 数据增强与销售线索生成**：从类 LinkedIn 站点抓取信息、构建公司数据库
- **遗留 Web 系统的内部 RPA**：成千上万的公司，核心业务还跑在没有 API 的纯 UI 系统上，Web Agent 终于让它们可以被自动化
- **质量保证与自动化测试**：回归测试、可访问性审计、内容合规
- **研究类智能体（第十四章主题）**：一个不能浏览网页的研究智能体瞎了一半，Web Agent 是 DeepResearch 类系统天然的后端
- **旅行与预订工作流（第十三章主题）**：旅行助手在 "能真正完成预订" 而不是 "只能给推荐" 之后，使用价值会翻 10 倍
- **个人自动化**：盯一个职位发布、监控商品补货、跟踪政府公示

### 1.6 当前技术的真实局限

请对你的读者诚实。Web Agent 既令人兴奋，又有它的边界：

- **成功率：基准 vs 生产是两条曲线**。生产级 Web Agent（混合方案 + 隐身 + 反爬加固）在常见业务流上已经能稳定在 **90% 左右**；但在 WebArena、VisualWebArena 这类刻意构造的对抗性学术基准上，最好的系统也还在持续追赶。换句话说：工程闭环上能做到的事，比学术评测看起来要多得多——但任务本身越偏门、链路越长，差距越大。
- **反爬是一场移动的猫鼠游戏**。上个月好用的方案这个月可能就被识破。厂商对抗永无止境。
- **成本真实存在**。托管 API 平均每个任务 0.10–1.00 美元。自部署省钱、烧的是工程时间。
- **验证码是硬上限**。厂商再怎么宣传，现代 Web Agent **依然没法可靠地解开 reCAPTCHA 或 hCaptcha**。务实的做法是设计任务时绕开它，而不是硬扛。
- **幻觉的代价是真金白银**。一个填错的表单字段，可能让快递寄到错的地址。高风险动作必须有人类在环（human-in-the-loop）的检查点。

---

## 第二部分：实战教程

我们按由浅入深三步走：

1. **极速上手**——5 分钟内跑通第一个 TinyFish 调用，零框架、零环境
2. **观察智能体工作**——用直播 URL 可视化调试每一次运行
3. **集成进 HelloAgents**——把 TinyFish 包成一个 `Tool`，接入第七章框架里的 ReAct 智能体

### 2.1 极速上手：5 分钟内你的第一个 Web Agent

TinyFish 是一个托管型的 Web Agent API。你给它一个 URL 和一段自然语言 **目标（goal）**，它返回结构化 JSON。

#### 第 1 步：获取 API 密钥

1. 在 `agent.tinyfish.ai` 注册账号
2. 进入 API Keys 页面，点击 **Create API Key**
3. 复制密钥——它只显示一次
4. 写进你的 shell：

```bash
export TINYFISH_API_KEY="sk-tinyfish-..."
```

#### 第 2 步：安装 SDK

```bash
# Python
pip install tinyfish

# 或 TypeScript
npm install @tiny-fish/sdk
```

#### 第 3 步：你的第一个自动化任务

**Python：**

```python
from tinyfish import TinyFish, CompleteEvent

client = TinyFish()  # 自动从环境变量读取 TINYFISH_API_KEY

with client.agent.stream(
    url="https://scrapeme.live/shop",
    goal="提取前 2 个产品的名称和价格，以 JSON 形式返回。",
) as stream:
    for event in stream:
        if isinstance(event, CompleteEvent):
            print(event.result_json)
```

**TypeScript：**

```typescript
import { TinyFish, EventType } from "@tiny-fish/sdk";

const client = new TinyFish();

const stream = await client.agent.stream({
  url: "https://scrapeme.live/shop",
  goal: "提取前 2 个产品的名称和价格，以 JSON 形式返回。",
});

for await (const event of stream) {
  if (event.type === EventType.COMPLETE) {
    console.log(event.result);
  }
}
```

**原始 HTTP（不用 SDK）：**

```bash
curl -N -X POST https://agent.tinyfish.ai/v1/automation/run-sse \
  -H "X-API-Key: $TINYFISH_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://scrapeme.live/shop",
    "goal": "提取前 2 个产品的名称和价格"
  }'
```

运行起来，你会看到 Server-Sent Events 实时流进终端：

```
{"type": "STARTED", "run_id": "abc123"}
{"type": "STREAMING_URL", "run_id": "abc123", "streaming_url": "https://tf-abc123.fra0-tinyfish.unikraft.app/stream/0"}
{"type": "PROGRESS", "run_id": "abc123", "purpose": "Visit the page to extract product information"}
{"type": "PROGRESS", "run_id": "abc123", "purpose": "Check for product information on the page"}
{"type": "COMPLETE", "run_id": "abc123", "status": "COMPLETED", "result": {
  "products": [
    {"name": "Bulbasaur", "price": "$63.00"},
    {"name": "Ivysaur", "price": "$87.00"}
  ]
}}
```

就这样——你刚刚跑完了一个 Web Agent。这一次调用背后发生的事：数据中心里启动了一个真实的 Chromium 浏览器，导航到目标页面，解析布局，识别出商品卡片，提取数据，并把进度流式返回给你。

#### 请求的解剖

TinyFish 的 `/run-sse` 端点接收的 JSON 字段（**重点字段已加粗**）：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| **`url`** | string | 起始页面 |
| **`goal`** | string | 自然语言指令 |
| `output_schema` | object | 可选的 JSON Schema 子集，约束返回结构 |
| `browser_profile` | `"lite"` \| `"stealth"` | 默认 `lite` |
| `proxy_config` | object | 可选 `{enabled, type, country_code}` |
| `use_vault` | boolean | 是否使用保存的凭据完成登录 |
| `credential_item_ids` | string[] | 限定 vault 中的具体凭据 |

三个端点，三种模式：

- `POST /v1/automation/run`——同步，阻塞到完成，返回最终结果
- `POST /v1/automation/run-async`——发后即忘，立即返回 `run_id`
- `POST /v1/automation/run-sse`——流式，实时把进度事件推回给你

短任务（< 30 秒）用同步；批量作业用异步；要在 UI 上实时显示进度时用 SSE。

### 2.2 观察智能体工作——直播 URL

TinyFish 在教学上最有用的一个功能是 **`streaming_url`**：每次运行都会产生一个 URL，让你 **实时观看浏览器**。你可以把它嵌进自己产品的 iframe 里，也可以直接在浏览器开个 Tab 边调试边看。

```python
from tinyfish import TinyFish, CompleteEvent

client = TinyFish()

with client.agent.stream(
    url="https://scrapeme.live/shop",
    goal="提取前 3 个产品的名称和价格",
    on_streaming_url=lambda e: print(f"\n实时观看：{e.streaming_url}\n"),
    on_progress=lambda e: print(f"  → {e.purpose}"),
) as stream:
    for event in stream:
        if isinstance(event, CompleteEvent):
            print("\n最终结果：", event.result_json)
```

跑起来几乎瞬间就拿到一个可点击 URL。在浏览器里打开它——你看到的就是 **智能体正在驱动的真实浏览器会话**。页面在加载、鼠标在移动、字段在填写。这是大多数读者会发出 "卧槽，它真的在做" 的瞬间。

而且这不只是个演示噱头。直播流是调试 Web Agent **最好用** 的工具：

- 一次运行返回了空结果？打开直播——很可能你会看到一个 Cloudflare "Checking your browser" 拦截页，或者一个意料之外的弹窗
- 智能体点错了按钮？看直播、改 goal
- 在做面向用户的产品？把直播 URL 嵌进 iframe，让用户看着工作发生

### 2.3 怎么写好 goal

`goal` 这一个字段几乎就是 TinyFish 的全部 API 表面——写好它，是 90% 成功率和 30% 成功率的分水岭。

TinyFish 官方推荐的心智模型：**把智能体当成一个 "字面执行" 的助理，坐在浏览器前**。它能看到屏幕上的一切、能动手——但它没法猜你的意思。

一个出色的 goal 最多包含七个组件：

| 组件 | 示例 |
| --- | --- |
| **目标（Objective）** | "提取定价信息" |
| **范围（Target）** | "从定价表中" |
| **字段（Fields）** | "套餐名、月费、包含功能" |
| **结构（Schema）** | "返回 JSON：`[{plan: string, price_monthly: number}]`" |
| **步骤（Steps）** | "先关掉 cookie 横幅" |
| **护栏（Guardrails）** | "不要点击任何'立即购买'按钮" |
| **边缘情况（Edge cases）** | "如果价格显示为'联系我们'，置为 null" |

从最差到最好的演变：

**模糊（必然失败）：**
```
"获取这个页面的定价"
```

**好一些（可能能跑）：**
```
"提取产品名称、价格和库存状态"
```

**生产级品质：**
```
1. 等待页面完全加载。
2. 如果有 cookie 同意横幅，点击"全部接受"。
3. 定位定价区。
4. 对每个套餐，提取：套餐名称、月费（数字）、包含功能（字符串数组）。

不要点击任何购买或结账按钮。
如果套餐显示"联系我们"，monthly_price 置为 null。

返回 JSON：[{"plan": string, "monthly_price": number | null, "features": string[]}]
```

TinyFish 自己的测试里，相同任务下具体的 goal **完成速度快 4.9 倍**、**返回的多余数据少 16 倍**。Goal 写作就是新的 Prompt 工程，并且和所有 Prompt 工程一样，复利明显。

### 2.4 主菜：把 TinyFish 集成进 HelloAgents

这一节是本章的核心。直接调 API 当然可以——但本书，尤其是第四章和第七章，一直在传达的核心信息是：**当外部服务变成你自己框架里的工具，真正的力量才出现**。这就是 "使用 AI" 和 "用 AI 构建" 之间的分水岭。

我们要把 TinyFish 包装成一个 HelloAgents 的 `Tool`，接入 `ReActAgent`。

> **提示**：HelloAgents 是你在第七章构建的配套框架。如果还没装：`pip install hello-agents`。想要和正文完全对应的版本，可以切到 GitHub 上的 `learn_version` 分支。

#### 第 1 步：定义 `TinyFishWebTool`

我们写一个工具，把 Web 自动化暴露成单一能力。智能体用自然语言描述自己想做什么，工具负责调用 API 并返回结构化 JSON。

```python
# tools/tinyfish_tool.py
import json
import os
from typing import Any, Dict, List

from tinyfish import (
    TinyFish,
    BrowserProfile,
    ProxyConfig,
    ProxyCountryCode,
)

from hello_agents.tools import Tool, ToolParameter


class TinyFishWebTool(Tool):
    """让 ReAct 智能体通过自然语言驱动真实浏览器的工具。"""

    def __init__(self, api_key: str | None = None):
        super().__init__(
            name="web_automation",
            description=(
                "使用自然语言自动化任何网页。输入一个 JSON 字符串，包含两个必需字段："
                "`url`（起始页面）和 `goal`（清晰具体的任务描述）。"
                "可选字段：`stealth`（布尔值，针对有反爬保护的站点）、"
                "`country`（US/GB/CA/DE/FR/JP/AU，用于地理路由）。"
                "返回智能体抽取的结构化 JSON，或错误描述。"
            ),
        )
        self.client = TinyFish(
            api_key=api_key or os.environ["TINYFISH_API_KEY"],
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        # ToolRegistry 会把 ReAct 的输入文本包成 {"input": "..."}
        raw = parameters.get("input", "")
        try:
            params = json.loads(raw)
        except json.JSONDecodeError:
            return json.dumps(
                {"error": "输入必须是合法的 JSON 字符串"},
                ensure_ascii=False,
            )

        url = params.get("url")
        goal = params.get("goal")
        if not url or not goal:
            return json.dumps(
                {"error": "缺少必需字段 url 或 goal"},
                ensure_ascii=False,
            )

        kwargs: Dict[str, Any] = {"url": url, "goal": goal}
        if params.get("stealth"):
            kwargs["browser_profile"] = BrowserProfile.STEALTH
        if (country := params.get("country")):
            kwargs["proxy_config"] = ProxyConfig(
                enabled=True,
                country_code=ProxyCountryCode(country),
            )

        # 用同步 run——ReAct 循环要拿到结果再继续。
        # 长任务可以改用 queue + 轮询。
        run = self.client.agent.run(**kwargs)

        if run.status.value != "COMPLETED" or run.result is None:
            err = run.error.message if run.error else "未知失败"
            return json.dumps(
                {"error": err, "status": run.status.value},
                ensure_ascii=False,
            )

        return json.dumps(
            {"data": run.result, "run_id": run.run_id},
            ensure_ascii=False,
        )

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="input",
                type="string",
                description=(
                    "JSON 字符串，字段：url（必需）、goal（必需）、"
                    "stealth（可选）、country（可选）"
                ),
                required=True,
            )
        ]
```

代码里有几处值得特别留意：

1. **工具的 `description` 是 LLM 决定是否调用它时唯一看到的信息**。要像在跟一个从没读过你代码的初级开发者交代一样写描述——把输入、输出、何时使用都讲清楚。
2. **工具永远返回字符串**。ReAct 是文本进、文本出。我们把结果序列化成 JSON，让智能体在下一步 "Thought" 中能继续推理。
3. **`stealth` 和 `country` 不是默认开启而是可选参数**。让 LLM 自己决定——通过工具描述告诉它什么时候该开。

#### 第 2 步：把工具接入 ReAct 智能体

```python
# main.py
from hello_agents import ReActAgent, HelloAgentsLLM, ToolRegistry
from tools.tinyfish_tool import TinyFishWebTool

llm = HelloAgentsLLM()  # 从 .env 读取 provider 配置
registry = ToolRegistry()
registry.register_tool(TinyFishWebTool())

agent = ReActAgent(
    agent_name="research_assistant",
    llm=llm,
    tool_registry=registry,
)

result = agent.run(
    "查询苹果官方商店和京东上 iPhone 17 Pro 的当前价格，"
    "在考虑商品页面所标的运费后告诉我哪个更便宜。"
)
print(result)
```

运行起来，ReAct 循环大致会经历这样的过程：

1. **Thought（思考）**："我需要从两个不同的站点拿价格。我应该调用两次 web_automation。"
2. **Action（行动）**：`web_automation({"url": "https://www.apple.com/.../iphone-17-pro", "goal": "提取 iPhone 17 Pro 起步价。返回 JSON: {price_cny: number, free_shipping: boolean}"})`
3. **Observation（观察）**：`{"data": {"price_cny": 9999, "free_shipping": true}}`
4. **Thought**："现在拿京东价格。京东有反爬——我应该启用 stealth。"
5. **Action**：`web_automation({"url": "https://item.jd.com/...", "goal": "...", "stealth": true})`
6. **Observation**：`{"data": {"price_cny": 9799, "free_shipping": true}}`
7. **Thought**："两边都包邮。京东便宜 200 元。"
8. **Final Answer**："京东目前比苹果官方便宜 200 元：京东 ¥9,799，苹果官方 ¥9,999，两家都免运费。"

刚刚发生的事，正是第七章希望传达的核心：**外部服务作为一等公民进入你自己的框架**。ReAct 循环没变，LLM 也没变。我们只是加了一个工具，你的智能体就具备了在公开网络上行动的能力。这就是 **可组合性**。

#### 第 3 步：把它做到生产级

上面的版本演示足够了。真实生产环境还要再加几样：

**1. 验证内容，不要只看状态**

`COMPLETED` 的运行也可能返回垃圾，如果智能体撞上了软拦截（Cloudflare 挑战页、验证码、把 "访问被拒绝" 渲染成正文）。永远要检查 **结果内容**：

```python
def is_real_success(result: dict | None) -> bool:
    if not result:
        return False
    s = json.dumps(result, ensure_ascii=False).lower()
    failure_signals = ["captcha", "blocked", "access denied", "could not", "unable to"]
    return not any(signal in s for signal in failure_signals)
```

**2. 能缓存就缓存**

一次 30 秒的网页自动化是昂贵的。如果同一会话里 ReAct 智能体两次要求同一个 URL，应该返回缓存结果。（第八章的记忆系统是个合适的着力点。）

**3. 设置超时**

TinyFish 内部每次运行有 10 分钟超时，但你的工具应该更早失败——多数有意义的任务在 10–60 秒内完成。超过这个时间，多半是卡在挑战页上了。

**4. 用直播流做可观测**

把每次运行的 `streaming_url` 记下来，写日志。生产环境出问题时，运行录像是定位故障最快的工具。

### 2.5 应对反爬

你的智能体迟早会撞上一个返回空结果或 403 的站点。这是诊断流程：

**第 1 步——确认问题就是反爬**。打开失败那次运行的 `streaming_url`，找以下几种特征：

| 你看到什么 | 大概率原因 |
| --- | --- |
| Cloudflare "Checking your browser" 页 | Cloudflare 机器人检测 |
| DataDome 弹窗或重定向 | DataDome |
| 空白页或永远转圈 | 基于 IP 或指纹的拦截 |
| 验证码（reCAPTCHA、hCaptcha） | 验证码——硬上限 |
| "Access Denied" / 403 | IP 或 User-Agent 拦截 |
| 该看到内容时却出现登录墙 | 基于会话的反爬 |

**第 2 步——隐身和代理一起开**。隐身改变浏览器指纹，代理改变 IP。反爬厂商会关联两个信号——只改一个往往不够：

```python
run = client.agent.run(
    url="https://protected-site.com",
    goal="提取商品价格",
    browser_profile=BrowserProfile.STEALTH,
    proxy_config=ProxyConfig(enabled=True, country_code=ProxyCountryCode.US),
)
```

**第 3 步——让智能体表现得更像人类**。有些站点关注行为而不只是指纹。在 goal 里加上：

- 显式关闭 cookie 横幅
- 抽取前等页面加载完成
- 用视觉描述元素（"蓝色的'加入购物车'按钮"），不要用选择器
- 多步流程用编号步骤，让智能体自己慢下来

**第 4 步——实在不行就换打法**。有些站点死命拦爬虫，但会大方提供 RSS、sitemap、公开 API。花五分钟翻一翻，省下几天试错时间。如果数据真的只在付费墙后的格式化页面里，问问自己：底层信息源（公告、新闻稿、厂商页面）是不是在防守更弱的地方也有。

一段完整的、加固过的范例：

```python
from tinyfish import (
    TinyFish, BrowserProfile, ProxyConfig, ProxyCountryCode,
    CompleteEvent, RunStatus,
)

client = TinyFish()

with client.agent.stream(
    url="https://protected-site.com/pricing",
    browser_profile=BrowserProfile.STEALTH,
    proxy_config=ProxyConfig(enabled=True, country_code=ProxyCountryCode.US),
    goal="""
        1. 等待页面完全加载。
        2. 关闭任何 cookie 同意 / GDPR 横幅。
        3. 继续之前等待 1 秒。
        4. 定位定价区（通常是网格或卡片表格）。
        5. 对每个套餐，提取：套餐名、月费、年费（如有）。

        如果出现 Cloudflare 或安全检查页，等它自动通过。
        如果看到 Access Denied 或 CAPTCHA 页，返回 {"error": "blocked"}。
        不要点击任何购买或结账按钮。

        返回 JSON：[{"plan": "Pro", "monthly_price": 49, "annual_price": 39}]
    """,
    on_streaming_url=lambda e: print(f"实时观看：{e.streaming_url}"),
    on_progress=lambda e: print(f"  → {e.purpose}"),
) as stream:
    for event in stream:
        if isinstance(event, CompleteEvent):
            if event.status == RunStatus.COMPLETED:
                print("结果：", event.result_json)
            else:
                print("失败：", event.error.message if event.error else "unknown")
```

**重要的诚实声明**：包括 TinyFish 在内，没有任何 Web Agent 能可靠地解开现代验证码（reCAPTCHA v2/v3、hCaptcha）。如果一个站点向你弹出验证码，那目前就是一道硬墙。正确的做法是把你的运行设计得不去触发它，而不是硬扛。

### 2.6 加餐：通过 MCP 调用 TinyFish（对应第十章）

第十章介绍了 **MCP（Model Context Protocol）**——Anthropic 提出的、让 AI 助手连接外部工具和数据的开放协议。TinyFish 暴露了一个 MCP 服务器。这意味着，你可以让任何兼容 MCP 的助手（Claude Desktop、Cursor、Windsurf、Claude Code）具备驱动浏览器的能力——你自己一行代码都不用写。

一行命令安装：

```bash
# Claude Code
npx -y install-mcp@latest https://agent.tinyfish.ai/mcp --client claude-code

# Claude Desktop
npx -y install-mcp@latest https://agent.tinyfish.ai/mcp --client claude

# Cursor
npx -y install-mcp@latest https://agent.tinyfish.ai/mcp --client cursor
```

或者手动在 `claude_desktop_config.json` 里加：

```json
{
  "mcpServers": {
    "tinyfish": {
      "url": "https://agent.tinyfish.ai/mcp"
    }
  }
}
```

重启后，你的助手会多出 `run_web_automation`、`search`、`fetch_content`、`create_browser_session` 等工具。然后你就可以直接对 Claude 说：

> "并行抓取以下 5 个竞品的定价页，把结果整理成表格。"

Claude 就会用 TinyFish 在背后完成这件事，批量执行，实时反馈进度。

这正是第十章预告的 **一次构建、处处可用** 的回报。MCP 作为分发协议，把每一个工具都变成了 **每个 AI 助手都能直接使用** 的能力。

---

## 第三部分：综合思考

### 3.1 什么时候 **不要** 用托管 Web Agent

为了诚实：托管 Web Agent 并不总是正确选择。

- **有官方 API**——用 API。API 更快、更便宜、更可靠
- **高频率爬取无反爬站点**——纯 Playwright 就够了，便宜几个数量级
- **错误代价高的关键工作流**——不管你用什么工具，永远要在关键步骤加上人类在环检查点
- **你完全可控的内部工具**——干脆加一个 API 端点

什么时候用托管 Web Agent：目标站点在外部、没有 API、有反爬保护、流程是多步的，**而且工程时间比任务级单价更值钱**。

### 3.2 Web Agent 接下来的方向

这个领域走得很快。未来 12–24 个月值得关注的几件事：

- **更小、更快、专为 Web 微调的模型**。前沿模型对 "点击蓝色按钮" 是杀鸡用牛刀。下一代 OS 专家智能体——例如 Qwen-VL-2.5-VL 之后的模型——会大幅压低单步动作的延迟和成本。
- **认证会话成为一等公民**。Vault 集成（加密的密码管理器桥接）开始落地。这将解锁下一波智能体应用——银行、医疗、内部工具，这些场景登录是入口。
- **学术基准向生产水位靠拢**。常见业务流上的生产成功率已经稳定在 90% 左右；WebArena 这类对抗性基准上的分数也在快速攀升，差距正在被工程和模型两端同时压缩。
- **本地 Web Agent**。隐私敏感任务（医疗记录、税务）需要本地运行的智能体。本地 VLM 配合本地 Chromium 已经看起来可行。
- **Web Agent 评测成熟化**。第十二章讲的评测方法学正好适用——很快会看到面向生产 Web Agent 的标准化评测套件。

### 3.3 接下来该往哪走

如果这一章勾起了你的兴趣，下面几条路可以继续：

- **结合第八章（记忆）**：让你的 Web Agent 记住昨天爬到了什么，今天只取增量
- **结合第十二章（评估）**：给你的 Web Agent 装上成功率追踪。你会很快摸清楚哪些站点需要 stealth、哪些 goal 需要再细化
- **结合第十三章和第十四章**：旅行助手和 DeepResearch 智能体一旦把动作空间扩展到 "真实浏览器"，会发生质变。试试用 Web Agent 做后端重写其中一个
- **可以研究的开源替代品**：Browser-Use（Python）、Skyvern（Python）、WebVoyager（研究基准）、AgentE（开源智能体基础设施）
- **基准**：WebArena、VisualWebArena、Mind2Web、WebVoyager-2024——把论文读一遍，你就会清楚 2026 年的 Web Agent 在哪个水位

---

## 结语

归根到底，Web Agent 不过就是一个 ReAct 循环——只不过它的行动表面是浏览器。前面章节里你学到的一切——感知、推理、行动、记忆、评估——都直接适用。新的东西是这个 **对抗性环境**：真实网站对自动化的敌意，是移动 App 和桌面软件所没有的，这种敌意正是 Web Agent 工程之所以独立成为一门学问的原因。

好消息是：你不需要从零解决这一切。像 TinyFish 这样的生产级原语，正是为此而存在。作为一个 AI 原生智能体的构建者，你的工作是把这些原语 **组合** 成有用的东西——并且把这件事在你自己 **从头到尾理解** 的框架里完成。

去构建吧。开放的 Web 是世界上最大的行动表面，从未有过比现在更好的时机，去教会一个智能体使用它。

---

*致谢：感谢 TinyFish 团队对本章技术细节的输入。所有 API 细节核对自 [TinyFish 官方文档](https://docs.tinyfish.ai)。*
