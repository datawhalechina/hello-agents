# %% [markdown]
# # ========================================
# # 情感分析助手
# # ========================================

# %% [markdown]
# 

# %%
from hello_agents import SimpleAgent, HelloAgentsLLM, ToolRegistry
from hello_agents.tools import Tool, ToolParameter, ToolRegistry
from typing import Dict, Any, List
import os
import pandas as pd
import re
from paddlenlp import Taskflow



# %%

os.environ["LLM_API_KEY"] = ""  # 你自己的
os.environ["LLM_BASE_URL"] = "https://api-inference.modelscope.cn/v1"
os.environ["LLM_TIMEOUT"] = "60"


# %% [markdown]
# # ========================================
# # 1. 定义代码分析工具
# # ========================================

# %% [markdown]
# 文本清洗

# %%
class ProcessChatHistoryTool(Tool):
    """
    导入并清洗微信或QQ的文本聊天记录
    继承 Tool 抽象类，实现 run、get_parameters 方法
    """
    def __init__(self):
        super().__init__(
            name="process_chat_history",
            description="读取微信/QQ聊天记录TXT文件，自动清洗，返回结构化DataFrame"
        )

    def run(self, parameters: Dict[str, Any]) -> pd.DataFrame:
        """
        工具执行入口
        :param parameters: 外部传入参数 file_path, chat_type
        :return: 清洗后的 DataFrame
        """
        # 从参数中获取值
        file_path = parameters.get("file_path", "")
        chat_type = parameters.get("chat_type", "wechat")

        messages = []
        pattern = re.compile(r'(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\s+(.+?):\s+(.+)')

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    match = pattern.match(line)
                    if match:
                        time, sender, content = match.groups()

                        # 过滤系统消息
                        if any(keyword in content for keyword in ['[图片]', '[视频]', '撤回了一条消息', '拍了拍']):
                            continue

                        messages.append({
                            'time': time,
                            'sender': sender,
                            'content': content
                        })

            df = pd.DataFrame(messages)
            print(f"✅ 成功导入 {len(df)} 条有效聊天记录！")
            return df

        except Exception as e:
            print(f"❌ 读取文件失败：{str(e)}")
            return pd.DataFrame()

    def get_parameters(self) -> List[ToolParameter]:
        """
        定义工具参数
        """
        return [
            ToolParameter(
                name="file_path",
                type="string",
                description="聊天记录txt文件路径",
                required=True
            ),
            ToolParameter(
                name="chat_type",
                type="string",
                description="聊天类型：wechat 或 qq",
                required=False
            )
        ]

# %% [markdown]
# 情感分析

# %%
class AnalyzeSentimentAndMoodTool(Tool):
    """使用SKEP-ERNIE模型分析聊天记录情感与心情"""
    
    def __init__(self):
        super().__init__(
            name="analyze_sentiment_and_mood",
            description="分析聊天记录的情感倾向（正面/负面）与心情（开心/生气/平淡）"
        )
        # 初始化模型（只加载一次）
        self.sentiment_analyzer = Taskflow(
            "sentiment_analysis", 
            model="skep_ernie_1.0_large_ch",
        )

    def run(self, parameters: Dict[str, Any]) -> pd.DataFrame:
        df = parameters.get("df", pd.DataFrame())
        
        if df.empty:
            return df

        contents = df['content'].tolist()

        try:
            results = self.sentiment_analyzer(contents)

            sentiments = [res['sentiment_key'] for res in results]
            confidence = [
                res['positive_probs'] if res['sentiment_key'] == 'positive' 
                else 1 - res['positive_probs'] 
                for res in results
            ]

            moods = []
            for res in results:
                if res['sentiment_key'] == 'positive':
                    moods.append('开心/认可')
                else:
                    neg_prob = 1 - res['positive_probs']
                    if neg_prob > 0.8:
                        moods.append('生气/难过')
                    else:
                        moods.append('无奈/平淡')

            df['sentiment'] = sentiments
            df['mood'] = moods
            df['confidence'] = confidence

            print("✅ 情感与心情分析完成！")
            return df

        except Exception as e:
            print(f"❌ 情感分析出错：{e}")
            return df

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="df",
                type="object",
                description="清洗后的聊天记录DataFrame",
                required=True
            )
        ]

# %% [markdown]
# 情感统计

# %%
class SummarizeEmotionStatsTool(Tool):
    """统计聊天情感数据，生成报告与结构化结果"""
    
    def __init__(self):
        super().__init__(
            name="summarize_emotion_stats",
            description="统计情感分析结果，计算开心/生气数量与占比，返回报告字典"
        )

    def run(self, parameters: Dict[str, Any]) -> dict:
        df = parameters.get("df", pd.DataFrame())
        sender_name = parameters.get("sender_name", None)
        
        if df.empty or 'sentiment' not in df.columns:
            print("❌ 数据为空或尚未进行情感分析，请先运行前两个工具！")
            return {}

        if sender_name:
            analysis_df = df[df['sender'] == sender_name].copy()
            if analysis_df.empty:
                print(f"⚠️ 未找到 {sender_name} 的聊天记录")
                return {}
            print(f"🔍 正在统计 {sender_name} 的情感数据...")
        else:
            analysis_df = df.copy()
            print("🔍 正在统计全员的情感数据...")

        total_messages = len(analysis_df)
        happy_count = len(analysis_df[analysis_df['sentiment'] == 'positive'])
        angry_count = len(analysis_df[analysis_df['sentiment'] == 'negative'])

        happy_ratio = round((happy_count / total_messages) * 100, 2) if total_messages > 0 else 0.0
        angry_ratio = round((angry_count / total_messages) * 100, 2) if total_messages > 0 else 0.0

        print("\n" + "="*30)
        print(f"📊 【情感统计报告】")
        print(f"总有效发言数: {total_messages} 条")
        print(f"😄 开心/认可: {happy_count} 条 (占比 {happy_ratio}%)")
        print(f"😡 生气/难过: {angry_count} 条 (占比 {angry_ratio}%)")
        print(f"😐 中性/其他: {total_messages - happy_count - angry_count} 条")
        print("="*30 + "\n")

        return {
            'total_messages': total_messages,
            'happy_count': happy_count,
            'angry_count': angry_count,
            'happy_ratio': happy_ratio,
            'angry_ratio': angry_ratio
        }

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="df",
                type="object",
                description="已完成情感分析的 DataFrame",
                required=True
            ),
            ToolParameter(
                name="sender_name",
                type="string",
                description="可选，指定发言者名称",
                required=False
            )
        ]

