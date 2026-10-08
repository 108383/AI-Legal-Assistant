"""
对话管理器：负责会话管理、概述生成、记忆持久化
"""
import os
import uuid
import sqlite3
from pathlib import Path

from typing import Generator, Dict, Optional,List
from langgraph.checkpoint.sqlite import SqliteSaver
from agent.react_agent import ReactAgent
from utils.logger_handler import logger
from utils.overview_tool import OverviewService


class ChatManager:
    def __init__(self, history_dir: str = "history"):
        self.history_dir = history_dir
        os.makedirs(history_dir, exist_ok=True)

        self.overview_service = OverviewService()
        self.agents: Dict[str, ReactAgent] = {}
        self.sessions: Dict[str, dict] = {}

    def create_session(self, first_query: str) -> str:
        """
        创建新会话，自动生成概述并初始化记忆
        :param first_query: 用户首次提问
        :return: session_id（用于后续对话）
        """
        overview = self.overview_service.generate_overview(first_query)

        import re
        safe_overview = re.sub(r'[^\w\u4e00-\u9fff]', '_', overview)

        session_id = f"{safe_overview}_{uuid.uuid4().hex[:4]}"

        db_path = os.path.join(self.history_dir, f"{session_id}.sqlite")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=DELETE")
        checkpointer = SqliteSaver(conn)
        checkpointer.setup()

        agent = ReactAgent(checkpointer=checkpointer)
        self.agents[session_id] = agent

        self.sessions[session_id] = {
            "session_id": session_id,
            "overview": overview,
            "first_query": first_query,
            "db_path": db_path,
            "created_at": self._get_timestamp()
        }

        return session_id

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """获取会话信息（概述等）"""
        return self.sessions.get(session_id)

    def list_sessions(self) -> list:
        """列出所有会话"""
        return list(self.sessions.values())

    def delete_session(self, session_id: str) -> bool:
        """Delete only a validated history file, closing its live connection first."""
        root = Path(self.history_dir).resolve()
        path = (root / f"{session_id}.sqlite").resolve()
        if path.parent != root or not path.is_file():
            return False
        agent = self.agents.pop(session_id, None)
        if agent is not None and agent.checkpointer is not None:
            agent.checkpointer.conn.close()
        path.unlink()
        self.sessions.pop(session_id, None)
        return True

    def scan_history_files(self) -> List[dict]:
        """
        扫描 history 目录下所有数据库文件，返回会话列表
        """
        sessions = []
        for filename in os.listdir(self.history_dir):
            if filename.endswith('.sqlite'):
                session_id = filename.replace('.sqlite', '')
                db_path = os.path.join(self.history_dir, filename)

                overview = self._extract_overview_from_db(db_path, session_id)
                created_at = self._extract_created_at(db_path)

                sessions.append({
                    "session_id": session_id,
                    "overview": overview,
                    "db_path": db_path,
                    "created_at": created_at
                })

        sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return sessions

    def load_history_messages(self, session_id: str) -> List[dict]:
        """
        从数据库加载历史消息（使用 LangGraph 官方 API 读取，自动反序列化）
        """
        db_path = os.path.join(self.history_dir, f"{session_id}.sqlite")
        if not os.path.exists(db_path):
            return []

        messages = []
        conn = None
        try:
            conn = sqlite3.connect(db_path, check_same_thread=False)
            checkpointer = SqliteSaver(conn)
            checkpointer.setup()

            config = {"configurable": {"thread_id": session_id}}
            checkpoint_tuple = checkpointer.get_tuple(config)

            if checkpoint_tuple:

                channel_values = checkpoint_tuple.checkpoint.get("channel_values", {})
                raw_messages = channel_values.get("messages", [])
                logger.info(f"[history] 读取会话 {session_id}，共 {len(raw_messages)} 条原始消息")
                for msg in channel_values.get("messages", []):
                    msg_type = getattr(msg, "type", None)
                    content = getattr(msg, "content", "")
                    if not content:
                        continue
                    if msg_type == "human":
                        messages.append({"role": "user", "content": content})
                    elif msg_type == "ai":
                        messages.append({"role": "assistant", "content": content})
        except Exception as e:
            print(f"加载历史消息失败: {e}")
        finally:
            if conn:
                conn.close()

        return messages

    def chat_stream(self, session_id: str, query: str) -> Generator[str, None, None]:
        """
        发送消息并获取流式回复
        :param session_id: 会话ID
        :param query: 用户问题
        :return: 流式响应生成器
        """
        if session_id not in self.agents:
            self._load_session(session_id)

        agent = self.agents[session_id]
        return agent.execute_stream(query, thread_id=session_id)

    def _load_session(self, session_id: str):
        """从数据库加载已存在的会话"""
        db_path = os.path.join(self.history_dir, f"{session_id}.sqlite")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=DELETE")
            checkpointer = SqliteSaver(conn)
            checkpointer.setup()
            self.agents[session_id] = ReactAgent(checkpointer=checkpointer)

    @staticmethod
    def _extract_overview_from_db(db_path: str, session_id: str) -> str:
        """从session_id提取概述部分"""
        parts = session_id.split('_')
        if len(parts) >= 2:
            overview = '_'.join(parts[:-1])
            return overview.replace('_', '') if overview else session_id
        return session_id

    @staticmethod
    def _extract_created_at(db_path: str) -> str:
        """获取文件创建时间"""
        import os
        from datetime import datetime
        timestamp = os.path.getctime(db_path)
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _get_timestamp() -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
