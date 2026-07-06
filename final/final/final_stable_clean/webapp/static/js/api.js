import { getInitData } from "./telegram.js";

const TOKEN_KEY = "velarium_token";
let authPromise = null;

function getToken() {
  return sessionStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  sessionStorage.removeItem(TOKEN_KEY);
}

async function authenticate() {
  if (!authPromise) {
    authPromise = (async () => {
      const initData = getInitData();
      if (!initData) {
        throw new Error("Приложение нужно открывать через Telegram");
      }
      const res = await fetch("/api/auth/telegram", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ init_data: initData }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Не удалось авторизоваться");
      }
      const data = await res.json();
      setToken(data.token);
      return data;
    })().finally(() => {
      authPromise = null;
    });
  }
  return authPromise;
}

export async function ensureAuth() {
  if (!getToken()) {
    await authenticate();
  }
}

async function request(path, options = {}, retry = true) {
  const token = getToken();
  const headers = Object.assign({}, options.headers || {});
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(path, { ...options, headers });

  if (res.status === 401 && retry) {
    await authenticate();
    return request(path, options, false);
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const message = body.detail || `Ошибка запроса (${res.status})`;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  put: (path, body) => request(path, { method: "PUT", body: body !== undefined ? JSON.stringify(body) : undefined }),
  del: (path) => request(path, { method: "DELETE" }),
};

export async function fetchWithAuth(path, retry = true) {
  const token = getToken();
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(path, { headers });

  if (res.status === 401 && retry) {
    await authenticate();
    return fetchWithAuth(path, false);
  }
  if (!res.ok) {
    throw new Error(`Ошибка запроса (${res.status})`);
  }
  return res;
}

export async function downloadFile(path, fallbackName) {
  const res = await fetchWithAuth(path);
  const disposition = res.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : fallbackName;

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
