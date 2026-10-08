"""
总结服务类:用户提问,搜索参考资料,将提问和参考模型提交给模型,让模型总结回复
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

from model.factory import chat_model
from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompts
from langchain_core.prompts import PromptTemplate



def print_prompt(prompt):
    print("="*20)
    print(prompt.to_string())
    print("="*20)
    return prompt

class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

    # 初始化链式调用
    def _init_chain(self):
        chain = self.prompt_template | print_prompt | self.model | StrOutputParser()
        return chain

    # 搜索参考资料
    def retriever_docs(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)

    # 联想总结
    def rag_summarize(self, query: str) -> str:
        context_docs = self.retriever_docs(query)

        context = ""
        counter = 0
        for doc in context_docs:
            counter += 1
            context += f"【参考资料{counter}】:参考资料：{doc.page_content} | 参考源数据：{doc.metadata}\n"

        return self.chain.invoke(
            {
                "input":query,
                "context":context
            }
        )

if __name__ == '__main__':
    rag = RagSummarizeService()

    print(rag.rag_summarize("我家狗被毒死了,我怀疑是邻居投的毒,我可以告他吗"))
