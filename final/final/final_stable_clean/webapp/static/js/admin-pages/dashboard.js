import { api, downloadFile } from "../api.js";
import { toast } from "../ui.js";
import { ICON_SAVE } from "../icons.js";

export async function renderDashboard(root) {
  root.innerHTML = `<div class="center-loader">Загрузка…</div>`;
  const stats = await api.get("/api/admin/stats");

  root.innerHTML = `
    <div class="card">
      <p class="section-title">Статистика</p>
      <div class="stat-grid">
        <div class="stat-box"><div class="value">${stats.users}</div><div class="label">Пользователей</div></div>
        <div class="stat-box"><div class="value">${stats.active_subscriptions}</div><div class="label">Активных подписок</div></div>
        <div class="stat-box"><div class="value">${stats.paid_payments}</div><div class="label">Оплаченных счетов</div></div>
      </div>
      <div class="stat-grid" style="grid-template-columns: repeat(2, 1fr);">
        <div class="stat-box"><div class="value">${stats.revenue}₽</div><div class="label">Выручка</div></div>
        <div class="stat-box"><div class="value">${stats.total_balance}₽</div><div class="label">Баланс юзеров</div></div>
      </div>
    </div>

    <div class="card">
      <p class="section-title">Резервная копия базы</p>
      <p class="muted" style="margin-bottom:12px;">Автоматический бэкап уходит админам в Telegram каждый день в 03:00 UTC. Можно скачать снимок и вручную.</p>
      <button class="btn btn-secondary" id="btn-backup">${ICON_SAVE}Скачать бэкап сейчас</button>
    </div>
  `;

  const backupLabel = `${ICON_SAVE}Скачать бэкап сейчас`;
  root.querySelector("#btn-backup").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    btn.disabled = true;
    btn.textContent = "Готовим файл…";
    try {
      await downloadFile("/api/admin/backup", "velarium_backup.sqlite3");
    } catch (err) {
      toast(err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = backupLabel;
    }
  });
}
