# 智能API测试助手（API Test Assistant）

> 基于 Hello-Agents 框架的多智能体应用：给它一份 OpenAPI 文档，它自动完成「解析 → 生成用例 → 执行测试 → 验证结果 → 生成报告」的全流程，让接口测试从"手写 Postman 请求"变成"粘贴文档、看报告"。

## 📝 项目简介

接口测试是软件开发的刚需，但传统做法又慢又容易漏：测试人员要对着接口文档，**手写**各种测试用例，再**手动**一个个发请求、**肉眼**盯状态码和返回字段。一个接口磨十几分钟，几十个接口就是一天，还容易漏掉边界情况。

本项目用**多智能体流水线**把这件事自动化：

```
输入：一份 OpenAPI 文档（.yaml / .json）
          ↓
① ParserAgent    解析文档，提取接口清单
          ↓
② GeneratorAgent 用 LLM 智能生成测试用例（正常 / 边界 / 异常三类）
          ↓
③ ExecutorAgent  真实发 HTTP 请求去调用目标接口
          ↓
④ ValidatorAgent 校验状态码和返回结构是否符合预期
          ↓
⑤ ReporterAgent  汇总成 HTML 报告 + 通过率统计
          ↓
输出：一份漂亮的测试报告
```

**核心价值**：LLM 只负责"想该测什么"（这是最需要智能的地方），发请求、校验结果这些确定性的活交给工具，既智能又可靠。

## ✨ 核心功能

- ✅ **多智能体流水线**：5 个 Agent 各司其职，上一个的输出是下一个的输入
- ✅ **LLM 智能生成用例**：自动覆盖正常 / 边界 / 异常三类场景，人想不到的边界值它来补
- ✅ **真实 HTTP 调用**：带超时控制和自动重试，真实反映目标接口的行为
- ✅ **自动结果校验**：状态码比对 + JSON Schema 结构校验
- ✅ **双格式报告**：HTML + Markdown 两种格式 + 通过率统计，一眼定位失败用例
- ✅ **前端可视化**：FastAPI + Vue3 工程化前端，粘贴文档点按钮即可测试
- ✅ **命令行入口**：`python main.py` 一键跑完整个流程
- ✅ **URL 抓取**：`--url` 参数直接抓取网络上的 OpenAPI 文档，无需先下载
- ✅ **认证请求头**：`--header` 参数传入 Authorization / API Key，能测需要鉴权的接口

## 🛠️ 技术栈

- **Hello-Agents** 框架（`hello-agents>=1.0.0`，多 Agent 架构）
- **LLM**：OpenAI 兼容接口（支持 DeepSeek / 各类中转站），通过 `HelloAgentsLLM()` 调用
- **Web 服务**：FastAPI + Uvicorn（把测试能力暴露成 HTTP 接口）
- **前端**：Vue3 + Vite + Element Plus + axios（`npm run dev` 开发 / `npm run build` 打包）
- **文档解析**：PyYAML + JSON（解析 OpenAPI 文档）
- **结构校验**：jsonschema（校验响应体结构）
- **报告渲染**：Jinja2（HTML 报告模板）

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 一个 OpenAI 兼容的 LLM API Key（DeepSeek 或中转站均可）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置 API 密钥

```bash
# 复制模板
cp .env.example .env

# 编辑 .env，填入真实配置
# LLM_MODEL_ID=deepseek-chat          （你的模型名）
# LLM_API_KEY=sk-你的真实密钥
# LLM_BASE_URL=https://api.deepseek.com/v1
```

### 运行项目

本项目提供三种运行方式，按需选择：

**方式 1：命令行（最直接）**

```bash
python main.py --file api.yaml --base-url https://jsonplaceholder.typicode.com
```

**方式 2：Web 前端（可视化）**

```bash
cd frontend
npm install                 # 首次运行安装前端依赖
npm run build               # 构建 Vue 前端，生成 frontend/dist/
cd ..
python server.py
# 浏览器打开 http://localhost:8000
```

`server.py` 只托管 Vue 构建产物。首次运行或修改前端代码后，需要重新执行 `npm run build`。

**方式 3：Jupyter Notebook（教学演示）**

```bash
jupyter lab
# 打开 main.ipynb 并逐格运行
```

**方式 4：Docker 容器化部署（可选，免装本地环境）**

项目自带多阶段构建的 `Dockerfile`（Node 阶段编译前端 + Python 阶段运行后端），一条命令打成镜像：

```bash
docker build -t api-test-assistant .

# 运行时把 .env 的密钥注入容器（密钥不进镜像，只在本机运行时读取）
docker run -d --name api-test-assistant -p 8000:8000 --env-file .env api-test-assistant
# 浏览器打开 http://localhost:8000
```

> 若目标后端也跑在 Docker 里，把本容器挂到同一网络，即可用「容器名」当地址去测它：
> `docker network connect <网络名> api-test-assistant`，界面里目标地址填如 `http://chat-backend-1:8000`。

## 📖 使用示例

### 命令行方式

