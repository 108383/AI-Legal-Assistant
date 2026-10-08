# 智律 AI 法律咨询

基于 FastAPI、LangChain、Chroma 与 SQLite 的法律信息助手。支持本地法规 RAG、Tavily 联网案例检索、流式回答、新建咨询、历史恢复和确认删除。

## 启动

Python 3.13+。安装依赖、复制 `.env.example` 为 `.env` 并填写 DashScope 与 Tavily 密钥：

```bash
pip install -r requirements.txt
python web_app.py
```

访问 http://127.0.0.1:8000。首次使用需初始化本地法规库：

```bash
python -m rag.vector_store
```

法规文本在 `data`，请自行确认法规的有效性与适用范围。索引、MD5 缓存、SQLite 历史和日志均在本地生成，不上传 Git。原 Streamlit 页面在本地保留，不上传。

## 会话管理

- GET `/api/sessions`：会话列表。
- GET `/api/sessions/{id}/messages`：历史消息。
- POST `/api/chat`：SSE 事件流。
- DELETE `/api/sessions/{id}`：永久删除选中的会话；正在生成时禁止删除。

前端删除需确认。删除无法恢复。默认部署为单用户演示，公开前请添加身份认证、会话归属校验、限流、HTTPS 和持久化磁盘。停止生成只中止浏览器读取，不保证立刻取消服务端模型调用。

回答仅供法律信息参考，不构成律师意见。
