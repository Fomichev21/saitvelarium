// Velarium VPN — landing interactions
(function () {
  "use strict";

  document.documentElement.classList.add("js");

  // Year
  var y = document.getElementById("year");
  if (y) y.textContent = String(new Date().getFullYear());

  // Sticky nav shadow
  var nav = document.getElementById("nav");
  function onScroll() {
    if (!nav) return;
    nav.classList.toggle("scrolled", window.scrollY > 8);
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // Reveal on scroll
  var revealEls = [];
  document.querySelectorAll(".section, .final-cta, .hero-visual").forEach(function (el) {
    el.classList.add("reveal");
    revealEls.push(el);
  });
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add("in"); });
  }

  // Scroll progress bar
  var progress = document.getElementById("scroll-progress");
  function onScrollProgress() {
    if (!progress) return;
    var h = document.documentElement;
    var max = h.scrollHeight - h.clientHeight;
    progress.style.width = (max > 0 ? (h.scrollTop / max) * 100 : 0) + "%";
  }
  window.addEventListener("scroll", onScrollProgress, { passive: true });
  onScrollProgress();

  // Staggered card reveals (+ mark cards as spotlight targets)
  var revealIO = ("IntersectionObserver" in window)
    ? new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); revealIO.unobserve(e.target); } });
      }, { threshold: 0.15 })
    : null;

  function decorateGrids() {
    document.querySelectorAll(".features, .steps, .pricing, .apps, .reviews").forEach(function (grid) {
      var items = grid.children;
      for (var i = 0; i < items.length; i++) {
        var el = items[i];
        if (el.classList.contains("reveal-item")) continue;
        el.classList.add("reveal-item", "tilt");
        el.style.setProperty("--rd", (i % 4) * 0.08 + "s");
        if (revealIO) revealIO.observe(el); else el.classList.add("in");
      }
    });
  }
  decorateGrids();

  // Cursor spotlight — delegated so dynamically rendered cards work too
  document.addEventListener("mousemove", function (e) {
    var card = e.target && e.target.closest ? e.target.closest(".tilt") : null;
    if (!card) return;
    var r = card.getBoundingClientRect();
    card.style.setProperty("--mx", (e.clientX - r.left) + "px");
    card.style.setProperty("--my", (e.clientY - r.top) + "px");
  }, { passive: true });

  // Smooth FAQ accordion (keep content rendered, animate height)
  var faqItems = document.querySelectorAll(".faq details");
  faqItems.forEach(function (d) {
    d.setAttribute("open", ""); // keep rendered; visibility controlled by .open class
    var summary = d.querySelector("summary");
    var panel = d.querySelector("p");
    if (!summary || !panel) return;
    summary.addEventListener("click", function (e) {
      e.preventDefault();
      var willOpen = !d.classList.contains("open");
      faqItems.forEach(function (o) {
        if (o !== d) { o.classList.remove("open"); var p = o.querySelector("p"); if (p) p.style.maxHeight = "0px"; }
      });
      if (willOpen) { d.classList.add("open"); panel.style.maxHeight = panel.scrollHeight + 40 + "px"; }
      else { d.classList.remove("open"); panel.style.maxHeight = "0px"; }
    });
  });

  // Scrollspy: highlight the nav link for the section in view
  var navLinks = document.querySelectorAll(".nav-links a");
  var linkMap = {};
  navLinks.forEach(function (a) {
    var href = a.getAttribute("href") || "";
    if (href.charAt(0) === "#") linkMap[href.slice(1)] = a;
  });
  var spyTargets = Object.keys(linkMap).map(function (id) { return document.getElementById(id); }).filter(Boolean);
  if ("IntersectionObserver" in window && spyTargets.length) {
    var spyIO = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          navLinks.forEach(function (a) { a.classList.remove("active"); });
          if (linkMap[e.target.id]) linkMap[e.target.id].classList.add("active");
        }
      });
    }, { rootMargin: "-45% 0px -50% 0px", threshold: 0 });
    spyTargets.forEach(function (s) { spyIO.observe(s); });
  }

  // Count-up stats
  function animateCount(el) {
    var to = parseFloat(el.getAttribute("data-to")) || 0;
    var suffix = el.getAttribute("data-suffix") || "";
    var isFloat = String(to).indexOf(".") !== -1 || (el.getAttribute("data-to") || "").indexOf(".") !== -1;
    var dur = 1400, start = null;
    function frame(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      var val = to * eased;
      el.textContent = (isFloat ? val.toFixed(1) : Math.round(val).toLocaleString("ru-RU")) + (p === 1 ? suffix : "");
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }
  var counters = document.querySelectorAll(".count");
  if ("IntersectionObserver" in window && counters.length) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { animateCount(e.target); cio.unobserve(e.target); }
      });
    }, { threshold: 0.5 });
    counters.forEach(function (el) { cio.observe(el); });
  } else {
    counters.forEach(function (el) { el.textContent = (el.getAttribute("data-to") || "0") + (el.getAttribute("data-suffix") || ""); });
  }

  // Parallax: jellyfish + wordmark react to the mouse (depth)
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var stage = document.querySelector(".jelly-stage");
  var introCopy = document.querySelector(".intro-copy");
  var introEl = document.getElementById("intro");
  if (!reduceMotion && stage && introEl) {
    var tx = 0, ty = 0, cx = 0, cy = 0, praf = null;
    function paraLoop() {
      cx += (tx - cx) * 0.08;
      cy += (ty - cy) * 0.08;
      stage.style.transform = "translate(" + (cx * 30).toFixed(2) + "px," + (cy * 22).toFixed(2) + "px) rotate(" + (cx * 3).toFixed(2) + "deg)";
      if (introCopy) introCopy.style.transform = "translate(" + (cx * -14).toFixed(2) + "px," + (cy * -10).toFixed(2) + "px)";
      if (Math.abs(tx - cx) > 0.0008 || Math.abs(ty - cy) > 0.0008) praf = requestAnimationFrame(paraLoop);
      else praf = null;
    }
    window.addEventListener("mousemove", function (e) {
      if (introEl.getBoundingClientRect().bottom < 0) return; // skip when intro scrolled away
      tx = (e.clientX / window.innerWidth) - 0.5;
      ty = (e.clientY / window.innerHeight) - 0.5;
      if (!praf) praf = requestAnimationFrame(paraLoop);
    }, { passive: true });
  }

  // Config-driven links + pricing (graceful fallback if endpoint absent)
  var FALLBACK = {
    bot_url: "https://t.me/",
    support_url: "https://t.me/Velarium_Support",
    channel_url: "https://t.me/VelariumVPNchannel",
    terms_url: "https://telegra.ph/Polzovatelskoe-soglashenie-04-01-19",
    privacy_url: "https://telegra.ph/Politika-konfidencialnosti-06-21-31",
    referral_bonus_days: 3,
    tariffs: null
  };

  function applyLinks(cfg) {
    var map = {
      bot: cfg.bot_url, support: cfg.support_url, channel: cfg.channel_url,
      terms: cfg.terms_url, privacy: cfg.privacy_url,
      checkout: "/checkout?plan=quarter"
    };
    document.querySelectorAll("[data-link]").forEach(function (a) {
      var key = a.getAttribute("data-link");
      if (!map[key]) return;
      a.setAttribute("href", map[key]);
      if (/^https?:/.test(map[key])) { a.setAttribute("target", "_blank"); a.setAttribute("rel", "noopener"); }
      else { a.removeAttribute("target"); }
    });
  }

  function renderPricing(tariffs) {
    if (!tariffs) return;
    var grid = document.getElementById("pricing-grid");
    if (!grid) return;
    var order = ["month", "quarter", "year"];
    var featured = "quarter";
    var suffix = { month: "/мес", quarter: "/3 мес", year: "/год" };
    var monthly = tariffs.month ? Number(tariffs.month.price) : 0;
    var html = "";
    order.forEach(function (key) {
      var t = tariffs[key];
      if (!t) return;
      var feat = key === featured;
      var months = Math.max(1, Math.round((Number(t.duration_days) || 30) / 30));
      var perMonth = Math.round(Number(t.price) / months);
      // honest savings vs paying monthly
      var saveHtml = "";
      var permoHtml = "";
      if (months > 1 && monthly > 0) {
        var fullPrice = monthly * months;
        var savePct = Math.round((1 - Number(t.price) / fullPrice) * 100);
        if (savePct > 0) saveHtml = '<span class="price-save">−' + savePct + "%</span>";
        permoHtml = '<p class="price-permonth">≈ <b>' + perMonth + " ₽</b> в месяц</p>";
      }
      html +=
        '<article class="glass price' + (feat ? " price-featured" : "") + '">' +
        (feat ? '<span class="price-badge">Популярный</span>' : "") +
        saveHtml +
        '<div class="price-head"><h3>' + t.title + "</h3></div>" +
        '<div class="price-amount"><b>' + t.price + "</b> ₽<span>" + (suffix[key] || "") + "</span></div>" +
        permoHtml +
        '<p class="price-desc">' + (t.description || "") + "</p>" +
        '<ul class="price-list">' +
          "<li>Все серверы и локации</li><li>Несколько устройств</li><li>Без логов и слежки</li><li>Поддержка в Telegram</li>" +
        "</ul>" +
        '<a class="btn ' + (feat ? "btn-primary" : "btn-ghost") + ' btn-block" href="/checkout?plan=' + key + '">Выбрать тариф</a>' +
        "</article>";
    });
    if (html) grid.innerHTML = html;
  }

  // Sticky mobile CTA: reveal after hero scrolls away, hide at footer
  var mcta = document.getElementById("mobile-cta");
  if (mcta) {
    var footerEl = document.querySelector(".footer");
    window.addEventListener("scroll", function () {
      var pastHero = window.scrollY > 520;
      var atFooter = footerEl && footerEl.getBoundingClientRect().top < window.innerHeight;
      mcta.classList.toggle("show", pastHero && !atFooter);
    }, { passive: true });
  }

  fetch("/api/public/config", { headers: { Accept: "application/json" } })
    .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
    .then(function (cfg) {
      var merged = Object.assign({}, FALLBACK, cfg);
      renderPricing(merged.tariffs);
      applyLinks(merged); // re-apply after re-render
      decorateGrids();    // stagger + spotlight for freshly rendered price cards
    })
    .catch(function () { applyLinks(FALLBACK); });
})();
