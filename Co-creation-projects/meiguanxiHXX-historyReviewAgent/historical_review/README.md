# 多角色历史辩论智能体

立场预设：**官修史书不等于真相**；须联系**权力、文官书写、时代政治与语境**，对记载抱**怀疑目光**；野史笔记虽多不可靠，可与正史**对读缝隙**。通用模型作知识底座，本模块用 **五角色人设** + **终局综合模板** 落实上述取向；可选 **维基 + 检索** 作附录（可 `--no-evidence` 关闭）。

## 角色（五方交锋）

1. **官修史书与王朝叙事** — 复述常见官修框架，同时系统揭示其**政治文本**性质（胜利者、文官、避讳、曲笔），**禁止**把正史当免检真理。  
2. **野史与边缘叙事** — 笔记、谣谚、小说家言等：低可信度但与正史对读可照出沉默与矛盾。  
3. **政治语境与权力结构** — 谁掌权、谁修史、何种记载对当权「最省事」；何种记述显得**蹊跷**。  
4. **域外与他者视角** — 外典亦带偏见，但有时能照见官修盲区。  
5. **蹊跷与阴谋论辨析** — 区分地摊阴谋论与**史学上体面的怀疑**；「于谁有利、于谁消失」。

流程：**第一轮** 五方各陈 → **秘书摘要** → **第二轮** 碰撞 → **终局综合**（不写「唯一真相」，而写：为何不可轻信官修、野史能补什么、政治下何处蹊跷、暂可采纳的谦逊判断、阴谋论 vs 正当怀疑）。  

## 在 IDE 里消除 `from historical_review` 标红

如果你是直接打开本项目目录，IDE 仍然标红 `from historical_review`，通常是因为没有做可编辑安装。任选其一即可：

**方式 A（推荐）**：在项目根目录对当前虚拟环境做可编辑安装（与运行脚本用同一个解释器）：

```bash
pip install -r requirements.txt
pip install -e .
```

**方式 B（IntelliJ IDEA / PyCharm）**：在工程树中右键 **项目根目录** → **Mark Directory as** → **Sources Root**（标记为源代码根）。

然后 **File → Invalidate Caches** 若仍标红，确认 **Project Interpreter** 选的是已安装依赖的同一环境。

## Web 界面（推荐）

深色「史观交锋」主题页，可在浏览器内配置 Key、Base URL、模型、温度、超时、是否启用考据附录，并可选将配置写入本机 `localStorage`。

```bash
pip install -r requirements.txt
pip install -e .
python run_web.py
```

浏览器打开 **http://127.0.0.1:8777** 。服务端会读取项目根目录 `.env`（可与页面填写的 Key 互补：页面留空则用环境变量）。

等价命令：`uvicorn historical_review.web.app:app --reload --host 127.0.0.1 --port 8777`（需在项目根目录执行，保证能 `import historical_review`）。

## 命令行运行

```bash
pip install -r requirements.txt
pip install -e .
cp .env.example .env   # OpenRouter 等
```

默认会**交互询问**：历史议题（可回车用示例）、是否抓取维基+检索附录、是否确认开始（约 **12** 次 LLM 调用）。

```bash
python -m historical_review.run_agent
python -m historical_review.run_agent "你的历史议题"
```

非交互（脚本/CI，不再出现选择提示）：

```bash
python -m historical_review.run_agent -y
python -m historical_review.run_agent -y "你的议题"
python -m historical_review.run_agent -y --no-evidence "你的议题"
```

## 说明

输出为 **思辨与方法论训练**，非学术鉴定或考试标准答案；请勿将终局综合当作唯一真理表述。
