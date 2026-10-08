const state = {
  sessionId: null,
  sessions: [],
  generating: false,
  controller: null,
};

const els = {
  conversation: document.querySelector("#conversation"),
  welcome: document.querySelector("#welcome"),
  messages: document.querySelector("#messages"),
  historyList: document.querySelector("#historyList"),
  title: document.querySelector("#conversationTitle"),
  input: document.querySelector("#questionInput"),
  form: document.querySelector("#composer"),
  send: document.querySelector("#sendButton"),
  stop: document.querySelector("#stopButton"),
  sidebar: document.querySelector("#sidebar"),
  backdrop: document.querySelector("#sidebarBackdrop"),
  toast: document.querySelector("#toast"),
};

if (window.marked) marked.setOptions({ breaks: true, gfm: true });

function escapeHtml(value) {
  const div = document.createElement("div");
  div.textContent = value;
  return div.innerHTML;
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("show");
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => els.toast.classList.remove("show"), 2600);
}

function formatDate(value) {
  if (!value) return "";
  return value.slice(0, 16).replace("T", " ");
}

function scrollToBottom() {
  requestAnimationFrame(() => { els.conversation.scrollTop = els.conversation.scrollHeight; });
}

function setGenerating(active) {
  state.generating = active;
  els.send.classList.toggle("hidden", active);
  els.stop.classList.toggle("hidden", !active);
  els.input.disabled = active;
}

function renderMarkdown(text) {
  const safeSource = escapeHtml(text || "");
  if (!window.marked) return safeSource.replaceAll("\n", "<br>");
  return marked.parse(safeSource);
}

function addMessage(role, content = "") {
  els.welcome.classList.add("hidden");
  const row = document.createElement("article");
  row.className = `message ${role}`;
  if (role === "assistant") {
    row.innerHTML = `<div class="avatar">律</div><div class="bubble"></div>`;
  } else {
    row.innerHTML = `<div class="bubble"></div>`;
  }
  const bubble = row.querySelector(".bubble");
  bubble.innerHTML = role === "assistant" ? renderMarkdown(content) : escapeHtml(content).replaceAll("\n", "<br>");
  els.messages.appendChild(row);
  scrollToBottom();
  return bubble;
}

function showThinking(bubble) {
  bubble.innerHTML = `<span class="thinking">正在检索法规与案例 <i></i><i></i><i></i></span>`;
}

function renderHistory() {
  if (!state.sessions.length) {
    els.historyList.innerHTML = `<div class="history-empty">暂无历史咨询<br>发出第一个问题后会自动保存</div>`;
    return;
  }
  els.historyList.innerHTML = state.sessions.map(item => `
    <div class="history-row"><button class="history-item ${item.session_id === state.sessionId ? "active" : ""}" data-session="${escapeHtml(item.session_id)}">
      <strong>${escapeHtml(item.overview || "未命名咨询")}</strong>
      <span>${escapeHtml(formatDate(item.created_at))}</span>
    </button><button class="history-delete" data-delete="${escapeHtml(item.session_id)}" title="删除会话" aria-label="删除会话">×</button></div>`).join("");
  els.historyList.querySelectorAll("[data-session]").forEach(button => {
    button.addEventListener("click", () => loadSession(button.dataset.session));
  });
  els.historyList.querySelectorAll("[data-delete]").forEach(button => {
    button.addEventListener("click", () => deleteSession(button.dataset.delete));
  });
}