以项目自带的 `api.yaml`（JSONPlaceholder 的 /users、/posts 两个接口）为例：

```bash
python main.py --file api.yaml --base-url https://jsonplaceholder.typicode.com
```

运行后自动生成 `reports/report.html`，终端会打印：

```
[1/5] 解析完成：发现 2 个接口
[2/5] 生成完成：共 6 个测试用例
[3/5] 执行完成：已发送 6 个请求
[4/5] 验证完成
[5/5] 报告已生成：reports/report.html
测试结果：总数 6，通过 4，失败 2，通过率 66.7%
```

> 失败的那 2 个用例是"异常场景"：LLM 期望返回 400，但 JSONPlaceholder 这个 mock 服务对非法参数也返回 200。这恰恰证明了工具能**如实发现真实 API 的行为与文档约定不符**。

也可以直接用 `--url` 从网络抓取文档，无需先下载到本地：

```bash
python main.py --url https://httpbin.org/spec.json --base-url https://httpbin.org
```

两种方式都会同时生成 `reports/report.html` 和 `reports/report.md`。

需要认证的接口，用 `--header` 传入认证头（可多次使用）：

```bash
python main.py --url https://httpbin.org/spec.json --base-url https://httpbin.org --header "Authorization: Bearer your-token"
```

### Web 前端方式（Vue3）

前端是 Vue3 工程，支持生产模式和开发模式两种运行方式：

**生产模式（部署）**
```bash
cd frontend && npm run build   # 打包 → frontend/dist/
cd ..
python server.py               # 启动后端，自动托管 dist
# 浏览器打开 http://localhost:8000
```

**开发模式（改代码热更新）**
```bash
python server.py               # 终端1：后端在 8000
cd frontend                    # 终端2
npm install                     # 首次运行安装前端依赖
npm run dev                     # Vite 开发服务器在 5173（/api 自动代理到 8000）
# 浏览器打开 http://localhost:5173
```

打开后：选择「粘贴文档」并填入 OpenAPI 文档，或选择「URL 抓取」直接填写网络上的 OpenAPI 文档地址；
再填写目标 API 地址，点「🚀 开始测试」，下方展示统计卡片与用例明细（点行可展开看请求/响应详情）。

## 📂 项目结构

```
senming666-api_test_assistant/
├── README.md                       # 项目说明（本文件）
├── requirements.txt                # Python 运行依赖
├── requirements-dev.txt            # Python 开发依赖（pytest）
├── pytest.ini                      # pytest 配置
├── main.py                         # 命令行入口，串起 5 个 Agent
├── main.ipynb                      # Jupyter 演示入口
├── server.py                       # FastAPI 服务，托管 Vue 构建产物
├── .env.example                    # LLM 配置模板（不含真实密钥）
├── .env                            # 本地真实配置，不应提交到代码仓库
├── api.yaml                        # 示例：被测目标文档（JSONPlaceholder）
├── httpbin.json                    # 示例：被测目标文档（httpbin.org）
├── openapi_service.yaml            # 本项目自身服务的 OpenAPI 文档
├── frontend/                       # Vue3 + Vite + Element Plus 前端工程
│   ├── index.html                  # Vite HTML 入口和 Vue 挂载点
│   ├── package.json                # 前端依赖和 npm scripts
│   ├── package-lock.json           # 前端依赖锁定文件
│   ├── vite.config.js              # Vite 配置、路径别名和 /api 代理
│   └── src/
│       ├── main.js                 # Vue 应用入口，注册 Element Plus
│       ├── App.vue                 # 根组件，编排页面状态
│       ├── api/
│       │   ├── request.js          # axios 实例和统一错误处理
│       │   └── test.js             # 调用后端测试接口
│       ├── components/
│       │   ├── ApiTestForm.vue     # 文档粘贴、URL 抓取和测试参数表单
│       │   ├── ResultSummary.vue   # 测试汇总展示
│       │   └── ResultTable.vue     # 用例明细和请求响应展示
│       ├── constants/
│       │   └── exampleDoc.js       # 示例文档和展示映射
│       ├── utils/
│       │   └── format.js            # 数据展示格式化
│       └── styles/
│           └── index.css            # 全局样式
├── reports/                        # HTML 和 Markdown 测试报告输出目录
├── tests/                          # Python 单元测试
│   ├── test_parser_agent.py
│   ├── test_generator_agent.py
│   ├── test_executor_agent.py
│   ├── test_validator_agent.py
│   ├── test_reporter_agent.py
│   ├── test_schema_validator.py
│   └── test_http_client.py
└── src/                            # Python 核心源代码
    ├── __init__.py
    ├── config.py                   # 配置常量（超时/重试/并发等）
    ├── tools/                      # 工具层：HTTP 请求和结果校验
    │   ├── __init__.py
    │   ├── http_client.py           # HTTP 请求工具（超时+重试）
    │   └── schema_validator.py      # 状态码和 JSON Schema 校验
    └── agents/                     # Agent 流水线
        ├── __init__.py
        ├── parser_agent.py         # ① 解析 OpenAPI 文档
        ├── generator_agent.py      # ② 用 LLM 生成测试用例
        ├── executor_agent.py       # ③ 真实调用目标接口
        ├── validator_agent.py      # ④ 验证接口返回结果
        └── reporter_agent.py       # ⑤ 生成测试报告
```

