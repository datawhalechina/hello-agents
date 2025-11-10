# 国产大模型 API 配置指南

Hello-Agents 项目使用 OpenAI SDK，支持所有**兼容 OpenAI API 格式**的服务商。

## ✅ 支持的国产大模型服务商

以下是已验证支持的国产大模型服务商及其配置方法：

---

## 🌙 1. Moonshot AI（月之暗面 - Kimi）

**推荐指数**: ⭐⭐⭐⭐⭐

### 特点
- ✅ 完全兼容 OpenAI API 格式
- ✅ 长文本处理能力强（支持 128K tokens）
- ✅ 中文理解优秀
- ✅ 提供免费额度
- ✅ 国内访问速度快

### 注册地址
https://platform.moonshot.cn/

### 配置方法

在 `.env` 文件中配置：

```env
# Moonshot AI 配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.moonshot.cn/v1
OPENAI_MODEL=moonshot-v1-8k

# 可用模型：
# - moonshot-v1-8k (8K上下文)
# - moonshot-v1-32k (32K上下文)
# - moonshot-v1-128k (128K上下文，推荐)
```

### 获取 API Key
1. 访问 https://platform.moonshot.cn/console/api-keys
2. 点击"创建新的 API Key"
3. 复制生成的 API Key（格式：sk-xxxxx）

---

## 🌟 2. 通义千问（阿里云）

**推荐指数**: ⭐⭐⭐⭐⭐

### 特点
- ✅ 阿里云官方支持
- ✅ 稳定可靠
- ✅ 提供免费额度
- ✅ 支持多种模型

### 注册地址
https://dashscope.aliyun.com/

### 配置方法

```env
# 通义千问配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-max

# 可用模型：
# - qwen-max (最强版本)
# - qwen-plus (增强版)
# - qwen-turbo (快速版)
# - qwen-long (长文本版，支持1M tokens)
```

---

## 🤖 3. 智谱 AI（GLM）

**推荐指数**: ⭐⭐⭐⭐⭐

### 特点
- ✅ 清华技术背景
- ✅ 代码能力强
- ✅ 提供免费额度
- ✅ 完全兼容 OpenAI 格式

### 注册地址
https://open.bigmodel.cn/

### 配置方法

```env
# 智谱 AI 配置
OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxx
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
OPENAI_MODEL=glm-4

# 可用模型：
# - glm-4 (最新旗舰版)
# - glm-4-flash (快速版，免费)
# - glm-4-plus (增强版)
```

---

## 🔥 4. 百度千帆（文心一言）

**推荐指数**: ⭐⭐⭐⭐

### 特点
- ✅ 百度官方支持
- ✅ 企业级稳定性
- ✅ 中文能力优秀

### 注册地址
https://qianfan.cloud.baidu.com/

### 配置方法

```env
# 百度千帆配置
OPENAI_API_KEY=your_qianfan_api_key
OPENAI_BASE_URL=https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat
OPENAI_MODEL=ERNIE-4.0-8K

# 可用模型：
# - ERNIE-4.0-8K
# - ERNIE-3.5-8K
# - ERNIE-Speed-8K (快速版)
```

---

## 🚀 5. DeepSeek（深度求索）

**推荐指数**: ⭐⭐⭐⭐⭐

### 特点
- ✅ 性价比极高
- ✅ 代码能力强
- ✅ 完全兼容 OpenAI 格式
- ✅ 提供大量免费额度

### 注册地址
https://platform.deepseek.com/

### 配置方法

```env
# DeepSeek 配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
OPENAI_MODEL=deepseek-chat

# 可用模型：
# - deepseek-chat (对话模型)
# - deepseek-coder (代码专用模型)
```

---

## 🌐 6. 硅基流动（SiliconFlow）

**推荐指数**: ⭐⭐⭐⭐

### 特点
- ✅ 聚合多个开源模型
- ✅ 价格便宜
- ✅ 提供免费额度
- ✅ 完全兼容 OpenAI 格式

### 注册地址
https://siliconflow.cn/

### 配置方法

```env
# 硅基流动配置
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_MODEL=Qwen/Qwen2.5-7B-Instruct

# 可用模型众多，包括：
# - Qwen/Qwen2.5-7B-Instruct
# - deepseek-ai/DeepSeek-V2.5
# - meta-llama/Meta-Llama-3.1-8B-Instruct
```

---

