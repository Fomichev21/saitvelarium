const STORAGE_KEY = "velarium_sidebar_collapsed";

export function initSidebarToggle() {
  const shell = document.getElementById("app-shell");
  if (!shell) return;

  if (localStorage.getItem(STORAGE_KEY) === "1") {
    shell.classList.add("sidebar-collapsed");
  }

  const toggleFn = () => {
    const collapsed = shell.classList.toggle("sidebar-collapsed");
    localStorage.setItem(STORAGE_KEY, collapsed ? "1" : "0");
  };

  document.getElementById("menu-toggle")?.addEventListener("click", toggleFn);
  document.getElementById("menu-toggle-float")?.addEventListener("click", toggleFn);
}
