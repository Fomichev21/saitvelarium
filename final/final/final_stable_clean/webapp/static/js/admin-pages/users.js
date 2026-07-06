import { api } from "../api.js";
import { toast, fmtDate, showModal, closeModal } from "../ui.js";
import { ICON_WALLET, ICON_CLOCK, ICON_PLUS, ICON_MINUS, ICON_CHECK, ICON_BAN, ICON_TRASH } from "../icons.js";

let root;
let activeRole = "";
let activeBanned = "";

const ROLE_FILTERS = [
  { key: "", label: "Все" },
  { key: "user", label: "Пользователи" },
  { key: "admin", label: "Админы" },
];

const BANNED_FILTERS = [
  { key: "", label: "Все" },
  { key: "false", label: "Активные" },
  { key: "true", label: "Забаненные" },
];

export async function renderUsers(container) {
  root = container;
  root.innerHTML = `
    <div class="card">
      <input class="input" id="user-search" placeholder="Поиск по ID или username" style="margin-bottom:12px;" />
      <div class="filter-row" id="role-filters" style="margin-bottom:8px;"></div>
      <div class="filter-row" id="banned-filters"></div>
    </div>
    <div id="user-list"><div class="center-loader">Загрузка…</div></div>
  `;

  const search = root.querySelector("#user-search");
  let timer = null;
  search.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => loadUsers(search.value.trim()), 300);
  });

  const roleRow = root.querySelector("#role-filters");
  roleRow.innerHTML = ROLE_FILTERS.map(
    (f) => `<button class="chip-filter ${f.key === activeRole ? "active" : ""}" data-key="${f.key}">${f.label}</button>`
  ).join("");
  roleRow.querySelectorAll(".chip-filter").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeRole = btn.dataset.key;
      roleRow.querySelectorAll(".chip-filter").forEach((b) => b.classList.toggle("active", b === btn));
      loadUsers(search.value.trim());
    });
  });

  const bannedRow = root.querySelector("#banned-filters");
  bannedRow.innerHTML = BANNED_FILTERS.map(
    (f) => `<button class="chip-filter ${f.key === activeBanned ? "active" : ""}" data-key="${f.key}">${f.label}</button>`
  ).join("");
  bannedRow.querySelectorAll(".chip-filter").forEach((btn) => {
    btn.addEventListener("click", () => {
      activeBanned = btn.dataset.key;
      bannedRow.querySelectorAll(".chip-filter").forEach((b) => b.classList.toggle("active", b === btn));
      loadUsers(search.value.trim());
    });
  });

  await loadUsers("");
}

async function loadUsers(q) {
  const list = root.querySelector("#user-list");
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (activeRole) params.set("role", activeRole);
  if (activeBanned) params.set("banned", activeBanned);
  const query = params.toString();
  const data = await api.get(`/api/admin/users${query ? `?${query}` : ""}`);

  if (!data.users.length) {
    list.innerHTML = `<p class="muted">Никого не нашли.</p>`;
    return;
  }

  list.innerHTML = `<div class="card">${data.users
    .map(
      (u) => `
    <div class="list-row" data-uid="${u.user_id}" style="cursor:pointer;">
      <div>
        <div style="font-weight:700;">${u.user_id} · @${u.username || "unknown"}${u.is_banned ? ' · <span style="color:var(--danger);">забанен</span>' : ""}</div>
        <div class="faint">роль ${u.role} · баланс ${u.balance}₽ · подписка до ${fmtDate(u.subscription_until)}</div>
      </div>
      <div>→</div>
    </div>`
    )
    .join("")}</div>`;

  list.querySelectorAll(".list-row").forEach((row) => {
    row.addEventListener("click", () => openUserDetail(Number(row.dataset.uid)));
  });
}

async function openUserDetail(userId) {
  const detail = await api.get(`/api/admin/users/${userId}`);
  const u = detail.user;

  showModal(
    `
    <p class="section-title">Пользователь ${u.user_id}</p>
    <div class="card-soft" style="margin-bottom:12px;">
      <div class="list-row"><span class="muted">Username</span><span>@${u.username || "unknown"}</span></div>
      <div class="list-row"><span class="muted">Роль</span><span>${u.role}</span></div>
      <div class="list-row"><span class="muted">Баланс</span><span>${u.balance}₽</span></div>
      <div class="list-row"><span class="muted">Подписка до</span><span>${fmtDate(u.subscription_until)}</span></div>
      <div class="list-row"><span class="muted">Бан</span><span>${u.is_banned ? "да" : "нет"}</span></div>
    </div>
    <div class="btn-row" style="margin-bottom:8px;">
      <button class="btn btn-secondary" id="act-balance">${ICON_WALLET}Баланс</button>
      <button class="btn btn-secondary" id="act-extend">${ICON_CLOCK}Подписка</button>
    </div>
    <div class="btn-row" style="margin-bottom:8px;">
      <button class="btn btn-secondary" id="act-role">${u.role >= 2 ? ICON_MINUS + "Снять админку" : ICON_PLUS + "Выдать админку"}</button>
      <button class="btn btn-danger" id="act-ban">${u.is_banned ? ICON_CHECK + "Разбанить" : ICON_BAN + "Забанить"}</button>
    </div>
    <button class="btn btn-danger" id="act-reset" style="margin-bottom:8px;">${ICON_TRASH}Сбросить подписку и доступ</button>
    <button class="btn btn-secondary" id="modal-close">Закрыть</button>
  `,
    (modal) => {
      modal.querySelector("#modal-close").addEventListener("click", closeModal);

      modal.querySelector("#act-balance").addEventListener("click", async () => {
        const amount = Number(prompt("Сумма начисления (можно отрицательную):", "0"));
        if (!amount) return;
        await api.post(`/api/admin/users/${userId}/balance`, { amount });
        toast("Баланс обновлён");
        closeModal();
        loadUsers(root.querySelector("#user-search").value.trim());
      });

      modal.querySelector("#act-extend").addEventListener("click", async () => {
        const days = Number(prompt("На сколько дней продлить (отрицательное число — сократить):", "30"));
        if (!days) return;
        try {
          await api.post(`/api/admin/users/${userId}/subscription/extend`, { days });
          toast("Подписка обновлена");
        } catch (err) {
          toast(err.message);
        }
        closeModal();
        loadUsers(root.querySelector("#user-search").value.trim());
      });

      modal.querySelector("#act-role").addEventListener("click", async () => {
        const newRole = u.role >= 2 ? 1 : 2;
        await api.post(`/api/admin/users/${userId}/role`, { role: newRole });
        toast("Роль обновлена");
        closeModal();
        loadUsers(root.querySelector("#user-search").value.trim());
      });

      modal.querySelector("#act-ban").addEventListener("click", async () => {
        await api.post(`/api/admin/users/${userId}/ban`, { banned: !u.is_banned });
        toast(u.is_banned ? "Разбанен" : "Забанен");
        closeModal();
        loadUsers(root.querySelector("#user-search").value.trim());
      });

      modal.querySelector("#act-reset").addEventListener("click", async () => {
        if (!confirm("Точно сбросить подписку и отобрать доступ?")) return;
        try {
          await api.post(`/api/admin/users/${userId}/subscription/reset`, {});
          toast("Доступ сброшен");
        } catch (err) {
          toast(err.message);
        }
        closeModal();
        loadUsers(root.querySelector("#user-search").value.trim());
      });
    }
  );
}
