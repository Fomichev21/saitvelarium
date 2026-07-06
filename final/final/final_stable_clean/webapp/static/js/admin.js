import { initTelegram } from "./telegram.js";
import { ensureAuth, api } from "./api.js";
import { createRouter } from "./router.js";
import { toast } from "./ui.js";
import { initSidebarToggle } from "./sidebar.js";
import { renderDashboard } from "./admin-pages/dashboard.js";
import { renderUsers } from "./admin-pages/users.js";
import { renderPayments } from "./admin-pages/payments.js";
import { renderSupport } from "./admin-pages/support.js";
import { renderPromos } from "./admin-pages/promos.js";
import { renderBroadcast } from "./admin-pages/broadcast.js";

const main = document.getElementById("main");

const routes = {
  dashboard: () => renderDashboard(main),
  users: () => renderUsers(main),
  payments: () => renderPayments(main),
  support: () => renderSupport(main),
  promos: () => renderPromos(main),
  broadcast: () => renderBroadcast(main),
};

function setActiveNav(route) {
  document.querySelectorAll(".nav-item[data-route]").forEach((el) => {
    el.classList.toggle("active", el.dataset.route === route);
  });
}

document.querySelectorAll(".nav-item[data-route]").forEach((el) => {
  el.addEventListener("click", () => {
    window.location.hash = el.dataset.route;
  });
});

const router = createRouter(routes, "dashboard", setActiveNav);

function setSupportBadge(count) {
  const show = count > 0;
  document.querySelectorAll("#admin-support-badge, #admin-support-badge-mobile").forEach((el) => {
    el.hidden = !show;
  });
}

async function pollSupportUnread() {
  try {
    const data = await api.get("/api/admin/support/unread");
    setSupportBadge(data.unread || 0);
  } catch {
    // ignore transient errors
  }
}

async function boot() {
  initTelegram();
  initSidebarToggle();
  try {
    await ensureAuth();
  } catch (err) {
    main.innerHTML = `<div class="center-loader">${err.message || "Открой это приложение через кнопку в Telegram-боте."}</div>`;
    return;
  }

  const me = await api.get("/api/me").catch(() => null);
  if (!me || me.role < 2) {
    main.innerHTML = `<div class="center-loader">Недостаточно прав для доступа к админ-панели.</div>`;
    document.querySelector(".sidebar")?.remove();
    document.querySelector(".bottom-nav")?.remove();
    return;
  }

  try {
    await router.render();
  } catch (err) {
    toast(err.message || "Ошибка загрузки");
  }

  pollSupportUnread();
  setInterval(pollSupportUnread, 20000);
  window.addEventListener("hashchange", () => {
    if (window.location.hash.replace("#", "") === "support") {
      setTimeout(pollSupportUnread, 500);
    }
  });
}

boot();
