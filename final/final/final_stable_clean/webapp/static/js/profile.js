// Velarium VPN — web profile (works for Telegram- or e-mail-authenticated visitors)
(function () {
  "use strict";

  var TOKEN_KEY = "velarium_web_token";
  var isLocal = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  var state = { cfg: null };

  function $(sel) { return document.querySelector(sel); }
  function token() { return localStorage.getItem(TOKEN_KEY); }
  function authHeaders() { return { Authorization: "Bearer " + token() }; }
  function money(n) { return Number(n).toLocaleString("ru-RU"); }

  function showGate() {
    $("#pr-gate").hidden = false;
    $("#pr-content").hidden = true;
    $("#pr-header-actions").hidden = true;
  }

  function showContent() {
    $("#pr-gate").hidden = true;
    $("#pr-content").hidden = false;
    $("#pr-header-actions").hidden = false;
  }

  function api(path, opts) {
    opts = opts || {};
    opts.headers = Object.assign({}, opts.headers || {}, authHeaders());
    return fetch(path, opts).then(function (r) {
      if (r.status === 401) { localStorage.removeItem(TOKEN_KEY); showGate(); return Promise.reject(new Error("unauthorized")); }
      return r;
    });
  }

  // ---------- load + render profile ----------
  function loadProfile() {
    showContent();
    Promise.all([
      api("/api/me").then(function (r) { return r.json(); }),
      api("/api/subscription").then(function (r) { return r.json(); }),
      api("/api/referral").then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }),
      api("/api/payments/history").then(function (r) { return r.ok ? r.json() : { payments: [] }; }).catch(function () { return { payments: [] }; })
    ]).then(function (results) {
      renderMe(results[0]);
      renderSubscription(results[1]);
      if (results[2]) renderReferral(results[2]);
      renderHistory(results[3].payments || []);
      loadQr();
    }).catch(function (err) {
      if (String(err.message) !== "unauthorized") console.error(err);
    });
  }

  function renderMe(me) {
    var name = me.first_name || me.username || "";
    $("#pr-name").textContent = name ? ", " + name : "";
    var identity = me.username ? "@" + me.username : (me.email || ("ID " + me.user_id));
    $("#pr-identity").textContent = "Аккаунт: " + identity;
  }

  function renderSubscription(sub) {
    var badge = $("#pr-sub-badge"), title = $("#pr-sub-title"), desc = $("#pr-sub-desc"), bar = $("#pr-sub-bar-fill"), days = $("#pr-sub-days"), cta = $("#pr-sub-cta");
    var map = {
      active: { cls: "active", label: "Активна", title: "Подписка активна" },
      trial: { cls: "trial", label: "Пробный период", title: "Пробный доступ активен" },
      none: { cls: "none", label: "Нет подписки", title: "Подписка не активна" }
    };
    var m = map[sub.status] || map.none;
    badge.textContent = m.label;
    badge.className = "pr-sub-badge " + m.cls;
    title.textContent = m.title;

    if (sub.status === "none") {
      desc.textContent = "Оформи подписку, чтобы подключиться к VPN.";
      bar.style.width = "0%";
      days.textContent = "";
      cta.textContent = "Оформить подписку";
    } else {
      var pct = sub.total_days ? Math.max(4, Math.min(100, Math.round((sub.days_remaining / sub.total_days) * 100))) : 0;
      bar.style.width = pct + "%";
      days.textContent = sub.days_remaining + " дн. осталось";
      var untilStr = (sub.expires_at || "").slice(0, 10);
      desc.textContent = "Действует до " + untilStr;
      cta.textContent = "Продлить подписку";
    }

    var val = $("#pr-key-value");
    val.textContent = sub.subscription_url || "Ключ появится после оплаты";
  }

  function renderReferral(ref) {
    $("#pr-ref-bonus").textContent = ref.bonus_days || 3;
    $("#pr-ref-link").textContent = ref.link || "—";
    $("#pr-ref-total").textContent = ref.total || 0;
    $("#pr-ref-rewarded").textContent = ref.rewarded || 0;
  }

  var STATUS_ICON = { paid: "✓", pending: "…", failed: "✕" };
  function renderHistory(payments) {
    var wrap = $("#pr-history-list");
    if (!payments.length) { wrap.innerHTML = '<p class="pr-empty">Платежей пока нет.</p>'; return; }
    var html = payments.map(function (p) {
      var status = p.status || "pending";
      var icon = STATUS_ICON[status] || "?";
      var date = (p.created_at || "").slice(0, 10);
      return (
        '<div class="pr-history-row">' +
        '<span class="pr-history-status ' + status + '">' + icon + "</span>" +
        '<span class="pr-history-main">' + (p.tariff_code || "") + '<div class="pr-history-date">' + date + "</div></span>" +
        '<span class="pr-history-amount">' + money(p.amount) + " ₽</span>" +
        "</div>"
      );
    }).join("");
    wrap.innerHTML = html;
  }

  function loadQr() {
    api("/api/subscription/key/qrcode")
      .then(function (r) { return r.ok ? r.blob() : Promise.reject(); })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var img = $("#pr-qr-img");
        img.src = url;
        $("#pr-qr-wrap").hidden = false;
      })
      .catch(function () { $("#pr-qr-wrap").hidden = true; });
  }

  // ---------- copy buttons ----------
  function bindCopy(btnSel, valueSel) {
    var btn = $(btnSel);
    if (!btn) return;
    btn.addEventListener("click", function () {
      var text = ($(valueSel) || {}).textContent || "";
      if (!text || text === "—") return;
      if (navigator.clipboard) navigator.clipboard.writeText(text);
      var original = btn.textContent;
      btn.textContent = "Скопировано";
      btn.classList.add("copied");
      setTimeout(function () { btn.textContent = original; btn.classList.remove("copied"); }, 2000);
    });
  }

  // ---------- login gate (tabs + telegram + email OTP) ----------
  function setupGate() {
    document.querySelectorAll(".co-tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        var name = tab.getAttribute("data-tab");
        document.querySelectorAll(".co-tab").forEach(function (t) { t.classList.toggle("is-active", t === tab); });
        document.querySelectorAll(".co-tabpanel").forEach(function (p) { p.classList.toggle("is-active", p.getAttribute("data-tab") === name); });
      });
    });

    var fallback = $("#tg-continue");
    var slot = $("#tg-login-slot");
    if (state.cfg) {
      if (fallback) fallback.setAttribute("href", state.cfg.bot_url + "?start=profile");
      if (slot && !isLocal && state.cfg.bot_username) {
        var s = document.createElement("script");
        s.src = "https://telegram.org/js/telegram-widget.js?22";
        s.async = true;
        s.setAttribute("data-telegram-login", state.cfg.bot_username);
        s.setAttribute("data-size", "large");
        s.setAttribute("data-radius", "12");
        s.setAttribute("data-onauth", "onTelegramAuth(user)");
        slot.appendChild(s);
      }
    }

    bindEmailFlow();
    bindCopy("#pr-key-copy", "#pr-key-value");
    bindCopy("#pr-ref-copy", "#pr-ref-link");

    var logout = $("#pr-logout");
    if (logout) logout.addEventListener("click", function () { localStorage.removeItem(TOKEN_KEY); showGate(); });
  }

  window.onTelegramAuth = function (user) {
    fetch("/api/auth/telegram-login", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(user)
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (data) { localStorage.setItem(TOKEN_KEY, data.token); loadProfile(); })
      .catch(function () { /* stay on gate */ });
  };

  function bindEmailFlow() {
    var emailInput = $("#email-input"), codeInput = $("#code-input");
    var sendBtn = $("#email-send"), verifyBtn = $("#email-verify"), resendBtn = $("#email-resend"), changeBtn = $("#email-change");
    if (!emailInput || !sendBtn) return;
    var pendingEmail = "";

    function showError(id, msg) { var e = $(id); if (e) { e.textContent = msg; e.hidden = !msg; } }

    function cooldown(seconds) {
      if (!resendBtn) return;
      var left = seconds; resendBtn.disabled = true;
      var base = "Отправить код снова"; resendBtn.textContent = base + " (" + left + ")";
      var timer = setInterval(function () {
        left--;
        if (left <= 0) { clearInterval(timer); resendBtn.disabled = false; resendBtn.textContent = base; }
        else resendBtn.textContent = base + " (" + left + ")";
      }, 1000);
    }

    function sendCode() {
      var email = (emailInput.value || "").trim();
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) { showError("#email-error", "Введите корректный e-mail"); return; }
      showError("#email-error", "");
      sendBtn.disabled = true; sendBtn.textContent = "Отправляем…";
      fetch("/api/checkout/email/start", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: email }) })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          sendBtn.disabled = false; sendBtn.textContent = "Получить код";
          if (!res.ok) { showError("#email-error", (res.d && res.d.detail) || "Не удалось отправить код"); return; }
          pendingEmail = email;
          $("#email-sent-to").textContent = email;
          $("#estep-email").hidden = true; $("#estep-code").hidden = false;
          var hint = $("#email-dev-hint");
          if (res.d && res.d.dev_code) { hint.hidden = false; hint.textContent = "Dev-режим (SMTP не настроен): код — " + res.d.dev_code; }
          else hint.hidden = true;
          cooldown(res.d.cooldown || 45);
          if (codeInput) codeInput.focus();
        })
        .catch(function () { sendBtn.disabled = false; sendBtn.textContent = "Получить код"; showError("#email-error", "Ошибка сети"); });
    }

    function verifyCode() {
      var code = (codeInput.value || "").trim();
      if (code.length < 6) { showError("#code-error", "Введите 6-значный код"); return; }
      showError("#code-error", "");
      verifyBtn.disabled = true; verifyBtn.textContent = "Проверяем…";
      fetch("/api/checkout/email/verify", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email: pendingEmail, code: code }) })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          if (!res.ok) { verifyBtn.disabled = false; verifyBtn.textContent = "Войти"; showError("#code-error", (res.d && res.d.detail) || "Неверный код"); return; }
          localStorage.setItem(TOKEN_KEY, res.d.token);
          loadProfile();
        })
        .catch(function () { verifyBtn.disabled = false; verifyBtn.textContent = "Войти"; showError("#code-error", "Ошибка сети"); });
    }

    sendBtn.addEventListener("click", sendCode);
    if (verifyBtn) verifyBtn.addEventListener("click", verifyCode);
    if (resendBtn) resendBtn.addEventListener("click", sendCode);
    if (changeBtn) changeBtn.addEventListener("click", function () { $("#estep-code").hidden = true; $("#estep-email").hidden = false; showError("#code-error", ""); emailInput.focus(); });
    if (codeInput) codeInput.addEventListener("keydown", function (e) { if (e.key === "Enter") verifyCode(); });
    emailInput.addEventListener("keydown", function (e) { if (e.key === "Enter") sendCode(); });
  }

  // ---------- init ----------
  var FALLBACK_CFG = { bot_url: "https://t.me/Velariumvpn_bot", support_url: "https://t.me/Velarium_Support" };
  fetch("/api/public/config").then(function (r) { return r.ok ? r.json() : Promise.reject(); })
    .then(function (cfg) { state.cfg = Object.assign({}, FALLBACK_CFG, cfg); afterConfig(); })
    .catch(function () { state.cfg = FALLBACK_CFG; afterConfig(); });

  function afterConfig() {
    document.querySelectorAll("[data-link]").forEach(function (a) {
      var key = a.getAttribute("data-link");
      var map = { bot: state.cfg.bot_url, support: state.cfg.support_url };
      if (map[key]) { a.setAttribute("href", map[key]); a.setAttribute("target", "_blank"); a.setAttribute("rel", "noopener"); }
    });
    setupGate();
    if (token()) loadProfile(); else showGate();
  }
})();
