# 智能旅行规划系统

> 基于 AI 的智能旅行规划助手，自动为您生成个性化旅行方案

## 📝 项目简介

智能旅行规划系统是一个结合大语言模型（LLM）、向量数据库和地图服务的全栈旅游规划应用。它通过多智能体协作，为用户提供从景点搜索、酒店推荐、天气查询到完整行程生成的端到端服务。

### 解决什么问题？

- **繁琐的行程规划**：传统规划需要查阅大量攻略、地图和多个服务，耗时长且效率低
- **个性化不足**：通用攻略无法满足个人偏好和特殊需求
- **信息分散**：景点、酒店、交通、天气等信息需要从不同渠道获取，整合困难
- **缺乏记忆**：无法记住用户的旅行历史和偏好，每次都需要重新输入

### 有什么特色功能？

- 采用多智能体协作架构，专业化分工提升规划质量
- 基于向量数据库的记忆系统，越用越智能
- 地理位置验证确保行程可行性
- 并行查询优化，响应时间从 8-13 秒优化到 3-5 秒
- 支持地图可视化、预算计算、行程编辑、导出等完整功能

### 适用于什么场景？

- **个人旅行规划**：快速生成个性化行程，节省大量时间
- **家庭出游**：根据家庭成员偏好推荐合适行程，照顾每个人的需求
- **商务旅行**：高效安排出差行程，平衡工作效率与休息
- **深度游**：基于历史记忆的渐进式探索，发现更多特色景点

## ✨ 核心功能

- [ ] **智能行程规划**：输入目的地、日期、偏好，AI 自动生成完整行程，目前支持30个热门旅游城市的相关精确规划
- [ ] **地图可视化**：高德地图集成，标注景点位置和游览路线，直观展示行程安排
- [ ] **预算计算**：自动统计门票、酒店、餐饮、交通费用，帮助控制旅行成本
- [ ] **用户认证**：支持注册登录和行程记录，保存个人旅行历史
- [ ] **记忆学习**：向量数据库记录用户偏好，越用越智能，推荐更符合个人口味
- [ ] **实时天气**：查询行程期间天气预报，提前做好行程调整准备
- [ ] **行程编辑**：支持添加、删除、调整景点和活动，灵活定制行程
- [ ] **导出功能**：支持导出为 PDF 或图片格式，方便分享和保存
- [ ] **多智能体协作**：景点搜索专家、酒店推荐专家、天气查询专家、行程规划专家协同工作
- [ ] **地理位置验证**：确保景点位置准确性，同一天景点距离控制在 50 公里内
- [ ] **性能优化**：并行查询提升响应速度，提供更好的用户体验
- [ ] **限流熔断**：API 请求限流和熔断保护，确保系统稳定性

## 🛠️ 技术栈

### 后端技术栈

- **Web框架**：FastAPI - 高性能异步 Web 框架
- **LLM服务**：OpenAI API / 智谱 AI / 通义千问 - 大语言模型支持
- **Agent框架**：HelloAgents - 多智能体协作框架
- **向量数据库**：FAISS + Sentence-Transformers - 向量存储和检索
- **缓存数据库**：Redis - 高性能缓存和会话管理
- **地图服务**：高德地图 API（MCP 协议）- 地理位置服务和路线规划
- **图片服务**：Unsplash API - 高质量图片素材
- **认证**：JWT + Bcrypt - 安全的用户认证机制

### 前端技术栈

- **框架**：Vue 3 + TypeScript - 渐进式 JavaScript 框架
- **构建工具**：Vite - 下一代前端构建工具
- **组件库**：Element Plus - Vue 3 组件库
- **路由**：Vue Router - 官方路由管理器
- **状态管理**：Pinia - Vue 3 官方状态管理库
- **地图**：高德地图 JS API - 地图可视化
- **导出**：html2canvas + jsPDF - PDF 和图片导出

### 使用的智能体范式

- **多智能体协作**：采用 ReAct 范式，多个专业化 Agent 分工协作
- **专业分工**：景点搜索 Agent、酒店推荐 Agent、天气查询 Agent、行程规划 Agent
- **并行执行**：各 Agent 独立工作，提升整体效率

### 使用的工具和API

- **高德地图 API**：地理位置搜索、距离计算、路线规划
- **Unsplash API**：高质量图片素材获取
- **LLM API**：自然语言理解和行程生成

