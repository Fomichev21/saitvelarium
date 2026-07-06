import { initTelegram } from "./telegram.js";
import { ensureAuth, api } from "./api.js";
import { createRouter } from "./router.js";
import { toast } from "./ui.js";
import { initSidebarToggle } from "./sidebar.js";
import { renderHome } from "./pages/home.js";
import { renderReferrals } from "./pages/referrals.js";
import { renderSupport } from "./pages/support.js";
import { renderProfile } from "./pages/profile.js";

const main = document.getElementById("main");

const routes = {
  home: () => renderHome(main),
  referrals: () => renderReferrals(main),
  support: () => renderSupport(main),
  profile: () => renderProfile(main),
};

function setActiveNav(route) {
  document.querySelectorAll(".nav-item[data-route]").forEach((el) => {
    el.classList.toggle("active", el.dataset.route === route);
  });
  document.querySelector(".sidebar-header")?.classList.toggle("no-avatar", route === "home");
}

document.querySelectorAll(".nav-item[data-route]").forEach((el) => {
  el.addEventListener("click", () => {
    window.location.hash = el.dataset.route;
  });
});

const router = createRouter(routes, "home", setActiveNav);

function setSupportBadge(count) {
  const show = count > 0;
  document.querySelectorAll("#support-badge, #support-badge-mobile").forEach((el) => {
    el.hidden = !show;
  });
}

async function pollSupportUnread() {
  try {
    const data = await api.get("/api/support/unread");
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
  if (me && me.role >= 2) {
    const slot = document.getElementById("admin-switch-slot");
    if (slot) slot.innerHTML = `<a class="panel-switch" href="/admin">Админ-панель →</a>`;

    const bottomNav = document.querySelector(".bottom-nav");
    if (bottomNav && !bottomNav.querySelector("#bottom-nav-admin")) {
      const adminBtn = document.createElement("button");
      adminBtn.className = "nav-item";
      adminBtn.id = "bottom-nav-admin";
      adminBtn.innerHTML = `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V11M12 20V4M20 20v-7"/></svg><span>Админ</span>`;
      adminBtn.addEventListener("click", () => {
        window.location.href = "/admin";
      });
      bottomNav.appendChild(adminBtn);
    }
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
