import { api } from "../api.js";
import { fmtDate } from "../ui.js";
import { ICON_CHECK, ICON_CLOCK, ICON_X } from "../icons.js";

const STATUS_LABEL = { paid: "Оплачен", pending: "Ожидает", failed: "Отклонён" };
const STATUS_ICON = { paid: ICON_CHECK, pending: ICON_CLOCK, failed: ICON_X };
const FILTERS = [
  { key: "", label: "Все" },
  { key: "pending", label: "Ожидает" },
  { key: "paid", label: "Оплачен" },
  { key: "failed", label: "Отклонён" },
];

let root;
let activeFilter = "";

export async function renderPayments(container) {
  root = container;
  root.innerHTML = `
    <div class="card">
      <div class="filter-row" id="payment-filters"></div>
    </div>
    <div id="payments-list"><div class="center-loader">Загрузка…</div></div>
  `;

  const filterRow = root.querySelector("#payment-filters");
  filterRow.innerHTML = FILTERS.map(
    (f) => `<button class="chip-filter ${f.key === activeFilter ? "active" : ""}" data-key="${f.key}">${f.label}</button>`
  ).join("");
  filterRow.querySelectorAll(".chip-filter").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeFilter = btn.dataset.key;
      filterRow.querySelectorAll(".chip-filter").forEach((b) => b.classList.toggle("active", b === btn));
      load();
    });
  });

  await load();
}

async function load() {
  const list = root.querySelector("#payments-list");
  list.innerHTML = `<div class="center-loader">Загрузка…</div>`;
  const query = activeFilter ? `?status=${activeFilter}` : "";
  const data = await api.get(`/api/admin/payments${query}`);

  if (!data.payments.length) {
    list.innerHTML = `<p class="muted">Платежей не найдено.</p>`;
    return;
  }

  list.innerHTML = `<div class="card">${data.payments
    .map(
      (p) => `
    <div class="payment-row">
      <div class="payment-row-left">
        <span class="icon-badge sm status-${p.status}">${STATUS_ICON[p.status] || ""}</span>
        <div>
          <div style="font-weight:700;">${p.invoice_code || p.id.slice(0, 8)} · user ${p.user_id}</div>
          <div class="faint">${p.tariff_code} · ${fmtDate(p.created_at)}</div>
        </div>
      </div>
      <div class="payment-row-right">
        <div style="font-weight:700;">${p.amount}₽</div>
        <span class="badge ${p.status}">${STATUS_LABEL[p.status] || p.status}</span>
      </div>
    </div>`
    )
    .join("")}</div>`;
}
