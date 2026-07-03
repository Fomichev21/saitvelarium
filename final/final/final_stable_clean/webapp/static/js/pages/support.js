import { api } from "../api.js";
import { openLink } from "../telegram.js";
import { hapticSuccess } from "../telegram.js";
import { ICON_SEND } from "../icons.js";

let pollTimer = null;
let lastCount = -1;

export async function renderSupport(root) {
  stopPolling();
  root.innerHTML = `<div class="center-loader">Загрузка…</div>`;
  const data = await api.get("/api/support/faq");

  root.innerHTML = `
    <div class="card">
      <p class="section-title">Чат с поддержкой</p>
      <div class="chat-panel">
        <div class="chat-messages" id="chat-messages"></div>
        <div class="chat-input-row">
          <textarea id="chat-input" placeholder="Напиши сообщение…"></textarea>
          <button id="chat-send">${ICON_SEND}</button>
        </div>
      </div>
    </div>

    <div class="card" id="support-contact" style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div style="font-weight:700;">Открыть чат в Telegram</div>
        <div class="muted">@${data.support_username} · обычно отвечаем быстро</div>
      </div>
      <div>→</div>
    </div>

    <p class="section-title">Частые вопросы</p>
    <div class="card">
      ${data.faq
        .map(
          (item, i) => `
        <div class="faq-item" data-index="${i}">
          <button class="faq-question">${item.question}<span>⌄</span></button>
          <div class="faq-answer">${item.answer}</div>
        </div>`
        )
        .join("")}
    </div>

    ${
      data.knowledge_base_url
        ? `<div class="card" id="kb-link" style="cursor:pointer;display:flex;align-items:center;justify-content:space-between;">
             <div><div style="font-weight:700;">База знаний</div></div><div>→</div>
           </div>`
        : ""
    }
  `;

  root.querySelector("#support-contact").addEventListener("click", () => {
    openLink(`https://t.me/${data.support_username}`);
  });

  root.querySelectorAll(".faq-question").forEach((btn) => {
    btn.addEventListener("click", () => btn.parentElement.classList.toggle("open"));
  });

  const kbLink = root.querySelector("#kb-link");
  if (kbLink) kbLink.addEventListener("click", () => openLink(data.knowledge_base_url));

  const sendBtn = root.querySelector("#chat-send");
  const input = root.querySelector("#chat-input");
  sendBtn.addEventListener("click", () => sendMessage(root));
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(root);
    }
  });

  lastCount = -1;
  await refreshChat(root, true);
  pollTimer = setInterval(() => refreshChat(root, false), 4000);
  window.addEventListener("hashchange", stopPolling, { once: true });
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function refreshChat(root, forceScroll) {
  const list = root.querySelector("#chat-messages");
  if (!list) {
    stopPolling();
    return;
  }
  let data;
  try {
    data = await api.get("/api/support/chat");
  } catch (e) {
    return;
  }

  if (data.messages.length === lastCount) return;
  lastCount = data.messages.length;

  list.innerHTML = data.messages.length
    ? data.messages
        .map(
          (m) => `
      <div class="chat-bubble from-${m.sender}">
        ${escapeHtml(m.text)}
        <span class="chat-time">${fmtTime(m.created_at)}</span>
      </div>`
        )
        .join("")
    : `<div class="chat-empty">Напиши нам, если что-то пошло не так — ответим здесь.</div>`;

  list.scrollTop = list.scrollHeight;
}

async function sendMessage(root) {
  const input = root.querySelector("#chat-input");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  try {
    await api.post("/api/support/chat", { text });
    hapticSuccess();
    lastCount = -1;
    await refreshChat(root, true);
  } catch (err) {
    input.value = text;
  }
}

function fmtTime(value) {
  if (!value) return "";
  try {
    const d = new Date(value.replace(" ", "T") + "Z");
    return d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
  } catch (e) {
    return "";
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}
