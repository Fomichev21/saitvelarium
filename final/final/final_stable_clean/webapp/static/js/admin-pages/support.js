import { api } from "../api.js";
import { toast } from "../ui.js";
import { ICON_SEND } from "../icons.js";

let pollTimer = null;
let activeUserId = null;
let lastCount = -1;

export async function renderSupport(root) {
  stopPolling();
  activeUserId = null;
  root.innerHTML = `<div class="center-loader">Загрузка…</div>`;
  await renderThreadList(root);
  window.addEventListener("hashchange", stopPolling, { once: true });
}

async function renderThreadList(root) {
  const data = await api.get("/api/admin/support/threads");

  if (!data.threads.length) {
    root.innerHTML = `<p class="muted">Сообщений в поддержку пока нет.</p>`;
    return;
  }

  root.innerHTML = `<div class="card">${data.threads
    .map(
      (t) => `
    <div class="thread-row" data-uid="${t.user_id}">
      <div>
        <div style="font-weight:700;">${t.user_id} · @${t.username || "unknown"}</div>
        <div class="snippet">${t.last_message ? escapeHtml(t.last_message.text) : ""}</div>
      </div>
      <div>→</div>
    </div>`
    )
    .join("")}</div>`;

  root.querySelectorAll(".thread-row").forEach((row) => {
    row.addEventListener("click", () => openThread(root, Number(row.dataset.uid)));
  });
}

async function openThread(root, userId) {
  activeUserId = userId;
  lastCount = -1;
  root.innerHTML = `
    <button class="btn btn-secondary" id="back-to-threads" style="margin-bottom:12px;">← Все диалоги</button>
    <div class="card">
      <p class="section-title">Диалог с ${userId}</p>
      <div class="chat-panel">
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input-row">
          <textarea id="chat-input" placeholder="Ответить пользователю…"></textarea>
          <button id="chat-send">${ICON_SEND}</button>
        </div>
      </div>
    </div>
  `;

  root.querySelector("#back-to-threads").addEventListener("click", () => {
    stopPolling();
    renderThreadList(root);
  });

  const sendBtn = root.querySelector("#chat-send");
  const input = root.querySelector("#chat-input");
  sendBtn.addEventListener("click", () => sendReply(root, userId));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendReply(root, userId);
    }
  });

  await refreshThread(root, userId);
  pollTimer = setInterval(() => refreshThread(root, userId), 4000);
}

async function refreshThread(root, userId) {
  const list = root.querySelector("#chat-messages");
  if (!list || activeUserId !== userId) {
    stopPolling();
    return;
  }
  const data = await api.get(`/api/admin/support/threads/${userId}`);
  if (data.messages.length === lastCount) return;
  lastCount = data.messages.length;

  list.innerHTML = data.messages
    .map(
      (m) => `
    <div class="chat-bubble from-${m.sender === "admin" ? "user" : "admin"}">
      ${escapeHtml(m.text)}
    </div>`
    )
    .join("");
  list.scrollTop = list.scrollHeight;
}

async function sendReply(root, userId) {
  const input = root.querySelector("#chat-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  try {
    await api.post(`/api/admin/support/threads/${userId}/reply`, { text });
    lastCount = -1;
    await refreshThread(root, userId);
  } catch (err) {
    toast(err.message);
    input.value = text;
  }
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
