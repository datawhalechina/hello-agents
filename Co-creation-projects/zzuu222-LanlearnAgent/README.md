# 语言学习助手Language-Learn-Agent

> 一个语言学习agent，以对话来帮助用户进行语言学习，使用目标语言和ai讨论日常、专业知识、百科知识或者新闻等等。

## 📝 项目简介

详细介绍你的项目:
- 解决的问题：在英语学习的过程中，我们很少有机会使用英语来交流。
- 特色功能：用户可以设定自己偏好的方向。可设定难度，根据设定难度来选择回复中包含的单词和语法。对话长度不固定，可以由用户自己触发结束对话或由AI自己判定是否结束。对话完成后进行总结，总结对话中的拼写错误、语法错误、较难单词等。
- 适用场景：适用于中小学生到大学生的语言学习，或者从业人员对于专业领域的语言学习。

## ✨ 核心功能

- [X] 功能1: 根据用户设定的偏好和难度进行对话。
- [X] 功能2: 自行判断是否需要调用搜索来获取最新信息，并且根据信息来回答用户。
- [X] 功能3: 对话时保存对话文本，结束后开始总结，总结对话中的拼写错误和语法错误等。

## 🛠️ 技术栈

- HelloAgents框架
- Python3
- 搜索工具tavily

## 🚀 快速开始

### 环境要求

- Python 3.10+
- 其他要求

### 安装依赖


pip install -r requirements.txt


### 配置API密钥


# 创建.env文件
cp .env.example .env

# 编辑.env文件，填入你的API密钥


### 运行项目

- 直接运行主程序 main.py
- 运行后提示输入语句开始对话，
- 需要提前退出可以在输入语句写入bye等单词，即可自动结束对话

## 📖 使用示例
```
第1轮对话
请输入句子进行对话：Hi, you got anything new about RTX 60 series?
✅ Tavily 搜索引擎已初始化
⚠️ 未安装 google-search-results，无法使用 SerpApi 搜索
🔧 混合搜索模式已启用，可用后端: tavily
INFO:openai._base_client:Retrying request to /chat/completions in 0.475520 seconds
That's a really interesting topic, and I'm glad you brought it up. So, based on the latest rumors,......
......
......
第4轮对话
请输入句子进行对话：bye, i have to go.
Thanks for the reminder. I see that in your last message, "bey" should be "bye," and "i" should be capitalized as "I." So the correct sentence would be: "Bye, I have to go."

It was a pleasure chatting with you about the RTX 60 series and the 5070 Ti. Feel free to come back if you have more questions or want to practice English. Take care! 
对话总结如下：
以下是根据当前对话内容生成的总结，包含语法易错点和较难单词（对应中级难度，即四级到六级水平）。
---
### 【语法和易错点总结】
1. **现在完成时中动词形式错误**  
   - 用户错误：`"I have not think"`  
   - 正确：`"I have not thought"`（think 的过去分词是 thought）  
   - 提示：现在完成时（have/has + 过去分词）中，动词必须用过去分词形式，不能直接用原形。

2. **否定回答的用词错误**  
......
......
```

## 📄 许可证

MIT License

## 👤 作者

- GitHub: [@zzuu222](https://github.com/zzuu222)
- Email: zl2891229@gmail.com

## 🙏 致谢

感谢Datawhale社区和Hello-Agents项目！
