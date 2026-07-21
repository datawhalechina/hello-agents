from dotenv import load_dotenv

from my_llm import MyLLM



load_dotenv()

llm = MyLLM(provider="modelscope")
messages = [{"role" : "user","content" : "请介绍一下你自己"}]
response = llm.think(messages=messages)
print("ModelScope Response:")
for chunk in response:
    # chunk在my_llm库中已经打印过一遍，这里只需要pass即可
    # print(chunk, end="", flush=True)
    pass
