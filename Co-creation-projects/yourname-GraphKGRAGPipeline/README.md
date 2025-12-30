# GraphKGRAGPipeline（GraphRAG/LightRAG 基本跑通脚手架）

> 目标：先用“图片定位/识别 + LLM抽取”跑通 **LPG（Labeled Property Graph，属性图谱）** 的全链路：
> - 实体：团体 / 人 / 事件 / 位置（可扩展）
> - data gleaning（从文本与图谱结构推理补全信息）
> - 文章 → 知识图谱（节点/边带属性）
> - 查询（实体检索、邻域、路径、社区）
> - 社区检测 + 层级化总结 + 推理额外信息
> - “超越文本匹配”（图结构 + 语义相似度检索）

## 目录结构

```
yourname-GraphKGRAGPipeline/
  README.md
  requirements.txt
  .env.example
  main.ipynb
  data/
    sample_article.md
  src/
    app.py
    schema.py
    llm.py
    ocr.py
    extract.py
    graph_store.py
    gleaning.py
    community.py
    query.py
    integrations/
      graphrag_runner.py
      lightrag_runner.py
```

## 快速开始（无API也可跑）

1) 安装依赖

```bash
pip install -r requirements.txt
```

2) 直接跑 demo（不调用真实LLM，使用内置“规则/启发式抽取”）

```bash
python -m src.app demo --input data/sample_article.md --out outputs
```

你将得到：
- `outputs/graph.json`：抽取后的属性图谱（LPG）
- `outputs/communities.json`：社区检测结果
- `outputs/hierarchy_summary.md`：层级化总结（无LLM时是启发式）

## 启用 LLM 抽取（可选）

复制 `.env.example` 为 `.env`，按需填写：

- OpenAI 兼容接口：`OPENAI_API_KEY`、`OPENAI_BASE_URL`、`OPENAI_MODEL`
- 或 Ollama：`OLLAMA_BASE_URL`、`OLLAMA_MODEL`

然后运行：

```bash
python -m src.app demo --input data/sample_article.md --out outputs --llm
```

## 图片 OCR（可选）

当前 `src/ocr.py` 提供可插拔 OCR：
- `pytesseract`：轻量，但需要本机安装 Tesseract
- `paddleocr`：可返回框（定位）+ 文本（更符合“图片识别定位”）

示例（如果你在 `data/` 放入图片）：

```bash
python -m src.app ocr --image data/your_image.png --out outputs
```

## GraphRAG / LightRAG（可选接入）

本项目先用“自实现的 GraphRAG 核心思路”跑通：
- 构图（LPG）
- 社区检测
- 层级总结
- 图谱查询 + 语义检索

如果你要接入官方/第三方的 `graphrag` 或 `lightrag` 包：

```bash
python -m src.integrations.graphrag_runner --help
python -m src.integrations.lightrag_runner --help
```

（它们会检测你是否已安装对应包，并提示下一步安装与命令。）

## 作者

- 你的名字 / GitHub: @yourname
