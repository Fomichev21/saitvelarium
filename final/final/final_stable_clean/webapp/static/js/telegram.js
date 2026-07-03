const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;

export function initTelegram() {
  if (!tg) return;
  tg.ready();
  tg.expand();
  try {
    tg.setHeaderColor("#0b0b0c");
    tg.setBackgroundColor("#0b0b0c");
  } catch (e) {
    /* older client versions may not support this */
  }
}

export function getInitData() {
  return tg ? tg.initData || "" : "";
}

export function hapticSuccess() {
  if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
}

export function hapticError() {
  if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("error");
}

export function openLink(url) {
  if (tg && tg.openTelegramLink && url.includes("t.me")) {
    tg.openTelegramLink(url);
  } else if (tg && tg.openLink) {
    tg.openLink(url);
  } else {
    window.open(url, "_blank");
  }
}
