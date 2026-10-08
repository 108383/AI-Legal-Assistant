"""
问题概述服务：将用户问题自动总结为10字以内的简短标题
"""
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model


class OverviewService:
    def __init__(self):
        self.prompt_template = PromptTemplate.from_template(
            "请将以下用户法律问题概括为10个字以内的简短标题，只输出标题，不要任何解释：\n用户问题：{query}"
        )
        self.chain = self.prompt_template | chat_model | StrOutputParser()

    def generate_overview(self, query: str) -> str:
        """
        生成用户问题的简短概述
        :param query: 用户原始问题
        :return: 10字以内的概述标题
        """
        overview = self.chain.invoke({"query": query})
        cleaned = overview.strip().strip('"').strip("'")
        return cleaned[:10] if len(cleaned) > 10 else cleaned