## 📊 服务商对比

| 服务商 | 推荐度 | 免费额度 | 速度 | 中文能力 | 代码能力 | 长文本 |
|--------|--------|---------|------|----------|----------|--------|
| **Moonshot** | ⭐⭐⭐⭐⭐ | ✅ | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 128K ✅ |
| **通义千问** | ⭐⭐⭐⭐⭐ | ✅ | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 1M ✅ |
| **智谱GLM** | ⭐⭐⭐⭐⭐ | ✅ | ⚡⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 128K ✅ |
| **DeepSeek** | ⭐⭐⭐⭐⭐ | ✅✅✅ | ⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 64K |
| **百度千帆** | ⭐⭐⭐⭐ | ✅ | ⚡⚡⚡ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | 8K |
| **硅基流动** | ⭐⭐⭐⭐ | ✅ | ⚡⚡ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 视模型 |

---

## 🎯 推荐选择

### 场景 1: 学习 Hello-Agents（本项目）
**推荐**: Moonshot、通义千问、智谱 GLM
- 理由：稳定、快速、免费额度充足、中文支持好

### 场景 2: 代码相关任务
**推荐**: DeepSeek、智谱 GLM
- 理由：代码能力强，特别是 DeepSeek-Coder

### 场景 3: 长文本处理
**推荐**: 通义千问（qwen-long）、Moonshot（128k）
- 理由：支持超长上下文

### 场景 4: 预算有限
**推荐**: DeepSeek、硅基流动
- 理由：价格便宜，DeepSeek 免费额度最多

---

## 🔧 完整配置示例

创建 `.env` 文件（选择一个服务商配置即可）：

```env
# ========================================
# 方案 1: Moonshot AI (推荐用于本项目)
# ========================================
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.moonshot.cn/v1
OPENAI_MODEL=moonshot-v1-128k

# ========================================
# 方案 2: 通义千问
# ========================================
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# OPENAI_MODEL=qwen-max

# ========================================
# 方案 3: 智谱 AI
# ========================================
# OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxxxxxx
# OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
# OPENAI_MODEL=glm-4-flash

# ========================================
# 方案 4: DeepSeek（性价比之王）
# ========================================
# OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# OPENAI_BASE_URL=https://api.deepseek.com/v1
# OPENAI_MODEL=deepseek-chat

# ========================================
# 其他必需配置
# ========================================
# Tavily Search API（第1章、第4章需要）
TAVILY_API_KEY=tvly-xxxxx

# 高德地图 API（第13章需要）
AMAP_API_KEY=your_amap_key_here
```

---

## ✅ 验证配置

配置完成后，运行验证脚本：

```bash
python test_installation.py
```

如果看到以下输出，说明配置成功：

```
✅ LLM API 连接成功！
   响应: 你好！我是 AI 助手...
```

---

## 🐛 常见问题

### Q1: 提示 API Key 无效
**解决方案**:
1. 检查 API Key 是否完整复制（注意前后空格）
2. 确认 API Key 未过期
3. 检查账户余额或免费额度

### Q2: 连接超时
**解决方案**:
1. 检查网络连接
2. 尝试更换服务商
3. 增加超时时间（在代码中配置）

### Q3: 模型名称错误
**解决方案**:
1. 参考上方各服务商的可用模型列表
2. 访问服务商官网查看最新模型列表

### Q4: 速率限制（Rate Limit）
**解决方案**:
1. 检查免费额度是否用尽
2. 降低请求频率
3. 考虑升级付费套餐

---

## 💡 使用建议

1. **多备份几个服务商**: 建议注册 2-3 个服务商，避免单点故障
2. **合理使用免费额度**: 学习阶段完全够用
3. **选择合适的模型**: 
   - 简单任务用快速版（如 glm-4-flash）
   - 复杂任务用旗舰版（如 moonshot-v1-128k）
4. **监控使用量**: 定期查看 API 使用统计

---

## 📞 获取更多帮助

- Moonshot 文档: https://platform.moonshot.cn/docs
- 通义千问文档: https://help.aliyun.com/zh/dashscope/
- 智谱 AI 文档: https://open.bigmodel.cn/dev/api
- DeepSeek 文档: https://platform.deepseek.com/docs
- 项目 Issue: https://github.com/datawhalechina/hello-agents/issues

---

**祝您使用愉快！🎉**

如有任何问题，欢迎在项目 Issue 中反馈。

