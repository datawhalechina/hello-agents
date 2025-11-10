# 测试文件说明

## test_quick.py

快速测试 Hello-Agents 是否安装成功。

### 使用方法

**方式 1: 使用虚拟环境（推荐）**

```powershell
# 激活虚拟环境
.\venv_hello_agents\Scripts\Activate.ps1

# 运行测试
python test/test_quick.py
```

**方式 2: 直接指定 Python 解释器**

```powershell
.\venv_hello_agents\Scripts\python.exe test/test_quick.py
```

### 预期输出

如果配置了 API 密钥（.env 文件）：
```
✅ HelloAgents 导入成功！
✅ OpenAI API Key 已配置: True
```

如果没有配置 API 密钥：
```
✅ HelloAgents 导入成功！
✅ OpenAI API Key 已配置: False
```

### 配置 API 密钥

1. 复制环境变量模板：
   ```powershell
   copy .env.example .env
   ```

2. 编辑 `.env` 文件，填入您的 API 密钥：
   ```env
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_BASE_URL=https://api.moonshot.cn/v1
   OPENAI_MODEL=moonshot-v1-128k
   ```

   详细配置方法请参考：`国产大模型API配置指南.md`

### 常见问题

**Q: 提示 "No module named 'hello_agents'"**
A: 确保在虚拟环境中安装依赖：
   ```powershell
   .\venv_hello_agents\Scripts\python.exe -m pip install -r requirements-core.txt
   ```

**Q: 提示 "API密钥和服务器地址必须被提供"**
A: 需要配置 `.env` 文件，参考上方"配置 API 密钥"部分。

**Q: 如何验证 API 连接？**
A: 运行完整的测试脚本：
   ```powershell
   python test_installation.py
   ```

