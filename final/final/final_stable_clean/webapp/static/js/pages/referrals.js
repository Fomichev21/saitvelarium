import { api } from "../api.js";
import { toast, copyToClipboard, showModal, closeModal } from "../ui.js";
import { ICON_COPY, ICON_QR } from "../icons.js";

export async function renderReferrals(root) {
  root.innerHTML = `<div class="center-loader">Загрузка…</div>`;
  const data = await api.get("/api/referral");

  root.innerHTML = `
    <div class="card">
      <p class="section-title">Реферальная программа</p>
      <div class="stat-grid">
        <div class="stat-box"><div class="value">${data.total}</div><div class="label">Приглашено</div></div>
        <div class="stat-box"><div class="value">+${data.bonus_days}д</div><div class="label">Бонус дней</div></div>
        <div class="stat-box"><div class="value">${data.rewarded}</div><div class="label">Оплатили</div></div>
      </div>
      <p class="section-title">Реферальная ссылка</p>
      <div class="key-box"><span>${data.link}</span></div>
      <div class="btn-row" style="margin-top:10px;">
        <button class="btn btn-primary" id="btn-copy">${ICON_COPY}Копировать</button>
        <button class="btn btn-secondary btn-icon" id="btn-qr">${ICON_QR}</button>
      </div>
    </div>

    <div class="card">
      <p class="section-title">Как это работает</p>
      <div class="steps">
        <div class="step"><div class="step-num">1</div><div>Поделись реферальной ссылкой с друзьями</div></div>
        <div class="step"><div class="step-num">2</div><div>Друг переходит по ссылке и регистрируется в боте</div></div>
        <div class="step"><div class="step-num">3</div><div>Когда друг оплатит первую подписку — тебе начислится +${data.bonus_days} дня</div></div>
      </div>
    </div>
  `;

  root.querySelector("#btn-copy").addEventListener("click", async () => {
    await copyToClipboard(data.link);
    toast("Ссылка скопирована");
  });
  root.querySelector("#btn-qr").addEventListener("click", () => {
    showModal(
      `<p class="section-title">QR-код ссылки</p><div class="qr-wrap"><img src="/api/referral/qrcode" alt="QR" width="220" height="220"/></div><button class="btn btn-secondary" id="modal-close" style="margin-top:10px;">Закрыть</button>`,
      (modal) => modal.querySelector("#modal-close").addEventListener("click", closeModal)
    );
  });
}