async function deleteSession(sessionId) {
  if (state.generating) return showToast("请等待当前回答结束后删除");
  const info = state.sessions.find(item => item.session_id === sessionId);
  if (!window.confirm(`确认永久删除“${info?.overview || '该会话'}”及全部消息？此操作无法恢复。`)) return;
  try {
    const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}`, {method: 'DELETE'});
    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || '删除失败');
    }
    if (state.sessionId === sessionId) newChat();
    await loadSessions();
    showToast('会话已删除，无法恢复');
  } catch (error) { showToast(error.message); }
}

async function loadSessions() {
  try {
    const response = await fetch("/api/sessions");
    if (!response.ok) throw new Error("加载历史记录失败");
    const data = await response.json();
    state.sessions = data.sessions || [];
    renderHistory();
  } catch (error) {
    showToast(error.message);
  }
}

async function loadSession(sessionId) {
  if (state.generating) return showToast("请先停止当前回答");
  try {
    const response = await fetch(`/api/sessions/${encodeURIComponent(sessionId)}/messages`);
    if (!response.ok) throw new Error("无法读取该会话");
    const data = await response.json();
    state.sessionId = sessionId;
    els.messages.innerHTML = "";
    els.welcome.classList.add("hidden");
    data.messages.forEach(message => addMessage(message.role, message.content));
    const info = state.sessions.find(item => item.session_id === sessionId);
    els.title.textContent = info?.overview || "历史咨询";
    renderHistory();
    closeSidebar();
    scrollToBottom();
  } catch (error) {
    showToast(error.message);
  }
}

function newChat() {
  if (state.generating) state.controller?.abort();
  state.sessionId = null;
  els.messages.innerHTML = "";
  els.welcome.classList.remove("hidden");
  els.title.textContent = "新咨询";
  els.input.value = "";
  autoResize();
  setGenerating(false);
  renderHistory();
  closeSidebar();
  els.input.focus();
}

function autoResize() {
  els.input.style.height = "auto";
  els.input.style.height = `${Math.min(els.input.scrollHeight, 160)}px`;
}

function parseEventBlock(block) {
  const lines = block.split("\n");
  const type = lines.find(line => line.startsWith("event:"))?.slice(6).trim() || "message";
  const dataText = lines.filter(line => line.startsWith("data:")).map(line => line.slice(5).trim()).join("\n");
  return { type, data: dataText ? JSON.parse(dataText) : {} };
}

async function submitQuestion(question) {
  const text = (question ?? els.input.value).trim();
  if (!text || state.generating) return;
  addMessage("user", text);
  els.input.value = "";
  autoResize();
  const assistantBubble = addMessage("assistant");
  showThinking(assistantBubble);
  setGenerating(true);
  state.controller = new AbortController();

  let answer = "";
  let buffer = "";
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: state.sessionId }),
      signal: state.controller.signal,
    });
    if (!response.ok || !response.body) throw new Error("服务暂时不可用");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";
      for (const block of blocks) {
        if (!block.trim()) continue;
        const event = parseEventBlock(block);
        if (event.type === "session") {
          state.sessionId = event.data.session_id;
        } else if (event.type === "delta") {
          // LangGraph values mode returns the latest complete model message.
          // Replace the preview instead of concatenating repeated snapshots.
          answer = event.data.content || answer;
          assistantBubble.innerHTML = renderMarkdown(answer);
          scrollToBottom();
        } else if (event.type === "error") {
          throw new Error(event.data.message || "回答生成失败");
        }
      }
    }
    if (!answer) assistantBubble.innerHTML = `<p>暂时没有生成有效回答，请稍后重试。</p>`;
    await loadSessions();
    const info = state.sessions.find(item => item.session_id === state.sessionId);
    if (info) els.title.textContent = info.overview;
  } catch (error) {
    if (error.name === "AbortError") {
      if (!answer) assistantBubble.innerHTML = `<p>已停止生成。</p>`;
      else assistantBubble.innerHTML = renderMarkdown(answer + "\n\n_回答已停止_ ");
    } else {
      assistantBubble.innerHTML = `<p>${escapeHtml(error.message)}</p>`;
      showToast(error.message);
    }
  } finally {
    setGenerating(false);
    state.controller = null;
    els.input.focus();
  }
}

function openSidebar() { els.sidebar.classList.add("open"); els.backdrop.classList.add("show"); }
function closeSidebar() { els.sidebar.classList.remove("open"); els.backdrop.classList.remove("show"); }

els.form.addEventListener("submit", event => { event.preventDefault(); submitQuestion(); });
els.input.addEventListener("input", autoResize);
els.input.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    submitQuestion();
  }
});
els.stop.addEventListener("click", () => state.controller?.abort());
document.querySelector("#newChatButton").addEventListener("click", newChat);
document.querySelector("#refreshButton").addEventListener("click", loadSessions);
document.querySelector("#menuButton").addEventListener("click", openSidebar);
els.backdrop.addEventListener("click", closeSidebar);
document.querySelectorAll("[data-question]").forEach(button => button.addEventListener("click", () => submitQuestion(button.dataset.question)));

loadSessions();
autoResize();
