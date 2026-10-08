import os
import random
from langchain_tavily import TavilySearch
from langchain_core.tools import tool
from rag.rag_service import RagSummarizeService
from utils.path_tool import get_abs_path
from utils.logger_handler import logger
from dotenv import load_dotenv

load_dotenv()

rag = RagSummarizeService()

tavily_search = TavilySearch(max_results=5, topic="general")


@tool(description="从向量存储中检索参考资料")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)


@tool(description="从网上搜索相关案例")
def search_tool(query: str) -> str:
    return tavily_search.invoke({"query": query})


if __name__ == '__main__':
    print("hello world")

