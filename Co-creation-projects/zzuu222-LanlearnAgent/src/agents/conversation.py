from hello_agents import SimpleAgent
from ..tools import tools
import time

SENTENCE_AGENT_PROMPT = """你是一位专业的口语老师，任务是根据对话场景和相关信息选择合适的措辞来和用户对话。
并且根据对话轮次和上一轮的用户话语来决定何时结束对话。系统中有审核员会对你的回复进行审核，如果有问题会提示你修改。

【对话场景设定】
- 语言: {language}
- 难度: {difficulty}
- 偏好: {preference}

【难度设定】
- 入门: 对应小学难度
- 初级: 对应初中和高中难度
- 中级: 对应四级和六级难度
- 高级: 对应六级以上难度

【重要】
- 当前对话轮次接近总轮次时，选择合适时机结束对话
- 当用户回复表示想要结束对话时，回复合适的结束语句
- 结束对话时根据对话主题回复简单的结束语并在最后加上字符串"--thisisend--"
- 不要说"我是AI"或"我是语言模型"
- 要像真实的老师一样耐心
- 不要使用emoji
- 回复要有人情味,不要太机械
- 回复以对话为目的，不要对对话中提及的对象做过多说明
- 回复可以适度多包含此难度对应的语法和单词，作为学习使用
- 当用户输入包含语法错误或单词拼写错误时，适当纠正并给出正确的表达方式
- 如果审核员提示回复语句有错误，请纠正后再回复

对话示例：
用户: "It's a nice day!"
回复: "Yes, its sunny."

结束示例：
用户: "I gotta go!"
回复: "Bey, see you later.--thisisend--"
"""

SEARCH_AGENT_PROMPT = """你是一个信息搜索专家，负责根据用户输入的语句判断是否需要搜索相关信息来辅助对话。

回复格式要求:
如果需要搜索，回复:`[True, "搜索查询语句"]`
如果不需要搜索，回复:`[False, ""]`

回复示例：
[True, "英伟达最新型的GPU有哪些？"]
[False, ""]
"""

CONFIRM_AGENT_PROMPT = """你是对话审核专家，判断回复的正确性。

【要求】
- 根据用户输入判断待回复语句中是否存在语法和单词拼写错误
- 判断待回复语句是否符合用户输入
- 如果有问题，描述问题并提出修改意见
- 待回复语句中可能会有字符串"--thisisend--"，如果有请忽略，这是特定符号。

【回复格式要求】
如果待回复语句没有问题，回复:`[True, ""]`
如果待回复语句有问题，回复:`[False, "问题描述和修改意见"]`
【回复示例】
[True, ""]
[False, "待回复语句中存在语法错误，建议将'He go to school'修改为'He goes to school'"]
"""

SUMMARY_AGENT_PROMPT = """你是一个总结专家，负责对话信息生成总结。可以使用中文。

【当前对话场景】
- 语言: {language}
- 难度: {difficulty}
- 偏好: {preference}

【难度设定】
- 入门: 对应小学难度
- 初级: 对应初中和高中难度
- 中级: 对应四级和六级难度
- 高级: 对应六级以上难度

【要求】
- 总结对话中需要注意的语法和易错语法
- 根据当前对话场景下的难度设定，总结较难单词
"""

class SpeakTeacherAgent:
    """对话练习智能体"""
    def __init__(self,llm,language: str, difficulty: str, preference: str):
        self.llm = llm
        self.lan = language
        self.sentences: list(dict(str,str)) = []
        self.prompt = SENTENCE_AGENT_PROMPT.format(
            language=language,
            difficulty=difficulty,
            preference=preference)
        
        self.conversation_agent = SimpleAgent(
            name="专业口语老师",
            llm=self.llm,
            system_prompt=self.prompt)

        self.search_agent = SimpleAgent(
            name="信息搜索专家",
            llm=self.llm,
            system_prompt=SEARCH_AGENT_PROMPT)

        self.confirm_agent = SimpleAgent(
            name="对话审核员",
            llm=self.llm,
            system_prompt=CONFIRM_AGENT_PROMPT
        )

        self.summary_agent = SimpleAgent(
            name="总结专家",
            llm=self.llm,
            system_prompt=SUMMARY_AGENT_PROMPT.format(
                language=language,
                difficulty=difficulty,
                preference=preference)
        )

    def infosearcher(self,user_sentence: str) -> str:
        #根据用户输入决定是否需要调用搜索工具搜索相关的最新消息
        search_prompt = """请根据用户输入判断是否需要搜索相关信息来辅助对话，用户输入: {user_sentence}"""
        search_decision = self.search_agent.run(search_prompt.format(user_sentence=user_sentence))
        if search_decision.startswith("[True"):
            search_query = search_decision.split(",")[1].strip().strip('"').strip('"]')
            try:
                search_result = tools.search(search_query)
            except:
                print("搜索出错，请检查搜索配置")
                return ""
            return search_result
        else:
            return ""
    
    def reply_confirm(self,user_sentence: str,reply_sentence: str) -> str:
        # 确认回复的正确性
        confirm_prompt = f"用户输入: {user_sentence} 待回复语句: {reply_sentence}，请判断待回复语句是否正确。"
        result = self.confirm_agent.run(confirm_prompt)
        if result.startswith("[True"):
            return ""
        else:
            cprom = result.split(",")[1].strip().strip('"').strip('"]')
            return cprom

    def chatter(self,user_sentence: str) -> str:
        # 先调用信息搜索专家决定是否需要搜索
        info = self.infosearcher(user_sentence)
        if info:
            uprompt = f"用户输入: {user_sentence}  相关信息: {info}，请根据用户输入和相关信息生成回复。"
        else:
            uprompt = f"用户输入: {user_sentence}，请根据用户输入和相关信息生成回复。"
        reply = self.conversation_agent.run(uprompt)

        # 调用审核员确认回复的正确性
        replystate = self.confirm_agent.run(user_sentence, reply)
        if replystate:
            reply_confirm_prompt = f"【审核员提示】:{replystate}"
            reply = self.conversation_agent.run(reply_confirm_prompt)

        around = {"user": user_sentence,"reply": reply.split("--thisisend--")[0]}
        self.sentences.append(around)
        return reply
        
    def summary(self):
        # 生成总结
        summary_prompt = f"请根据当前对话内容生成总结，当前对话内容为: {self.sentences}"
        summary = self.summary_agent.run(summary_prompt)
        return summary
    
    def letstalk(self):
        talk_round = []
        # 开始对话

        while True:
            talk_round.append(len(self.sentences)+1)
            print(f"第{len(talk_round)}轮对话")

            usertalk = str(input("请输入句子进行对话："))
            if usertalk == "":
                if len(talk_round) == 1:
                    usertalk = "Hello! Who are you?"
                else:
                    usertalk = ""
            
            result = self.chatter(usertalk)
            if "--thisisend--" in result:
                print(result.split("--thisisend--")[0])
                break
            print(result)
        
        # 总结对话
        summary = self.summary()
        print("对话总结如下：")
        print(summary)

        # 将对话和最终报告生成文件进行存储
        thetime = time.strftime("%Y-%m-%d %H-%M")
        sents = ""
        for s in self.sentences:
            sents += f"用户: {s['user']}\n助手: {s['reply']}\n"
        sents += f"\n对话总结如下：\n{summary}\n"

        try:
            with open(f"./hello-agent-lanlearn/Co-creation-projects/zzuu222-LanlearnAgent/output/{thetime} {self.lan}.md","w",encoding="utf-8") as f:
                f.write(sents)
        except:
            print("写入失败")
            return False
        print("写入完成")
        return True
            
        
