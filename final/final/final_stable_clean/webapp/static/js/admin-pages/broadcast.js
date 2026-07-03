import { api } from "../api.js";
import { toast } from "../ui.js";
import { ICON_MEGAPHONE } from "../icons.js";

export async function renderBroadcast(root) {
  root.innerHTML = `
    <div class="card">
      <p class="section-title">Рассылка всем пользователям</p>
      <textarea class="input" id="broadcast-text" placeholder="Текст сообщения"></textarea>
      <button class="btn btn-primary" id="broadcast-send">${ICON_MEGAPHONE}Отправить</button>
    </div>
  `;

  root.querySelector("#broadcast-send").addEventListener("click", async () => {
    const text = root.querySelector("#broadcast-text").value.trim();
    if (!text) {
      toast("Введи текст сообщения");
      return;
    }
    if (!confirm("Разослать это сообщение всем пользователям?")) return;

    const btn = root.querySelector("#broadcast-send");
    btn.disabled = true;
    btn.textContent = "Отправка…";
    try {
      const result = await api.post("/api/admin/broadcast", { text });
      toast(`Доставлено: ${result.delivered}`);
      root.querySelector("#broadcast-text").value = "";
    } catch (err) {
      toast(err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `${ICON_MEGAPHONE}Отправить`;
    }
  });
}
