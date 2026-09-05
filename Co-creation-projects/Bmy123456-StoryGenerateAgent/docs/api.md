# API文档

## 概述

故事生成器智能体提供RESTful API接口，支持多种文本生成功能。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`

## 端点

### 1. 生成内容

**POST** `/generate`

生成小说、诗歌或剧本等内容。

#### 请求参数

```json
{
  "generation_type": "novel|poem|script",
  "theme": "string",
  "style": "string",
  "length": "短篇|中篇|长篇",
  "form": "自由诗|格律诗|十四行诗|俳句",
  "genre": "喜剧|悲剧|科幻|悬疑|剧情",
  "scene_count": 3
}
```

#### 响应

```json
{
  "success": true,
  "content": "生成的文本内容",
  "generation_type": "novel",
  "tokens_used": 500
}
```

#### 示例

```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "generation_type": "novel",
    "theme": "一个关于友谊的故事",
    "style": "现实主义"
  }'
```

### 2. 总结内容

**POST** `/summarize`

总结给定文本内容。

#### 请求参数

```json
{
  "content": "需要总结的文本"
}
```

#### 响应

```json
{
  "success": true,
  "summary": "总结内容"
}
```

#### 示例

```bash
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{
    "content": "这是一个测试文本，用于测试总结功能。它包含一些重要信息。"
  }'
```

### 3. 翻译内容

**POST** `/translate`

将文本翻译成指定语言。

#### 请求参数

```json
{
  "content": "需要翻译的文本",
  "language": "目标语言"
}
```

#### 响应

```json
{
  "success": true,
  "translation": "翻译后的文本"
}
```

#### 示例

```bash
curl -X POST http://localhost:8000/translate \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, world!",
    "language": "中文"
  }'
```

### 4. 健康检查

**GET** `/health`

检查服务健康状态。

#### 响应

```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### 5. 获取模型信息

**GET** `/model/info`

获取当前使用的模型信息。

#### 响应

```json
{
  "model_name": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 1000
}
```

## 错误处理

API使用标准的HTTP状态码表示错误：

- `200 OK`: 请求成功
- `400 Bad Request`: 请求参数错误
- `500 Internal Server Error`: 服务器内部错误

错误响应格式：

```json
{
  "success": false,
  "error": "错误信息"
}
```

## 认证

API使用API密钥进行认证，需要在请求头中包含：

```
Authorization: Bearer YOUR_API_KEY
```

## 速率限制

- 每分钟最多100个请求
- 每小时最多1000个请求

## 版本

当前API版本：v1.0.0

## 联系方式

如有问题，请联系支持团队。