## 🎯 项目亮点

- **分层清晰**：工具层（tools）与智能体层（agents）分离，Agent 决策、Tool 干活
- **智能与确定性结合**：只有 GeneratorAgent 用 LLM（想"测什么"），其余 4 个 Agent 是确定性逻辑（更可靠、更省 token）
- **数据穿层设计**：用例在流水线中逐层包裹新字段（case → +result → +passed/errors），每层职责单一
- **真实可跑**：不依赖 mock，直接对公网 API 发起真实请求，结果可信
- **全栈完整**：后端（FastAPI）+ Vue3 前端 + 命令行 + Notebook 四种入口

## 📊 性能评估

> 覆盖三套被测对象。后续计划补充：接口覆盖率、各环节耗时占比、不同 LLM 对比。

### 测试对象一：JSONPlaceholder（`api.yaml`，2 个 GET 接口）

结果：**总数 6，通过 4，失败 2，通过率 66.7%**

- ✅ normal / boundary 用例全部通过（GET 接口正常返回 200）
- ❌ 2 个 error 用例失败：LLM 预期"传未定义参数返回 400"，但 JSONPlaceholder 是 mock 服务，对任意参数都返回 200

**分析**：失败并非 bug，而是 LLM 预期与 mock 服务宽松行为的合理摩擦，证明工具如实报告而非"粉饰"。

### 测试对象二：自己测自己（`openapi_service.yaml`，GET / + POST /api/test）

用测试助手测试它自己暴露的接口，三轮迭代：

| 迭代 | 通过率 | 抓到的 bug → 修复 |
|---|---|---|
| ① 初始 | 33.3% (2/6) | POST 用例全 422：ParserAgent 未提取 requestBody，LLM 看不到必填字段 |
| ② 补数据穿层 | 66.7% (4/6) | POST boundary 空字符串 → server 内部 500 崩溃 |
| ③ 加空输入容错 | 83.3% (5/6) | 只剩 GET / 不校验参数（非 bug，页面接口常态） |

**修复内容**：
1. `parser_agent.py`：提取 `requestBody` 字段，并对空输入 / 非 dict 加类型容错
2. `generator_agent.py`：prompt 传入请求体定义，强调 body 字段名必须精确匹配

**关键结论**：这个项目本身就是"测试工具"，用它测自己时连续抓到 2 个真实 bug（requestBody 穿层断裂、空输入 500 崩溃），比"全绿"更能体现工具价值——测试工具能反过来驱动被测对象改进。

### 测试对象三：httpbin.org（`--url` 抓取完整 spec，73 个接口）

用 `--url` 抓取 httpbin 官方 spec（`https://httpbin.org/spec.json`），传入认证头 `Authorization: Bearer test-token`，启用路径参数替换，并对请求做 1.5 秒限速以避开 httpbin 对突发流量的限流（返回 503）。

结果：**总数 219，通过 120，失败 99，通过率 54.8%**（干净数据，0 个 503）

失败原因分布（99 个失败，均非工具缺陷）：
- **46 个「期望报错却返回 200」**：LLM 预期 400/404/405 等错误码，但 httpbin 作为测试服务对异常输入宽容，统一返回 200（工具如实报告了被测对象的宽松行为）
- **20 个「服务端 500」**：重定向到无效目标、`/delay`、`/stream` 等特殊接口的参数组合，httpbin 服务端直接返回 500
- **17 个「404」**：路径参数为空或缺失时，httpbin 返回 404 而非文档声明的 4xx
- **7 个「502」**：`/brotli`、`/deflate`、`/gzip` 等压缩编码接口的响应解码问题（httpbin 服务端上游）
- **5 个「401 认证」**：`/basic-auth`、`/digest-auth` 需要 Basic 认证，本次测试传的是 Bearer 头，认证方式不匹配（测试参数配置问题，非工具缺陷）
- 其余 4 个为 406（图片内容协商）等边缘情况

**结论**：99 个失败均可归因于被测对象（httpbin 测试服务）的行为特性或测试参数配置，**工具本身无缺陷**——它如实报告了每一个失败，没有误判、没有掩盖。


## 🔮 未来计划

- [ ] 并发执行测试用例（config 里已预留 MAX_CONCURRENCY）
- [ ] 补充更多性能数据（接口覆盖率、各环节耗时占比、多 LLM 对比）

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@senming666](https://github.com/senming666)
- 项目链接: [senming666-api_test_assistant](https://github.com/datawhalechina/Hello-Agents/tree/main/Co-creation-projects/senming666-api_test_assistant)

## 🙏 致谢

感谢 Datawhale 社区和 Hello-Agents 项目！
