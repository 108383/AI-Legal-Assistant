# 智律 AI 法律咨询系统

面向日常法律信息咨询的 AI 应用。围绕劳动纠纷、消费维权、合同和交通事故等问题，结合本地法律法规知识库与联网资料检索生成回答，并支持连续咨询、历史回顾与会话删除。

项目重点展示法律资料的 RAG 检索、工具调用型智能体、流式 Web 交互，以及基于 SQLite 的会话记忆管理。

## 功能概览

| 功能 | 实现方式 |
| --- | --- |
| 法规知识库 | 加载法律文本，切分后通过 Embedding 写入 Chroma 向量库 |
| RAG 检索与总结 | 检索相关片段，将问题和参考资料提交模型生成总结 |
| 联网案例检索 | 通过 Tavily 搜索公开资料，补充本地法规检索结果 |
| 工具调用型智能体 | LangChain Agent 编排本地资料检索与联网搜索工具 |
| 连续咨询与历史恢复 | SQLite checkpoint 持久化消息，使用会话 ID 管理对话上下文 |
| 历史删除 | 前端确认后删除选中的会话数据库，生成期间禁止删除 |
| Web 交互 | FastAPI SSE 输出、Markdown 展示、快捷问题和移动端历史侧栏 |

## 技术架构

```text
Web 前端 → FastAPI → LangChain Agent → 大语言模型
                         ├─ 本地法规检索工具
                         │    └─ Chroma → 法规片段 → RAG 总结
                         ├─ Tavily 联网搜索工具
                         └─ SQLite checkpoint → 对话记忆

法规文本 → 文本切分 → Embedding → Chroma
```

## 工程实现

- **检索链路**：以本地法规为资料来源，使用文本切分、向量化和 Retriever 完成检索，再将参考片段与问题交给模型总结。
- **增量入库**：使用文件 MD5 记录已处理资料，重复执行加载时跳过相同文件，减少重复入库。
- **智能体编排**：将本地资料检索与联网搜索封装为工具，交由模型根据问题调用；提示词引导参考资料组织与回答格式。
- **会话持久化**：通过 `ChatManager` 统一创建会话、生成概述标题、扫描历史和恢复消息，LangGraph checkpoint 保留上下文。
- **删除边界**：删除前校验数据库路径位于历史目录，关闭对应连接后移除文件；接口通过会话锁阻止生成期间删除。
- **Web 交付**：由 FastAPI 提供接口与静态页面，前端支持 SSE 事件处理、Markdown 回答、错误反馈和移动端适配。

资料检索和提示词约束用于提供参考上下文，并不保证回答无幻觉或法律结论正确。法规时效、案例适用性和引用准确性仍需核验。

## 技术栈

前端：HTML、CSS、JavaScript、Markdown 渲染。

后端：Python、FastAPI、LangChain、LangGraph、Chroma、SQLite、DashScope、Tavily。

## 项目结构

```text
agent/                   智能体与工具编排
rag/                     法规检索、总结与向量库加载
model/                   聊天模型与 Embedding 工厂
utils/                   会话、配置、日志与资料读取
config/                  模型和检索配置
prompts/                 系统提示词与 RAG 提示词
data/                    法律法规文本
web/static/              Web 页面、交互与样式
web_app.py               FastAPI 服务入口
```

## 本地体验

环境要求：Python 3.13+。复制 `.env.example` 为 `.env`，填写 DashScope 与 Tavily 密钥。

```bash
pip install -r requirements.txt
```

首次运行前初始化法规知识库：

```bash
python -c "from dotenv import load_dotenv; load_dotenv(); import runpy; runpy.run_module('rag.vector_store', run_name='__main__')"
```

启动应用：

```bash
python web_app.py
```

访问 `http://127.0.0.1:8000`，接口文档位于 `http://127.0.0.1:8000/docs`。知识库初始化需要模型服务可用，并可能产生 Embedding 调用费用。

仓库提供源码与法规文本，不包含 API 密钥、本地向量索引、真实会话数据库、日志或缓存。法规文本需根据实际使用时间自行检查更新。

## 验证与应用边界

已完成临时数据库接口测试，覆盖历史列表、指定会话删除、其他会话保留、重复删除和路径校验。测试不代表法律回答准确率或生产级性能验证。

当前为单用户应用演示。公开部署需增加身份认证、会话归属校验、限流和 HTTPS；会话 ID 不能替代访问权限。前端停止读取不保证立即终止模型调用。删除的会话无法恢复。

本系统提供法律信息参考，不构成正式法律意见，也不能替代执业律师的个案分析。
