<div style="text-align:center">

<h1>Agently-Daily-News-Collector</h1>

<h3>Agently 新闻汇总报告生成器</h3>

<b><a href = "./README.md">English Introduction</a> | 中文说明</b>

</div>

**Agently新闻汇总报告生成器**是一个基于[**_<font color = "red">Agent</font><font color = "blue">ly</font>_** AI应用开发框架](https://github.com/Maplemx/Agently)开发的应用项目。本项目构建了**基于大语言模型驱动的全自动工作流**，能够根据用户输入的主题关键词，自动完成新闻汇总报告的结构设计、栏目组稿（含新闻检索、筛查、总结、栏目信息撰写）及报告MarkDown格式文件的输出全过程。同时，本项目**完全开源**，欢迎开发者们通过Fork->PR的方式共同优化。

新闻汇总报告的样例可参考：

`MarkDown文件` [Lastest Updated on AI Models 2024-05-02](https://github.com/AgentEra/Agently-Daily-News-Collector/blob/main/examples/Latest%20Updates%20on%20AI%20Models2024-05-02.md)

`PDF文件` [Lastest Updated on AI Models 2024-05-02](https://github.com/AgentEra/Agently-Daily-News-Collector/blob/main/examples/Latest%20Updates%20on%20AI%20Models%202024-05-02.pdf)

> 如果您希望进一步了解[**_<font color = "red">Agent</font><font color = "blue">ly</font>_** AI应用开发框架](https://github.com/Maplemx/Agently)，您可以访问框架的[主仓库地址](https://github.com/Maplemx/Agently)或是[中文官网](http://Agently.cn)阅读更多相关信息，框架提供了丰富的教程和案例，帮助您逐步上手。

## 如何使用

### 第一步：将本仓库Clone到本地

在您的开发目录中使用以下Shell脚本指令：

```shell
git clone git@github.com:AgentEra/Agently-Daily-News-Collector.git
```

### 第二步：修改SETTINGS.yaml设置文件

您可以在Clone到本地的项目文件夹中找到[`SETTINGS.yaml`](https://github.com/AgentEra/Agently-Daily-News-Collector/blob/main/SETTINGS.yaml)这个文件，再根据您的需要修改其中的设置项即可。

下面是具体的设置项说明：

```yaml
# Debug Settings
IS_DEBUG: false # 如果此项为true，将会输出更多执行过程信息，包括搜索和模型请求的明细信息
# Proxy Settings
PROXY: http://127.0.0.1:7890 # 项目中的搜索和模型请求可能会需要使用前向代理，可以通过此项设置代理信息
# Model Settings
MODEL_PROVIDER: OAIClient #默认使用OpenAI格式的兼容客户端，此客户端能够适配OpenAI以及各类兼容OpenAI格式的本地模型
MODEL_URL: http://base_url_path # 如果您需要修改Base URL，使用此项进行设置
MODEL_AUTH:
  api_key: "" # 在这里输入鉴权用的API-Key信息
MODEL_OPTIONS: # 在这里指定模型需要的其他参数，如指定具体的模型，或是调整temperature
  model: gpt-3.5-turbo
  temperature: 0.8
# Application Settings
MAX_COLUMN_NUM: 3 # 在这里设置汇总报告结构中的专栏数量 
OUTPUT_LANGUAGE: Chinese # 在这里设置汇总报告的输出语种，默认为英语，您可能需要手动改成中文
MAX_SEARCH_RESULTS: 8 # 在这里设置每个栏目搜索的最大结果数量
# 注意，如果数量设置过大，可能会导致超出模型的处理窗口大小，请根据模型具体情况设置
SLEEP_TIME: 5 # 在这里设置每次模型请求后的等待时间，以防止频繁请求导致模型拒绝访问
```

如果您想要了解切换其他模型的更多细节，可以阅读Agently官方网站关于[模型设置的说明页面](http://agently.tech/features/model_request.html)。

### 第三步：启动任务

因为本项目为Python项目，您需要在本地安装Python环境。您可以在[Python官方网站](https://www.python.org/)找到适合您的安装方法。

然后，在您的项目目录下使用以下Shell脚本指令更新项目依赖包：

```shell
pip install -r requirements.txt
```

依赖包安装完毕后，通过以下Shell脚本指令即可启动：

```shell
python app.py
```

随后您会看到一个提示：`[Please input the topic of your daily news collection]:`。

根据提示输入您想要汇总的新闻领域主题关键词，或是用一句话描述您想要生成什么样的新闻汇总报告，然后任务就会开始自动运行了。在这里，您可以输入任何语种的内容，但生成内容的语种会和您在第二步中的设置的语种要求相同。

接下来您就可以等待运行的结果了，整个过程大约需要5-8分钟。

在运行的过程中，您会看到类似下面展示的输出日志，这些日志将帮助您了解当前在处理的任务，以及运行的关键进展情况：

```shell
2024-05-02 22:44:27,347 [INFO]  [Outline Generated] {'report_title': "Today's news about AI Models Appliaction", 'column_list': [{'column_title': 'Latest News', 'column_requirement': 'The content is related to AI Models Appliaction, and the time is within 24 hours', 'search_keywords': 'AI Models Appliaction news latest'}, {'column_title': 'Hot News', 'column_requirement': 'The content is related to AI Models Appliaction, and the interaction is high', 'search_keywords': 'AI Models Appliaction news hot'}, {'column_title': 'Related News', 'column_requirement': 'The content is related to AI Models Appliaction, but not news', 'search_keywords': 'AI Models Appliaction report'}]}
2024-05-02 22:44:32,352 [INFO]  [Start Generate Column] Latest News
2024-05-02 22:44:34,132 [INFO]  [Search News Count] 8
2024-05-02 22:44:46,062 [INFO]  [Picked News Count] 2
2024-05-02 22:44:46,062 [INFO]  [Summarzing]    With Support from AWS, Yseop Develops a Unique Generative AI Application for Regulatory Document Generation Across BioPharma
2024-05-02 22:44:52,579 [INFO]  [Summarzing]    Success
2024-05-02 22:44:57,580 [INFO]  [Summarzing]    Over 500 AI models are now optimised for Core Ultra processors, says Intel
2024-05-02 22:45:02,130 [INFO]  [Summarzing]    Success
2024-05-02 22:45:19,475 [INFO]  [Column Data Prepared]  {'title': 'Latest News', 'prologue': 'Stay up-to-date with the latest advancements in AI technology with these news updates: [Yseop Partners with AWS to Develop Generative AI for BioPharma](https://finance.yahoo.com/news/support-aws-yseop-develops-unique-130000171.html) and [Intel Optimizes Over 500 AI Models for Core Ultra Processors](https://www.business-standard.com/technology/tech-news/over-500-ai-models-are-now-optimised-for-core-ultra-processors-says-intel-124050200482_1.html).', 'news_list': [{'url': 'https://finance.yahoo.com/news/support-aws-yseop-develops-unique-130000171.html', 'title': 'With Support from AWS, Yseop Develops a Unique Generative AI Application for Regulatory Document Generation Across BioPharma', 'summary': "Yseop utilizes AWS to create a new Generative AI application for the Biopharma sector. This application leverages AWS for its scalability and security, and it allows Biopharma companies to bring pharmaceuticals and vaccines to the market more quickly. Yseop's platform integrates LLM models for generating scientific content while meeting the security standards of the pharmaceutical industry.", 'recommend_comment': 'AWS partnership helps Yseop develop an innovative Generative AI application for the BioPharma industry, enabling companies to expedite the delivery of pharmaceuticals and vaccines to market. The integration of LLM models and compliance with stringent pharmaceutical industry security standards make this a valuable solution for BioPharma companies.'}, {'url': 'https://www.business-standard.com/technology/tech-news/over-500-ai-models-are-now-optimised-for-core-ultra-processors-says-intel-124050200482_1.html', 'title': 'Over 500 AI models are now optimised for Core Ultra processors, says Intel', 'summary': 'Intel stated over 500 AI models are optimized for Core Ultra processors. These models are accessible from well-known sources like OpenVINO Model Zoo, Hugging Face, ONNX Model Zoo, and PyTorch.', 'recommend_comment': "Intel's optimization of over 500 AI models for Core Ultra processors provides access to a vast selection of pre-trained models from reputable sources. This optimization enhances the performance and efficiency of AI applications, making it easier for developers to deploy AI solutions on Intel-based hardware."}]}
```
### 第四步：得到一份新鲜出炉的新闻汇总报告📰！

在整个处理过程结束时，您将会看到类似下方的提示，并可以看到完整的报告MarkDown格式结果被输出到屏幕上：

```shell
2024-05-02 21:57:20,521 [INFO] [Markdown Generated]
```

同时，您也可以在您的项目文件夹中找到一份命名格式为`<汇总报告名称> <生成日期>.md`的文件。

大功告成！🎉

---

## 常见问题（FAQ）

**1. 为什么提示请求超时（如：operation timed out，504错误等）或是出现搜索结果为0的情况？**

通常情况下是因为无法请求外网造成的，需要通过配置Proxy代理解决，配置方法请参考上文中SETTINGS.yaml的PROXY配置项

**2. 我用的国内模型，为什么还需要配置Proxy？**

本项目默认使用的搜索工具是外网的搜索工具，所以即使模型本身不存在请求访问限制的问题，也需要使用Proxy代理。

**3. 我机子上开着VPN或者其他代理软件呢，为什么还需要配置Proxy？**

因为大部分情况下，在代理软件没有开启特定的全局系统请求代理模式（如Clash的TUN模式）前，Python脚本在运行时，不会使用代理软件在本地启动的代理服务接口来发起网络请求，而是会直接对目标网址进行请求。因此，需要通过配置Proxy来帮助Python脚本调用代理软件在本地启动的代理服务接口。

以Clash客户端为例，你可以从这个位置找到代理服务的端口：

<img width="320" alt="image" src="https://github.com/AgentEra/Agently-Daily-News-Collector/assets/4413155/b94774be-1a9f-4be1-9071-96131eecf4fd">

根据上图，本地的Proxy服务地址应该为http://127.0.0.1:7890

**4. 我自己有更好用的搜索/浏览工具，我能不能干脆直接修改掉默认的搜索或者浏览工具？**

当然可以，我们在项目中对不同的模块都做了解耦，要修改搜索工具，只需要修改/workflows/tools/search.py文件即可，而要修改浏览工具，只需要修改/workflows/tools/browse.py文件即可。

我们也非常欢迎您将自己修改优化的好用的工具PR给项目，分享给更多的人使用，这类贡献者我们还会在项目首页进行署名感谢！

**5. 都说到这里了，我还能修改/定制/优化哪些地方？**

您可以修改的内容包括：

1. /workflows 文件夹中的处理工作流程，比如，添加一个愚人节处理工作流，来生成洋葱新闻
2. /workflows/tools 文件夹中的搜索和浏览工具，或是结合新增处理工作流，添加更多你觉得有用的工具
3. /prompts 文件夹中的所有Prompt YAML文件，这些文件都非常易读易修改，欢迎您修改出更好的Prompt，或是简单地将英文Prompt调整为中文

---

## 主要依赖说明

- Agently AI应用开发框架：https://github.com/Maplemx/Agently | https://pypi.org/project/Agently/ | http://Agently.cn
- duckduckgo-search: https://pypi.org/project/duckduckgo-search/
- BeautifulSoup4: https://pypi.org/project/beautifulsoup4/
- PyYAML: https://pypi.org/project/pyyaml/

---

如果您喜欢这个项目，请为本项目以及[Agently框架主仓库](https://github.com/Maplemx/Agently)点亮⭐️。

如果您希望了解更多关于本项目的线上产品化版本信息，欢迎通过下面的方式加入我们的讨论群，我们将在近期组织线上产品化版本的测试。

> 💡 意见反馈/Bug提交: [Report Issues Here](https://github.com/AgentEra/Agently-Daily-News-Collector/issues)
>
> 📧 联系我们: [developer@agently.cn](mailto:developer@agently.cn)
>
> 💬 加入微信讨论群:
>
>  [点击这里填写申请表](https://doc.weixin.qq.com/forms/AIoA8gcHAFMAScAhgZQABIlW6tV3l7QQf)或扫描下方二维码申请入群
>
> <img width="120" alt="image" src="https://github.com/Maplemx/Agently/assets/4413155/fb95e15e-c6bd-4dd4-8fc9-99285df9d443">
