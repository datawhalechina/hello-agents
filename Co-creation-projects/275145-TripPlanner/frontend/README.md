# 智能旅行助手 - 前端

基于 Vue 3 + TypeScript + Element Plus 的智能旅行规划前端应用。

## 功能特性

- 🌍 **智能行程规划**：输入目的地和偏好，AI 自动生成完整行程
- 🗺️ **地图可视化**：高德地图集成，标注景点位置和游览路线
- 💰 **预算计算**：自动统计门票、酒店、餐饮等费用
- ✏️ **行程编辑**：支持添加、删除、调整景点和活动
- 📄 **导出功能**：支持导出为 PDF 或图片格式

## 技术栈

- Vue 3 - 渐进式 JavaScript 框架
- TypeScript - 类型安全的 JavaScript 超集
- Vite - 下一代前端构建工具
- Element Plus - Vue 3 组件库
- Vue Router - 官方路由管理器
- Axios - HTTP 客户端
- 高德地图 JS API - 地图服务
- html2canvas + jsPDF - 导出功能

## 快速开始

### 安装依赖

\`\`\`bash
npm install
\`\`\`

### 配置环境变量

复制 `.env` 文件并配置您的 API 密钥：

\`\`\`bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000
VITE_AMAP_KEY=您的高德地图Key
\`\`\`

### 开发模式

\`\`\`bash
npm run dev
\`\`\`

访问 http://localhost:5173

### 生产构建

\`\`\`bash
npm run build
\`\`\`

## 项目结构

\`\`\`
src/
├── components/          # 通用组件
│   ├── MapView.vue     # 地图组件
│   ├── BudgetSummary.vue  # 预算组件
│   └── ExportButtons.vue  # 导出组件
├── views/              # 页面组件
│   ├── Home.vue        # 首页（规划表单）
│   ├── Result.vue      # 结果展示页
│   └── EditPlan.vue    # 编辑页面
├── services/           # API 服务
│   └── api.ts          # API 请求封装
├── types/              # 类型定义
│   └── index.ts        # TypeScript 接口
├── router/             # 路由配置
│   └── index.ts        # 路由定义
├── App.vue             # 根组件
└── main.ts             # 应用入口
\`\`\`

## 主要功能

### 1. 智能行程规划

用户在首页填写表单：
- 目的地
- 出行日期
- 旅行偏好
- 酒店偏好
- 预算范围

提交后系统调用后端 API，生成智能行程计划。

### 2. 地图可视化

使用高德地图展示：
- 景点位置标记
- 游览路线绘制
- 信息窗口展示详情
- 自适应视野调整

### 3. 预算计算

自动统计并分类显示：
- 景点门票费用
- 餐饮美食费用
- 酒店住宿费用
- 交通及其他费用

### 4. 行程编辑

支持灵活编辑：
- 添加/删除天数
- 添加/删除/修改活动
- 编辑酒店信息
- 实时预算更新

### 5. 导出功能

支持多种导出格式：
- PDF 文档导出
- PNG 图片导出
- 自定义导出内容

## API 接口

### 创建行程规划

\`\`\`typescript
POST /api/v1/trips/plan

请求体：
{
  destination: string
  start_date: string
  end_date: string
  preferences: string[]
  hotel_preferences: string[]
  budget: string
}

响应：
{
  trip_title: string
  total_budget: number
  hotels: Hotel[]
  days: DailyPlan[]
}
\`\`\`

## 开发说明

- 使用 Vue 3 Composition API
- TypeScript 严格模式
- ESLint + Prettier 代码规范
- 响应式设计，适配移动端

## 注意事项

1. 需要申请高德地图 API Key
2. 确保后端服务已启动（默认 http://localhost:8000）
3. 首次运行需要安装依赖

## 许可证

MIT
