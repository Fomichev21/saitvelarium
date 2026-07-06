import { api } from "../api.js";
import { toast, fmtDate, copyToClipboard, showModal, closeModal } from "../ui.js";
import { hapticSuccess, openLink } from "../telegram.js";
import { ICON_COPY, ICON_QR, ICON_ARROW_OUT, HIGHLIGHT_ICONS } from "../icons.js";

const STATUS_LABEL = {
  active: "Активна",
  trial: "Пробный доступ",
  none: "Не активна",
};

export async function renderHome(root) {
  root.innerHTML = `<div class="center-loader">Загрузка…</div>`;

  const [subscription, tariffs, info, me, serverStatus] = await Promise.all([
    api.get("/api/subscription"),
    api.get("/api/tariffs"),
    api.get("/api/info"),
    api.get("/api/me"),
    api.get("/api/status").catch(() => ({ available: false })),
  ]);

  const pct = subscription.total_days
    ? Math.min(100, Math.round((subscription.days_remaining / subscription.total_days) * 100))
    : 0;

  root.innerHTML = `
    <div class="hero">
      <img class="hero-avatar" src="/static/assets/avatar.webp" alt="" />
      <div>
        <div class="hero-title">Привет, ${me.first_name || "друг"}!</div>
        <div class="hero-subtitle">${info.tagline}</div>
      </div>
    </div>

    ${
      serverStatus.available
        ? `<div class="server-status ${serverStatus.all_online ? "ok" : "warn"}">
             <span class="pill-dot"></span>
             ${serverStatus.all_online ? "Все серверы работают" : `Перебои на некоторых серверах (${serverStatus.online}/${serverStatus.total})`}
           </div>`
        : ""
    }

    <div class="highlight-row">
      ${info.highlights
        .map((h) => `<div class="highlight-chip"><span class="icon-badge sm">${HIGHLIGHT_ICONS[h.icon] || ""}</span>${h.text}</div>`)
        .join("")}
    </div>

    <div class="card">
      <span class="pill ${subscription.status}"><span class="pill-dot"></span>${STATUS_LABEL[subscription.status]}</span>
      ${
        subscription.status === "none"
          ? `<div class="big-number" style="font-size:32px;margin-top:16px;">Подписка не активна</div>`
          : `<div class="big-number">${subscription.days_remaining} ${pluralDays(subscription.days_remaining)}</div>
             <div class="muted">до ${fmtDate(subscription.expires_at)}</div>
             <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
             <div class="progress-label"><span>Осталось</span><span>${subscription.days_remaining} из ${subscription.total_days} дн.</span></div>`
      }
      <div class="btn-row" style="margin-top:16px;">
        <button class="btn btn-primary" id="btn-buy">${subscription.status === "none" ? "Купить" : "Продлить"}</button>
        ${subscription.status === "none" ? `<button class="btn btn-secondary" id="btn-trial">Попробовать бесплатно</button>` : ""}
      </div>
    </div>

    <div class="card" id="key-card" style="display:${subscription.subscription_url ? "block" : "none"}">
      <p class="section-title">Ключ подключения</p>
      <div class="key-box"><span id="key-value">${subscription.subscription_url || ""}</span></div>
      <div class="btn-row" style="margin-top:10px;">
        <button class="btn btn-secondary" id="btn-copy-key">${ICON_COPY}Скопировать</button>
        <button class="btn btn-secondary btn-icon" id="btn-qr-key">${ICON_QR}</button>
      </div>
      ${renderTrafficUsage(subscription.traffic)}
    </div>

    <div class="card">
      <p class="section-title">Как подключиться</p>
      <div class="steps" style="margin-bottom:14px;">
        <div class="step"><div class="step-num">1</div><div>Установи одно из приложений ниже</div></div>
        <div class="step"><div class="step-num">2</div><div>Скопируй ключ подключения выше</div></div>
        <div class="step"><div class="step-num">3</div><div>Вставь ключ в приложение через «Добавить по URL»</div></div>
      </div>
      ${info.connect_apps
        .map(
          (a) => `
        <a class="app-row" href="${a.url}" target="_blank" rel="noopener">
          <div class="app-row-left">
            <img class="app-icon" src="${a.icon}" alt="${a.name}" />
            <div>
              <div style="font-weight:700;">${a.name}</div>
              <div class="faint">${a.platform}</div>
            </div>
          </div>
          <div>${ICON_ARROW_OUT}</div>
        </a>`
        )
        .join("")}
    </div>

    <div class="card">
      <p class="section-title">Velarium VPN — информация</p>
      <p class="muted" style="line-height:1.6;">${info.description}</p>
      <p class="section-title" style="margin-top:16px;">Документы</p>
      <div class="steps">
        <div class="step"><div class="step-num">1</div><a href="${info.terms_url}" target="_blank" rel="noopener">Пользовательское соглашение</a></div>
        <div class="step"><div class="step-num">2</div><a href="${info.privacy_url}" target="_blank" rel="noopener">Политика конфиденциальности</a></div>
      </div>
      <div class="list-row" style="margin-top:10px;">
        <span class="muted">Поддержка</span>
        <span id="info-support" style="cursor:pointer;color:var(--accent);font-weight:700;">@${info.support_username}</span>
      </div>
    </div>
  `;

  root.querySelector("#info-support")?.addEventListener("click", () => openLink(`https://t.me/${info.support_username}`));

  root.querySelector("#btn-buy").addEventListener("click", () => openTariffPicker(tariffs.tariffs));
  const trialBtn = root.querySelector("#btn-trial");
  if (trialBtn) trialBtn.addEventListener("click", activateTrial);

  const copyBtn = root.querySelector("#btn-copy-key");
  if (copyBtn) {
    copyBtn.addEventListener("click", async () => {
      await copyToClipboard(subscription.subscription_url);
      toast("Скопировано");
      hapticSuccess();
    });
  }
  const qrBtn = root.querySelector("#btn-qr-key");
  if (qrBtn) qrBtn.addEventListener("click", showKeyQr);
}

