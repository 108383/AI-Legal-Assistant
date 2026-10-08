# 智律 Web 前端

## 启动

首次运行时确认原项目依赖已经安装，并补充 Web 服务依赖：

```powershell
pip install -r requirements-web.txt
```

将 `.env.example` 复制为 `.env`，填写自己的 DashScope 与 Tavily 密钥。不要把 `.env` 上传到代码仓库。

在项目根目录运行：

```powershell
python web_app.py
```

然后访问 `http://127.0.0.1:8000`。

## 已实现功能

- 新建法律咨询
- 自动创建并持久化会话
- 历史会话列表、切换与消息恢复
- 复用原项目的本地法规 RAG 与 Tavily 联网搜索 Agent
- SSE 流式回答和停止生成
- Markdown 回答展示
- 常见问题快捷入口
- 桌面端和移动端自适应

原来的 `streamlit.py` 保留不变，可继续使用 `streamlit run streamlit.py` 启动。

## 部署提示

- 线上部署时将 `web_app.py` 的启动地址改为 `0.0.0.0`，或使用 `uvicorn web_app:app --host 0.0.0.0 --port 8000`。
- 建议在 Nginx 中关闭 SSE 响应缓冲，并配置 HTTPS。
- 当前项目的历史记录保存在 `history` 目录，部署时需要挂载持久化磁盘。
