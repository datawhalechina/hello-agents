# 配置指南

## 当前状态
项目已配置为使用智谱AI的GLM-4.5模型，支持小说、诗歌、剧本生成功能。

## 遇到的导入问题及解决方案

### 1. 重复的配置文件内容
- **问题**: `config/settings.py` 文件中有重复内容
- **解决方案**: 已修复，文件现在只包含一份配置

### 2. LLM客户端不支持智谱AI
- **问题**: 原来的LLM客户端只支持OpenAI
- **解决方案**: 已更新支持智谱AI接口

### 3. 验证工具中的错误
- **问题**: `validation.py` 中调用了不存在的 `settings.get_available_models()`
- **解决方案**: 已修复为调用本地的 `get_available_models()` 函数

### 4. 依赖管理问题
- **问题**: requirements.txt 中有不存在的依赖（如 langchain、hello-agent）
- **解决方案**: 已移除不需要的依赖

### 5. 缺少必要的目录
- **问题**: 某些运行时需要的目录不存在
- **解决方案**: 创建脚本会自动创建这些目录

## 快速开始步骤

### 步骤1：安装依赖
```bash
python setup.py
```

### 步骤2：检查环境
```bash
python check_env.py
```

### 步骤3：基础测试
```bash
python basic_test.py
```

### 步骤4：使用项目
```bash
# 运行Jupyter Notebook
jupyter notebook main.ipynb

# 或启动API服务器
python start_server.py
```

## 文件说明

### 配置文件
- `.env`: 环境变量配置
- `config/settings.py`: 主配置文件
- `config/prompts.py`: 提示词模板

### 核心代码
- `src/agent.py`: 智能体主类
- `src/models/llm_client.py`: LLM客户端（支持OpenAI和智谱AI）
- `src/generator/`: 各种生成器实现
- `src/utils/validation.py`: 输入验证

### 测试工具
- `basic_test.py`: 基础功能测试
- `simple_test.py`: 简单测试
- `test_imports.py`: 导入测试
- `check_env.py`: 环境检查

### 启动脚本
- `start_server.py`: FastAPI服务器
- `setup.py`: 安装脚本

## 常见问题

### Q: 运行时报错"No module named 'xxx'"
A: 运行 `python setup.py` 安装依赖

### Q: API密钥错误
A: 确保 `.env` 文件中的密钥正确

### Q: 无法连接到智谱AI
A: 检查网络连接和BASE_URL

### Q: 导入模块失败
A: 检查Python路径和文件结构

## 技术支持

如果仍有问题，请：
1. 运行所有测试脚本
2. 检查错误日志
3. 查看文档和示例