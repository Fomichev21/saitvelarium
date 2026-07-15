// Velarium VPN — checkout flow
(function () {
  "use strict";

  var TOKEN_KEY = "velarium_web_token";
  var PLAN_ORDER = ["month", "quarter", "year"];
  var FEATURED = "quarter";
  var SUFFIX = { month: "/мес", quarter: "/3 мес", year: "/год" };

  var params = new URLSearchParams(location.search);
  var isLocal = /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);

  var state = {
    cfg: null,
    tariffs: null,
    plan: params.get("plan") || FEATURED,
    step: 1
  };

  // ---------- helpers ----------
  function $(sel) { return document.querySelector(sel); }
  function money(n) { return Number(n).toLocaleString("ru-RU"); }
  function months(t) { return Math.max(1, Math.round((Number(t.duration_days) || 30) / 30)); }
  function botStart(suffix) {
    var base = (state.cfg && state.cfg.bot_url) || "https://t.me/VelariumVPNbot";
    return base + "?start=" + suffix;
  }

  function planMeta(key) {
    var t = state.tariffs[key];
    if (!t) return null;
    var m = months(t);
    var perMonth = Math.round(Number(t.price) / m);
    var monthly = state.tariffs.month ? Number(state.tariffs.month.price) : 0;
    var savePct = 0;
    if (m > 1 && monthly > 0) savePct = Math.round((1 - Number(t.price) / (monthly * m)) * 100);
    return { t: t, m: m, perMonth: perMonth, savePct: savePct };
  }

  // ---------- render plans ----------
  function renderPlans() {
    var wrap = $("#co-plans");
    if (!wrap || !state.tariffs) return;
    var html = "";
    PLAN_ORDER.forEach(function (key) {
      var meta = planMeta(key);
      if (!meta) return;
      var sel = key === state.plan ? " is-selected" : "";
      var tags = "";
      if (key === FEATURED) tags += '<span class="co-plan-tag">Популярный</span>';
      if (meta.savePct > 0) tags += '<span class="co-plan-tag save">−' + meta.savePct + "%</span>";
      var perMonth = meta.m > 1 ? '<div class="co-plan-desc">≈ ' + money(meta.perMonth) + " ₽ в месяц</div>" : '<div class="co-plan-desc">' + (meta.t.description || "") + "</div>";
      html +=
        '<div class="co-plan' + sel + '" data-plan="' + key + '" role="button" tabindex="0">' +
        '<span class="co-plan-radio"></span>' +
        '<div class="co-plan-info"><div class="co-plan-name">' + meta.t.title + tags + "</div>" + perMonth + "</div>" +
        '<div class="co-plan-price"><b>' + money(meta.t.price) + " ₽</b><span>" + (SUFFIX[key] || "") + "</span></div>" +
        "</div>";
    });
    wrap.innerHTML = html;
    wrap.querySelectorAll(".co-plan").forEach(function (el) {
      function pick() { state.plan = el.getAttribute("data-plan"); renderPlans(); renderSummary(); }
      el.addEventListener("click", pick);
      el.addEventListener("keydown", function (e) { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pick(); } });
    });
  }

  function renderSummary() {
    var meta = planMeta(state.plan);
    if (!meta) return;
    $("#sum-plan-name").textContent = meta.t.title;
    $("#sum-plan-price").textContent = money(meta.t.price) + " ₽";
    $("#sum-total").textContent = money(meta.t.price) + " ₽";
    var pm = $("#sum-permonth");
    pm.innerHTML = meta.m > 1 ? "≈ <b>" + money(meta.perMonth) + " ₽</b> в месяц" : "";
    var save = $("#sum-save");
    save.textContent = meta.savePct > 0 ? "Вы экономите " + meta.savePct + "% против помесячной оплаты" : "";
  }

  // ---------- steps ----------
  function goStep(n) {
    state.step = n;
    document.querySelectorAll(".co-panel").forEach(function (p) {
      p.classList.toggle("is-active", Number(p.getAttribute("data-step")) === n);
    });
    document.querySelectorAll(".co-step").forEach(function (s) {
      var sn = Number(s.getAttribute("data-step"));
      s.classList.toggle("is-active", sn === n);
      s.classList.toggle("is-done", sn < n);
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
    if (n === 2) setupAuthStep();
  }

  // ---------- auth / payment ----------
  var authBound = false;
  function setupAuthStep() {
    var fallback = $("#tg-continue");
    if (fallback) fallback.setAttribute("href", botStart("buy_" + state.plan));

    // On a real domain, show the official Telegram Login Widget for on-site checkout.
    var slot = $("#tg-login-slot");
    if (slot && !slot.dataset.loaded && !isLocal && state.cfg && state.cfg.bot_username) {
      slot.dataset.loaded = "1";
      var s = document.createElement("script");
      s.src = "https://telegram.org/js/telegram-widget.js?22";
      s.async = true;
      s.setAttribute("data-telegram-login", state.cfg.bot_username);
      s.setAttribute("data-size", "large");
      s.setAttribute("data-radius", "12");
      s.setAttribute("data-request-access", "write");
      s.setAttribute("data-onauth", "onTelegramAuth(user)");
      slot.appendChild(s);
    }

    if (authBound) return;
    authBound = true;

    // Tabs
    document.querySelectorAll(".co-tab").forEach(function (tab) {
      tab.addEventListener("click", function () {
        var name = tab.getAttribute("data-tab");
        document.querySelectorAll(".co-tab").forEach(function (t) { t.classList.toggle("is-active", t === tab); });
        document.querySelectorAll(".co-tabpanel").forEach(function (p) { p.classList.toggle("is-active", p.getAttribute("data-tab") === name); });
      });
    });

    bindEmailFlow();
  }

  function bindEmailFlow() {
    var emailInput = $("#email-input");
    var codeInput = $("#code-input");
    var sendBtn = $("#email-send");
    var verifyBtn = $("#email-verify");
    var resendBtn = $("#email-resend");
    var changeBtn = $("#email-change");
    if (!emailInput || !sendBtn) return;

    function showError(id, msg) { var e = $(id); if (e) { e.textContent = msg; e.hidden = !msg; } }

    function cooldown(seconds) {
      if (!resendBtn) return;
      var left = seconds;
      resendBtn.disabled = true;
      var base = "Отправить код снова";
      resendBtn.textContent = base + " (" + left + ")";
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
      fetch("/api/checkout/email/start", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email })
      })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          sendBtn.disabled = false; sendBtn.textContent = "Получить код";
          if (!res.ok) { showError("#email-error", (res.d && res.d.detail) || "Не удалось отправить код"); return; }
          state.email = email;
          $("#email-sent-to").textContent = email;
          $("#estep-email").hidden = true;
          $("#estep-code").hidden = false;
          var hint = $("#email-dev-hint");
          if (res.d && res.d.dev_code) { hint.hidden = false; hint.textContent = "Dev-режим (SMTP не настроен): код — " + res.d.dev_code; }
          else { hint.hidden = true; }
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
      fetch("/api/checkout/email/verify", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: state.email, code: code })
      })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (res) {
          if (!res.ok) { verifyBtn.disabled = false; verifyBtn.textContent = "Подтвердить и оплатить"; showError("#code-error", (res.d && res.d.detail) || "Неверный код"); return; }
          localStorage.setItem(TOKEN_KEY, res.d.token);
          verifyBtn.textContent = "Создаём заказ…";
          createPayment();
        })
        .catch(function () { verifyBtn.disabled = false; verifyBtn.textContent = "Подтвердить и оплатить"; showError("#code-error", "Ошибка сети"); });
    }

    sendBtn.addEventListener("click", sendCode);
    if (verifyBtn) verifyBtn.addEventListener("click", verifyCode);
    if (resendBtn) resendBtn.addEventListener("click", sendCode);
    if (changeBtn) changeBtn.addEventListener("click", function () {
      $("#estep-code").hidden = true; $("#estep-email").hidden = false; showError("#code-error", ""); emailInput.focus();
    });
    if (codeInput) codeInput.addEventListener("keydown", function (e) { if (e.key === "Enter") verifyCode(); });
    emailInput.addEventListener("keydown", function (e) { if (e.key === "Enter") sendCode(); });
  }

  window.onTelegramAuth = function (user) {
    // Verify login on the server → session → create payment → redirect to pay.
    fetch("/api/auth/telegram-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(user)
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (data) {
        localStorage.setItem(TOKEN_KEY, data.token);
        return createPayment();
      })
      .catch(function () { location.href = botStart("buy_" + state.plan); });
  };

  function createPayment() {
    var token = localStorage.getItem(TOKEN_KEY);
    return fetch("/api/subscription/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: "Bearer " + token },
      body: JSON.stringify({ tariff_code: state.plan })
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (payment) {
        if (payment && payment.url) {
          // remember what to show when the user returns from the payment page
          sessionStorage.setItem("velarium_pending_payment", payment.id);
          location.href = payment.url;
        } else {
          location.href = botStart("buy_" + state.plan);
        }
      })
      .catch(function () { location.href = botStart("buy_" + state.plan); });
  }

  // ---------- delivery (step 3) — three states: processing / failed / done ----------
  function setDeliveryState(which) {
    var map = { processing: "#co-processing", failed: "#co-failed", done: "#co-done" };
    Object.keys(map).forEach(function (k) {
      var el = $(map[k]);
      if (el) el.hidden = k !== which;
    });
  }

  function showProcessing(paymentId) {
    state.pendingPayment = paymentId;
    goStep(3);
    setDeliveryState("processing");
    pollDelivery(paymentId);
  }

  function showFailed() {
    goStep(3);
    setDeliveryState("failed");
  }

  // Poll payment status; only reveal the key once it is really PAID.
  function pollDelivery(paymentId) {
    var token = localStorage.getItem(TOKEN_KEY);
    var tries = 0;
    var MAX = 20; // ~1 min at 3s
    (function tick() {
      tries++;
      fetch("/api/subscription/checkout/" + encodeURIComponent(paymentId) + "/status", {
        headers: { Authorization: "Bearer " + token }
      })
        .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
        .then(function (p) {
          if (p && p.status === "paid") { fetchKeyAndShow(); }
          else if (p && (p.status === "failed" || p.status === "canceled")) { showFailed(); }
          else if (tries < MAX) { setTimeout(tick, 3000); }
          else { showFailed(); }
        })
        .catch(function () { if (tries < MAX) setTimeout(tick, 3000); else showFailed(); });
    })();
  }

  function fetchKeyAndShow() {
    var token = localStorage.getItem(TOKEN_KEY);
    fetch("/api/subscription/key", { headers: { Authorization: "Bearer " + token } })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (d) { showDelivery(d.subscription_url || ""); })
      .catch(function () { showDelivery(""); });
  }

  // Success screen — ONLY called after a confirmed paid status (or demo).
  function showDelivery(key) {
    var val = $("#co-key-value");
    if (val) val.textContent = key || "Ключ появится в кабинете и в боте через несколько секунд…";
    goStep(3);
    setDeliveryState("done");
    fireConfetti();
  }

  // Retry: reopen the same payment link for the pending order.
  function retryPayment() {
    var token = localStorage.getItem(TOKEN_KEY);
    var pid = state.pendingPayment;
    if (!pid || !token) { goStep(1); return; }
    fetch("/api/subscription/checkout/" + encodeURIComponent(pid) + "/status", {
      headers: { Authorization: "Bearer " + token }
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (p) {
        if (p && p.payment_url) { sessionStorage.setItem("velarium_pending_payment", pid); location.href = p.payment_url; }
        else { goStep(1); }
      })
      .catch(function () { goStep(1); });
  }

  function fireConfetti() {
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var wrap = document.createElement("div");
    wrap.className = "co-confetti";
    var colors = ["#ff5b5b", "#ff8a8a", "#c81f28", "#5fe3a1", "#ffcf4a"];
    for (var i = 0; i < 70; i++) {
      var c = document.createElement("i");
      c.style.left = Math.random() * 100 + "%";
      c.style.background = colors[i % colors.length];
      c.style.animationDuration = (2.2 + Math.random() * 1.8) + "s";
      c.style.animationDelay = (Math.random() * 0.5) + "s";
      c.style.transform = "rotate(" + (Math.random() * 360) + "deg)";
      wrap.appendChild(c);
    }
    document.body.appendChild(wrap);
    setTimeout(function () { wrap.remove(); }, 4600);
  }

  // ---------- init ----------
  function bindStatic() {
    var t2 = $("#to-step-2"); if (t2) t2.addEventListener("click", function () { goStep(2); });
    var b1 = $("#back-to-1"); if (b1) b1.addEventListener("click", function () { goStep(1); });
    var trial = $("#co-trial"); if (trial) trial.addEventListener("click", function () { location.href = botStart("trial"); });

    var copy = $("#co-copy");
    if (copy) copy.addEventListener("click", function () {
      var text = ($("#co-key-value") || {}).textContent || "";
      if (navigator.clipboard) navigator.clipboard.writeText(text);
      copy.textContent = "Скопировано";
      copy.classList.add("copied");
      setTimeout(function () { copy.textContent = "Скопировать"; copy.classList.remove("copied"); }, 2000);
    });

    var retry = $("#co-retry"); if (retry) retry.addEventListener("click", retryPayment);

    var links = {
      bot: (state.cfg && state.cfg.bot_url) || "https://t.me/VelariumVPNbot",
      support: (state.cfg && state.cfg.support_url) || (state.cfg && state.cfg.bot_url) || "https://t.me/VelariumVPNbot"
    };
    document.querySelectorAll("[data-link]").forEach(function (a) {
      var key = a.getAttribute("data-link");
      if (!links[key]) return;
      a.setAttribute("href", links[key]);
      a.setAttribute("target", "_blank"); a.setAttribute("rel", "noopener");
    });
  }

  function afterConfig() {
    renderPlans();
    renderSummary();
    bindStatic();

    var trialTitle = $("#co-trial-title");
    if (trialTitle && state.cfg && state.cfg.trial_days) trialTitle.textContent = state.cfg.trial_days + " дня бесплатно";

    // Returning from a real payment page → verify status first, never assume success.
    var pending = params.get("paid") || sessionStorage.getItem("velarium_pending_payment");
    if (pending && localStorage.getItem(TOKEN_KEY)) {
      sessionStorage.removeItem("velarium_pending_payment");
      showProcessing(pending);
      return;
    }
    // Demo / direct step (for preview only)
    if (params.get("demo") === "1" || params.get("step") === "3") {
      showDelivery("https://sub.velariumvpn.ru/s/EXAMPLE-DEMO-KEY-9f2c1a");
      return;
    }
    goStep(1);
  }

  var FALLBACK_CFG = { bot_url: "https://t.me/VelariumVPNbot", trial_days: 3 };
  fetch("/api/public/config", { headers: { Accept: "application/json" } })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
    .then(function (cfg) {
      state.cfg = Object.assign({}, FALLBACK_CFG, cfg);
      state.tariffs = cfg.tariffs;
      if (!state.tariffs[state.plan]) state.plan = FEATURED;
      afterConfig();
    })
    .catch(function () {
      state.cfg = FALLBACK_CFG;
      state.tariffs = {
        month: { title: "1 месяц", price: 59, duration_days: 30, description: "Оптимально, чтобы попробовать" },
        quarter: { title: "3 месяца", price: 99, duration_days: 90, description: "Самый популярный вариант" },
        year: { title: "12 месяцев", price: 599, duration_days: 365, description: "Максимально выгодный тариф" }
      };
      afterConfig();
    });
})();
