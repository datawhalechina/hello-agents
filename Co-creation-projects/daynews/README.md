<div style="text-align:center">

<h1>Agently-Daily-News-Collector</h1>

<b>English | <a href = "./README_CN.md">中文说明</a></b>

</div>

**Agently Daily News Collector** is an open-source LLM based automatically news collecting workflow showcase project powered by [**_<font color = "red">Agent</font><font color = "blue">ly</font>_** AI application development framework](https://github.com/Maplemx/Agently).

You can use this project to generate almost any topic of news collection. All you need to do is simply input the field topic of your news collection. Then you wait and the AI agents will do their jobs automatically until a high quality news collection is generated and saved into a markdown file.

News collection file examples:

`MarkDown File` [Lastest Updated on AI Models 2024-05-02](https://github.com/AgentEra/Agently-Daily-News-Collector/blob/main/examples/Latest%20Updates%20on%20AI%20Models2024-05-02.md)

`PDF File` [Lastest Updated on AI Models 2024-05-02](https://github.com/AgentEra/Agently-Daily-News-Collector/blob/main/examples/Latest%20Updates%20on%20AI%20Models%202024-05-02.pdf)

> **ℹ️ Notice:**
> 
> Visit https://github.com/Maplemx/Agently if you want to learn more about **_<font color = "red">Agent</font><font color = "blue">ly</font>_** AI Application development framework.

## How to Use

### Step 1: Clone this repo

Run this command in shell:

```shell
git clone git@github.com:AgentEra/Agently-Daily-News-Collector.git
```

### Step 2: Edit settings YAML file

You can find [`SETTINGS.yaml`](https://github.com/AgentEra/Agently-Daily-News-Collector/blob/main/SETTINGS.yaml) file in the project dir.

Input your model's API key and change other settings as your wish.

If you want to use other model, you can read [this document](https://github.com/Maplemx/Agently/blob/main/docs/guidebook/application_development_handbook.ipynb) or [this Agently official website page](http://agently.tech/features/model_request.html) to see how to set the settings.

### Step 3: Start

Because this project is a Python project, you need to install Python first. You can find installation instruction on [Python official website](https://www.python.org/).

At the first time to run this project, you should use this command in shell to download and install dependency packages:

```shell
pip install -r path/to/project/requirements.txt
```

Wait until the dependency packages are installed then use this command in shell to start the generation process.

```shell
python path/to/project/app.py
```

You will see a tip `[Please input the topic of your daily news collection]:`.

Input your topic idea about the field of news that you want to collect, then you're good to go.

During the process, there'll be some logs printed to shell to present what tasks are done like this:

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

Whole process will take some time, so just relax and have some rest☕️.

### Step 4: Get your news collection markdown file!

When the process is done finally, you will see a tip like this with markdown text that generated printed on screen:

```shell
2024-05-02 21:57:20,521 [INFO] [Markdown Generated]
```

Then you can find a markdown file named `<collection name> <generated date>.md` in your project dir.

Enjoy it! 😄

---

## Mainly Dependencies

- **Agently AI Development Framework**: https://github.com/Maplemx/Agently | https://pypi.org/project/Agently/
- **duckduckgo-search**: https://pypi.org/project/duckduckgo-search/
- **BeautifulSoup4**: https://pypi.org/project/beautifulsoup4/
- **PyYAM**L: https://pypi.org/project/pyyaml/

---

Please ⭐️ this repo and [Agently](https://github.com/Maplemx/Agently) main repo if you like it! Thank you very much!

> 💡 Ideas / Bug Report: [Report Issues Here](https://github.com/AgentEra/Agently-Daily-News-Collector/issues)
>
> 📧 Email Us: [developer@agently.cn](mailto:developer@agently.cn)
>
> 👾 Discord Group:
>
> [Click Here to Join](https://discord.gg/4HnarMBpYT) or Scan the QR Code Down Below
>
> <img width="120" alt="image" src="https://github.com/Maplemx/Agently/assets/4413155/089c239c-6133-4844-840c-b48c42ccbad1">
>
> 💬 WeChat Group（加入微信群）:
>
>  [Click Here to Apply](https://doc.weixin.qq.com/forms/AIoA8gcHAFMAScAhgZQABIlW6tV3l7QQf) or Scan the QR Code Down Below
>
> <img width="120" alt="image" src="https://github.com/Maplemx/Agently/assets/4413155/fb95e15e-c6bd-4dd4-8fc9-99285df9d443">