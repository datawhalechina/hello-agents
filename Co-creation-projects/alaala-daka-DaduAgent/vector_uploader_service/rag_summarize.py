from langchain_chroma import Chroma
from vector_uploader_service.file_uploader import File_Uploader
from tool.config_handler import Rag_Config,Prompt_Config
from tool.path_tool import get_abs_path
from factory.model_generator import create_ragmodel, create_rerankmodel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
"""
筛选Chroma库返回结果,总结并以string反馈
"""
def prompt_check(mes):
    print('='*20)
    print(mes.to_string())
    print('='*20)
    return mes
class _Rag_Summarize(File_Uploader):
    def __init__(self) -> None:
        super().__init__()
        self.retriever=self.get_retriever()
        self.summarize_model=create_ragmodel()
        self.reranker=create_rerankmodel()
        self.retrieve_k=int(Rag_Config.get("retrieve_k", 10))
        self.rerank_top_k=int(Rag_Config.get("rerank_top_k", 5))
        rag_prompt_path = get_abs_path(Prompt_Config['rag_prompt_path'])
        self.sys_prompt=open(rag_prompt_path,'r',encoding='utf-8').read()
        self.chat_tem=ChatPromptTemplate(
            [
                ('system',self.sys_prompt),
                ('system',"[参考资料]{reference}"),
                ('human',"{input}"),
            ]
        )
        self.rag_sum_chain=self.chat_tem|self.summarize_model|StrOutputParser()
    def get_rag_content(self,input:str)->str:
        """
        召回 retrieve_k 条 → Reranker 重排 → 保留 rerank_top_k 条，带序号返回。
        序号对齐 rag_prompt.txt 的「参考资料第X条」来源标注要求。
        """
        hits=self.chroma.similarity_search_with_score(query=input,k=self.retrieve_k)
        docs=[doc.page_content for doc,_ in hits]
        if not docs:
            return ''
        if self.reranker and len(docs)>1:
            ranked=self.reranker.rerank(input,docs,top_n=self.rerank_top_k)
        else:
            ranked=docs[:self.rerank_top_k]
        return '\n'.join(f'[{i}] {doc}' for i,doc in enumerate(ranked,start=1))
    def model_summary(self,input:str):
        reference=self.get_rag_content(input)
        summary=self.rag_sum_chain.invoke({'reference':reference,'input':input})
        return summary

Rag_Summarize=_Rag_Summarize()