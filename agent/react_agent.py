from langchain.agents import create_agent
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from agent.tools.agent_tools import (rag_summarize, search_tool)
from agent.tools.middleware import monitor_tool, log_before_model
from langgraph.checkpoint.sqlite import SqliteSaver


class ReactAgent:
    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer

        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[rag_summarize, search_tool],
            middleware=[monitor_tool, log_before_model],
            checkpointer=self.checkpointer
        )

    def execute_stream(self, query: str, thread_id: str = "default"):
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }

        input_dict = {
            "messages": [
                {"role": "user", "content": query},
            ]
        }

        for chunk in self.agent.stream(input_dict, config, stream_mode="values"):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == '__main__':
    agent = ReactAgent()

    for chunk in agent.execute_stream("女方主动要离婚,男方必须同意吗?离婚必须分走一半财产吗?有没有相关案例"):
        print(chunk, end='', flush=True)