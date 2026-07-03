import { api } from "../api.js";
import { fmtDate } from "../ui.js";

const STATUS_LABEL = { paid: "Оплачен", pending: "Ожидает", failed: "Отклонён" };

export async function renderProfile(root) {
  root.innerHTML = `<div class="center-loader">Загрузка…</div>`;
  const [me, history] = await Promise.all([
    api.get("/api/me"),
    api.get("/api/payments/history"),
  ]);

  root.innerHTML = `
    <div class="card">
      <p class="section-title">Аккаунт</p>
      <div class="list-row"><span class="muted">Telegram ID</span><span>${me.user_id}</span></div>
      <div class="list-row"><span class="muted">Username</span><span>@${me.username || "—"}</span></div>
      <div class="list-row"><span class="muted">Баланс</span><span>${me.balance}₽</span></div>
      <div class="list-row"><span class="muted">С нами с</span><span>${fmtDate(me.created_at)}</span></div>
    </div>

    <p class="section-title">История платежей</p>
    <div class="card">
      ${
        history.payments.length
          ? history.payments
              .map(
                (p) => `
        <div class="list-row">
          <span>${p.invoice_code || p.id.slice(0, 8)} · ${fmtDate(p.created_at)}</span>
          <span><span class="badge ${p.status}">${STATUS_LABEL[p.status] || p.status}</span> ${p.amount}₽</span>
        </div>`
              )
              .join("")
          : `<p class="muted">Платежей пока нет</p>`
      }
    </div>
  `;
}
