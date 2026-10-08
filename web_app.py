"""智律 Web 前端服务。

运行方式：python web_app.py
浏览器访问：http://127.0.0.1:8000
"""

import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from utils.chat_manager import ChatManager


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "web" / "static"

app = FastAPI(title="智律 AI 智能法律咨询系统", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

chat_manager = ChatManager(history_dir=str(ROOT / "history"))
session_locks: dict[str, asyncio.Lock] = {}
END_OF_STREAM = object()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    session_id: str | None = None


def event(event_name: str, data: dict) -> str:
    return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def next_chunk(iterator):
    return next(iterator, END_OF_STREAM)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/sessions")
def list_sessions() -> dict:
    return {"sessions": [{k: v for k, v in item.items() if k != "db_path"}
                         for item in chat_manager.scan_history_files()]}


@app.get("/api/sessions/{session_id}/messages")
def get_messages(session_id: str) -> dict:
    sessions = {item["session_id"] for item in chat_manager.scan_history_files()}
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session_id": session_id, "messages": chat_manager.load_history_messages(session_id)}


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> StreamingResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="问题不能为空")
    if payload.session_id and payload.session_id not in {s["session_id"] for s in chat_manager.scan_history_files()}:
        raise HTTPException(404, "会话不存在")

    async def generate() -> AsyncGenerator[str, None]:
        session_id = payload.session_id
        try:
            if session_id is None:
                session_id = await asyncio.to_thread(chat_manager.create_session, message)
                yield event("session", {"session_id": session_id})

            lock = session_locks.setdefault(session_id, asyncio.Lock())
            if lock.locked():
                yield event("error", {"message": "当前会话正在生成回答，请稍后再试。"})
                return

            async with lock:
                iterator = chat_manager.chat_stream(session_id, message)
                while True:
                    chunk = await asyncio.to_thread(next_chunk, iterator)
                    if chunk is END_OF_STREAM:
                        break
                    if chunk:
                        yield event("delta", {"content": chunk})

            yield event("done", {"session_id": session_id})
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            yield event("error", {"message": f"生成回答失败：{exc}"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    lock = session_locks.setdefault(session_id, asyncio.Lock())
    if lock.locked():
        raise HTTPException(409, "会话正在生成回答，请稍后删除")
    async with lock:
        if not chat_manager.delete_session(session_id):
            raise HTTPException(404, "会话不存在")
    return {"success": True}


if __name__ == "__main__":
    uvicorn.run("web_app:app", host="127.0.0.1", port=8000, reload=False)