# %%
class PlotEmotionChartTool(Tool):
    """将情感统计结果绘制成柱状图"""
    
    def __init__(self):
        super().__init__(
            name="plot_emotion_chart",
            description="根据情感统计字典绘制可视化柱状图"
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        stats = parameters.get("stats", {})
        
        if not stats:
            return "⚠️ 无统计数据，无法生成图表"

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei']
        plt.rcParams['axes.unicode_minus'] = False

        labels = ['开心/认可', '生气/难过']
        counts = [stats['happy_count'], stats['angry_count']]
        colors = ['#FF9999', '#66B2FF']

        plt.figure(figsize=(8, 5))
        bars = plt.bar(labels, counts, color=colors)
        plt.title(f"情感分布统计 (总数: {stats['total_messages']}条)", fontsize=15)
        plt.ylabel('发言条数', fontsize=12)

        # 显示数值
        for bar in bars:
            yval = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2, yval + 0.5, int(yval), ha='center', va='bottom', fontsize=12)

        plt.show()
        return "✅ 图表已成功绘制！"

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="stats",
                type="object",
                description="summarize_emotion_stats 函数返回的统计字典",
                required=True
            )
        ]

# %% [markdown]
# # ========================================
# # 2. 创建工具注册表和智能体
# # ========================================

# %%
tool_registry = ToolRegistry()

tool_registry.register_tool(ProcessChatHistoryTool())
tool_registry.register_tool(AnalyzeSentimentAndMoodTool())
tool_registry.register_tool(SummarizeEmotionStatsTool())
tool_registry.register_tool(PlotEmotionChartTool())

print("✅ 所有情感分析工具注册成功！")

# %% [markdown]
# # ========================================
# # 3.初始化大模型
# # ========================================

# %%
print(">>> 实际读取到的 Base URL 是：", repr(os.getenv("LLM_BASE_URL")))
llm = HelloAgentsLLM(
	 model_id="Qwen/Qwen2.5-72B-Instruct",  # ✅ 使用支持的 72B 模型，注意大写 Q
	 api_key="",
	base_url="https://api-inference.modelscope.cn/v1"
	)
	# 打印底层客户端的真实 URL，确认是否生效
print("底层客户端 Base URL:", llm._client.base_url)

# %% [markdown]
# # ========================================
# # 4. 定义系统提示词
# # ========================================

# %%
system_prompt = """你是一位拥有10年经验的亲密关系心理学专家,同时也是一位高情商沟通教练。你的任务是深入分析用户提供的聊天记录，并提供极具洞察力的情感分析报告。

请严格按照以下步骤执行：
1. **语境理解**：结合上下文，精准识别对话双方的关系阶段（如暧昧期、热恋期、冷战期）。
2. **潜台词挖掘**：不要只看表面文字，要深度解读对方话语背后的真实情绪、需求和未说出口的潜台词。
3. **情感量化**：基于对话的亲密度、回应速度和情绪价值,给出一个0-100分的“心动指数”。
4. **回复建议**：针对当前的对话僵局或话题,提供3种不同风格(如:幽默风趣、深情走心、推拉试探）的高情商回复话术。

请以Markdown格式输出报告,报告结构必须包含：
-  **心动指数**:(给出具体分数及简短评语)
-  **深度解读**:(分析对方的心理状态和潜在意图)
-  **潜台词翻译**:(挑选1-2句关键对话进行“翻译”)
-  **高情商回复**:(提供3个具体的回复选项)
"""

# %% [markdown]
# # ========================================
# # 5.生成智能体
# # ========================================

# %%
agent = SimpleAgent(
name="情感分析助手",
llm=llm,
system_prompt=system_prompt,
tool_registry=tool_registry
)

# %% [markdown]
# # ========================================
# # 6. 运行示例
# # ========================================

# %%
with open("data/1.txt","r",encoding="utf-8") as f:
  talktxt=f.read()

print('---------------聊天记录---------------')
print(talktxt)

print('--------------开始分析记录--------------')
print("当前 LLM_BASE_URL:", repr(os.environ["LLM_BASE_URL"]))
result=agent.run(talktxt)
print(result)
print('---------------保存结果---------------')
with open("outputs/review_report.md", "w", encoding="utf-8") as f:
  f.write(result)
print("\n审查报告已保存到 outputs/review_report.md")