### 其他依赖库

- FastAPI 相关：pydantic、uvicorn、python-multipart
- 数据处理：numpy、requests
- 向量处理：faiss-cpu、sentence-transformers
- 认证安全：pyjwt、bcrypt
- 日志监控：huggingface-hub

## 🚀 快速开始

### 环境要求

**后端环境**：
- Python 3.11+
- pip 包管理器
- Redis 缓存服务

**前端环境**：
- Node.js 16+
- npm 包管理器

**外部服务**：
- 高德地图 API Key
- Unsplash API Key
- LLM API Key（OpenAI、DeepSeek、智谱 AI、通义千问等）

### 安装依赖

#### 前期准备工作

1. **准备 API 密钥**
   
   你需要准备以下 API 密钥：
   
   - **LLM API Key**：OpenAI、DeepSeek、智谱 AI 或通义千问等任一平台的 API 密钥
   - **高德地图 Web 服务 Key**：访问 https://console.amap.com/ 注册并创建应用
   - **Unsplash Access Key**：访问 https://unsplash.com/developers 注册并创建应用

2. **克隆项目**

```bash
git clone <repository-url>
cd trip_planner
```

#### 后端安装步骤

1. **安装并启动 Redis**

   - **Windows**：下载并安装 Redis for Windows，在 redis 安装目录下使用命令：
     ```bash
     redis-server.exe
     ```
   
   - **macOS**：
     ```bash
     brew install redis && brew services start redis
     ```
   
   - **Linux**：
     ```bash
     sudo apt-get install redis-server && sudo systemctl start redis
     ```

2. **安装后端依赖**

```bash
cd backend
pip install -r requirements.txt
```

3. **配置后端环境变量**

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，填入必要配置：
#   - LLM_API_KEY（必需）：LLM API 密钥
#   - LLM_BASE_URL（可选）：LLM 服务地址
#   - LLM_MODEL_ID（可选）：模型名称
#   - AMAP_API_KEY（必需）：高德地图 API 密钥
#   - UNSPLASH_ACCESS_KEY（必需）：Unsplash API 密钥
#   - REDIS_HOST、REDIS_PORT（默认 localhost:6379）：Redis 连接信息
```

4. **启动后端服务**

```bash
python run.py
```

后端服务将在 http://localhost:8000 启动

#### 前端安装步骤

1. **安装前端依赖**

```bash
cd ../frontend
npm install
```

2. **配置前端环境变量**

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，配置：
#   - VITE_API_BASE_URL：后端服务地址（默认 http://localhost:8000）
#   - VITE_AMAP_KEY：高德地图 JavaScript API Key（与后端的 Web 服务 Key 不同）
#   - VITE_AMAP_SECURITY_CODE：高德地图安全密钥（如果需要）
```

3. **启动前端服务**

```bash
npm run dev
```

前端服务将在 http://localhost:5173 启动

### 访问应用

打开浏览器访问 http://localhost:5173，注册或登录账号，然后输入目的地、日期、偏好等信息，点击"生成行程"即可使用。

## 📖 使用示例

### 示例 1：规划北京三日游

```javascript
// 前端表单提交示例
const tripRequest = {
  destination: "北京",
  start_date: "2024-03-01",
  end_date: "2024-03-03",
  preferences: ["历史文化", "美食", "博物馆"],
  hotel_preferences: ["市中心", "交通便利"],
  budget: "中等"
};

// 调用 API 生成行程
const response = await fetch('/api/v1/trips/plan', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify(tripRequest)
});

const tripPlan = await response.json();
```

**返回结果示例**：
```json
{
  "trip_title": "北京历史文化三日深度游",
  "total_budget": 2500,
  "hotels": [
    {
      "name": "北京王府井希尔顿酒店",
      "address": "东城区王府井东街8号",
      "price_per_night": 800,
      "rating": 4.8
    }
  ],
  "days": [
    {
      "day": 1,
      "date": "2024-03-01",
      "weather": "晴天，温度 8-18°C",
      "activities": [
        {
          "name": "故宫博物院",
          "type": "景点",
          "description": "中国古代皇家宫殿，世界文化遗产",
          "duration": "4小时",
          "cost": 60,
          "image": "https://images.unsplash.com/photo-...",
          "location": {"lat": 39.9163, "lng": 116.3972}
        }
      ]
    }
  ]
}
```

