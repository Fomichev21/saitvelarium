export function createRouter(routes, defaultRoute, onNavigate) {
  function currentPath() {
    const hash = window.location.hash.replace(/^#/, "");
    return hash || defaultRoute;
  }

  async function render() {
    const path = currentPath();
    const handler = routes[path] || routes[defaultRoute];
    if (onNavigate) onNavigate(path);

    try {
      await handler();
    } catch (err) {
      renderError(err);
      return;
    }

    const main = document.getElementById("main");
    if (main) {
      main.classList.remove("page-enter");
      void main.offsetWidth;
      main.classList.add("page-enter");
    }
  }

  function renderError(err) {
    const main = document.getElementById("main");
    if (!main) return;
    main.innerHTML = `
      <div class="card" style="text-align:center;">
        <p class="section-title">Не удалось загрузить</p>
        <p class="muted" style="margin-bottom:14px;">${(err && err.message) || "Проверь соединение и попробуй ещё раз."}</p>
        <button class="btn btn-primary" id="router-retry">Повторить</button>
      </div>
    `;
    main.querySelector("#router-retry")?.addEventListener("click", render);
  }

  window.addEventListener("hashchange", render);
  return { render, currentPath, navigate: (path) => (window.location.hash = path) };
}

export function h(html) {
  const template = document.createElement("template");
  template.innerHTML = html.trim();
  return template.content.firstElementChild;
}