function fmtGB(bytes) {
  return (bytes / 1024 ** 3).toFixed(1).replace(/\.0$/, "");
}

function renderTrafficUsage(traffic) {
  if (!traffic) return "";
  const usedGB = fmtGB(traffic.used_bytes);
  if (!traffic.limit_bytes) {
    return `
      <div class="traffic-usage">
        <div class="progress-label"><span>Использовано трафика</span><span>${usedGB} ГБ</span></div>
      </div>`;
  }
  const pct = Math.min(100, Math.round((traffic.used_bytes / traffic.limit_bytes) * 100));
  const limitGB = fmtGB(traffic.limit_bytes);
  return `
    <div class="traffic-usage">
      <div class="progress-track"><div class="progress-fill" style="width:${pct}%"></div></div>
      <div class="progress-label"><span>Трафик</span><span>${usedGB} из ${limitGB} ГБ</span></div>
    </div>`;
}

function pluralDays(n) {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return "день";
  if ([2, 3, 4].includes(mod10) && ![12, 13, 14].includes(mod100)) return "дня";
  return "дней";
}

const TARIFF_BADGES = {
  month: "Попробовать",
  quarter: "Популярный выбор",
  year: "Максимальная выгода",
};

function openTariffPicker(tariffs) {
  showModal(
    `
    <p class="section-title">Выбери тариф</p>
    ${tariffs
      .map((t) => {
        const perMonth = Math.round(t.price / Math.max(1, Math.round(t.duration_days / 30)));
        const featured = t.code === "quarter";
        return `
      <div class="plan-card ${featured ? "featured" : ""}" data-code="${t.code}">
        <span class="badge-pill">${TARIFF_BADGES[t.code] || t.title}</span>
        <div class="plan-title">${t.title}</div>
        <div class="plan-price">${perMonth}₽<span>/мес</span></div>
        <div class="faint" style="margin-bottom:12px;">${t.description} · всего ${t.price}₽</div>
        <button class="btn btn-primary" data-code="${t.code}">Оформить</button>
      </div>`;
      })
      .join("")}
    <button class="btn btn-secondary" id="modal-cancel">Отмена</button>
  `,
    (modal) => {
      modal.querySelector("#modal-cancel").addEventListener("click", closeModal);
      modal.querySelectorAll("button[data-code]").forEach((el) => {
        el.addEventListener("click", () => checkout(el.dataset.code));
      });
    }
  );
}

async function checkout(tariffCode) {
  closeModal();
  try {
    const payment = await api.post("/api/subscription/checkout", { tariff_code: tariffCode });
    showModal(
      `
      <p class="section-title">Счёт создан</p>
      <p class="muted">Тариф: ${payment.title}<br/>Сумма: ${payment.amount}₽<br/>Счёт: ${payment.invoice_code}</p>
      <a class="btn btn-primary" href="${payment.url}" target="_blank" rel="noopener">Оплатить</a>
      <p class="faint" style="margin-top:10px;">После оплаты доступ активируется автоматически в течение пары минут.</p>
      <button class="btn btn-secondary" id="modal-close" style="margin-top:10px;">Закрыть</button>
    `,
      (modal) => modal.querySelector("#modal-close").addEventListener("click", closeModal)
    );
  } catch (err) {
    toast(err.message);
  }
}

async function activateTrial() {
  try {
    await api.post("/api/trial/activate", {});
    toast("Пробный доступ активирован");
    hapticSuccess();
    location.reload();
  } catch (err) {
    toast(err.message);
  }
}

function showKeyQr() {
  showModal(
    `<p class="section-title">QR-код ключа</p><div class="qr-wrap"><img src="/api/subscription/key/qrcode" alt="QR" width="220" height="220"/></div><button class="btn btn-secondary" id="modal-close" style="margin-top:10px;">Закрыть</button>`,
    (modal) => modal.querySelector("#modal-close").addEventListener("click", closeModal)
  );
}