### 示例 2：地图可视化展示

系统会在结果页面自动加载高德地图，展示：
- 📍 各景点的位置标记
- 🛤️ 每日的游览路线
- 💡 点击标记显示景点详细信息
- 🎯 自动调整视野以显示所有景点

### 示例 3：预算计算

系统自动统计并分类显示：
- **景点门票**：故宫 60元 + 天坛 35元 + 颐和园 30元 = 125元
- **酒店住宿**：800元/晚 × 2晚 = 1600元
- **餐饮美食**：预计 500元
- **交通及其他**：预计 275元
- **总预算**：2500元

### 示例 4：导出行程

用户可以点击"导出 PDF"或"导出图片"按钮，将生成的行程保存为 PDF 文档或 PNG 图片，方便分享给同行的朋友或保存到本地。

## 🎯 项目亮点

- **多智能体协作**：景点搜索专家、酒店推荐专家、天气查询专家、行程规划专家协同工作，各司其职，提升规划质量

- **向量记忆系统**：基于 FAISS 的向量数据库，记录用户偏好和历史行程，系统会根据用户的旅行习惯不断优化推荐，越用越智能

- **地理位置验证**：确保所有景点都在目标城市范围内，同一天景点距离控制在 50 公里内，避免行程过于紧张或不可行

- **并行性能优化**：景点、酒店、天气查询并行执行，响应时间从 8-13 秒优化到 3-5 秒，大幅提升用户体验

- **企业级架构**：包含中间件、异常处理、日志系统、限流熔断等完整的企业级特性，确保系统稳定性和可维护性

- **智能体范式应用**：采用 ReAct 范式，结合推理和行动，让智能体能够自主思考和执行任务

## 🔮 未来计划

- [ ] **智能体增强**：增加餐厅推荐、交通规划等专业化 Agent，提供更全面的旅行服务

- [ ] **社交功能**：支持行程分享、评论、收藏，让用户可以与朋友一起规划旅行

- [ ] **多语言支持**：国际化支持多语言界面，方便海外用户使用

- [ ] **移动端优化**：开发小程序或 APP，提供更便捷的移动端体验

- [ ] **实时协作**：支持多人共同编辑行程，适合团队旅行规划

- [ ] **预算智能**：基于历史数据预测实际花费，提供更准确的预算估算

- [ ] **智能推荐**：基于用户画像和历史行为，推荐目的地和景点

- [ ] **行程优化**：提供多种行程方案对比，让用户选择最满意的方案

## 🤝 贡献指南

欢迎提出 Issue 和 Pull Request！

### 如何贡献

1. Fork 本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

### 代码规范

- **Python 代码**：遵循 PEP 8 规范，使用 black 进行格式化
- **JavaScript/TypeScript 代码**：遵循 ESLint 规范，使用 Prettier 进行格式化
- **提交信息**：使用清晰的提交信息，说明修改内容和原因

### Issue 提交

提交 Issue 时，请提供：
- 清晰的问题描述
- 重现步骤
- 期望行为
- 实际行为
- 环境信息（操作系统、Python/Node 版本等）
- 相关的日志或错误信息

## 📄 许可证

本项目采用 MIT 许可证。详情请参阅 [LICENSE](LICENSE) 文件。

MIT License

Copyright (c) 2024 Trip Planner Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

## 👤 作者

- GitHub: [@你的用户名](https://github.com/你的用户名)
- Email: 你的邮箱（可选）

## 🙏 致谢

感谢以下开源项目和社区的支持：

- **HelloAgents 框架**：提供了强大的多智能体协作能力
- **Datawhale 社区**：提供了学习和交流的平台
- **Hello-Agents 项目**：为智能体应用开发提供了灵感和参考
- **FastAPI**：高性能的 Web 框架
- **Vue.js**：优雅的前端框架
- **Element Plus**：精美的 Vue 3 组件库
- **高德地图**：提供专业的地图服务
- **Unsplash**：提供高质量的图片素材

同时感谢所有为本项目做出贡献的开发者和用户！

---

**注意**：本项目仅用于学习和研究目的，请遵守各 API 服务商的使用条款和隐私政策。
