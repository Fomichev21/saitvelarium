import { api } from "../api.js";
import { toast, fmtDate } from "../ui.js";
import { openLink, hapticSuccess, hapticError } from "../telegram.js";
import { ICON_CHECK, ICON_CLOCK, ICON_X, ICON_WALLET_LG, ICON_RECEIPT, ICON_CALENDAR } from "../icons.js";

const STATUS_LABEL = { paid: "Оплачен", pending: "Ожидает", failed: "Отклонён" };
const STATUS_ICON = { paid: ICON_CHECK, pending: ICON_CLOCK, failed: ICON_X };

export async function renderProfile(root) {
  root.innerHTML = `<div class="center-loader">Загрузка…</div>`;
  const [me, history] = await Promise.all([
    api.get("/api/me"),
    api.get("/api/payments/history"),
  ]);

  const paidPayments = history.payments.filter((p) => p.status === "paid");
  const totalSpent = paidPayments.reduce((sum, p) => sum + p.amount, 0);
  const initial = (me.first_name || me.username || "?").trim().charAt(0).toUpperCase();

  root.innerHTML = `
    <div class="hero profile-hero">
      <div class="profile-avatar">${initial}</div>
      <div>
        <div class="hero-title">${me.first_name || "Пользователь"}</div>
        <div class="hero-subtitle">@${me.username || "unknown"} · ID ${me.user_id}</div>
      </div>
    </div>

    <div class="stat-grid">
      <div class="stat-box"><div class="value">${me.balance}₽</div><div class="label">Баланс</div></div>
      <div class="stat-box"><div class="value">${paidPayments.length}</div><div class="label">Оплат</div></div>
      <div class="stat-box"><div class="value">${totalSpent}₽</div><div class="label">Потрачено</div></div>
    </div>

    <div class="card">
      <div class="list-row">
        <span class="muted" style="display:flex;align-items:center;gap:8px;">${ICON_CALENDAR}С нами с</span>
        <span>${fmtDate(me.created_at)}</span>
      </div>
    </div>

    <p class="section-title">Промокод</p>
    <div class="card">
      <div style="display:flex;gap:8px;">
        <input class="input" id="promo-input" placeholder="Введите промокод" style="margin-bottom:0;flex:1;text-transform:uppercase;" />
        <button class="btn btn-primary btn-sm" id="promo-submit">Активировать</button>
      </div>
    </div>

    <p class="section-title">История платежей</p>
    <div class="card">
      ${
        history.payments.length
          ? history.payments
              .map(
                (p) => `
        <div class="payment-row">
          <div class="payment-row-left">
            <span class="icon-badge sm status-${p.status}">${STATUS_ICON[p.status] || ICON_RECEIPT}</span>
            <div>
              <div style="font-weight:700;">${p.invoice_code || p.id.slice(0, 8)}</div>
              <div class="faint">${fmtDate(p.created_at)}</div>
            </div>
          </div>
          <div class="payment-row-right">
            <div style="font-weight:700;">${p.amount}₽</div>
            ${
              p.status === "pending" && p.payment_url
                ? `<button class="btn btn-primary btn-sm" data-pay-url="${p.payment_url}">Оплатить</button>`
                : `<span class="badge ${p.status}">${STATUS_LABEL[p.status] || p.status}</span>`
            }
          </div>
        </div>`
              )
              .join("")
          : `<p class="muted">Платежей пока нет</p>`
      }
    </div>
  `;

  root.querySelectorAll("[data-pay-url]").forEach((btn) => {
    btn.addEventListener("click", () => openLink(btn.dataset.payUrl));
  });

  const promoInput = root.querySelector("#promo-input");
  const promoSubmit = root.querySelector("#promo-submit");
  promoSubmit.addEventListener("click", async () => {
    const code = promoInput.value.trim();
    if (!code) return;
    promoSubmit.disabled = true;
    try {
      const result = await api.post("/api/promo/redeem", { code });
      hapticSuccess();
      toast(`Промокод активирован: +${result.days} дн.`);
      promoInput.value = "";
      renderProfile(root);
    } catch (err) {
      hapticError();
      toast(err.message || "Промокод не найден или уже использован");
    } finally {
      promoSubmit.disabled = false;
    }
  });
  promoInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") promoSubmit.click();
  });
}
