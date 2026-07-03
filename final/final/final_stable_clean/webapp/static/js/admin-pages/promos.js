import { api } from "../api.js";
import { toast, showModal, closeModal } from "../ui.js";
import { ICON_PLUS, ICON_EDIT, ICON_TRASH } from "../icons.js";

let root;

export async function renderPromos(container) {
  root = container;
  await load();
}

async function load() {
  root.innerHTML = `<div class="center-loader">Загрузка…</div>`;
  const data = await api.get("/api/admin/promos");

  root.innerHTML = `
    <div class="card">
      <button class="btn btn-primary" id="btn-new-promo">${ICON_PLUS}Новый промокод</button>
    </div>
    ${
      data.promos.length
        ? `<div class="card">${data.promos
            .map(
              (p) => `
      <div class="list-row" data-code="${p.code}">
        <div>
          <div style="font-weight:700;">${p.code}</div>
          <div class="faint">${p.value} дн. · использовано ${p.used_count}/${p.usage_limit}</div>
        </div>
        <div class="btn-row" style="width:auto;">
          <button class="btn btn-secondary btn-icon" data-edit="${p.code}">${ICON_EDIT}</button>
          <button class="btn btn-danger btn-icon" data-del="${p.code}">${ICON_TRASH}</button>
        </div>
      </div>`
            )
            .join("")}</div>`
        : `<p class="muted">Промокодов пока нет.</p>`
    }
  `;

  root.querySelector("#btn-new-promo").addEventListener("click", () => openForm());
  root.querySelectorAll("[data-edit]").forEach((btn) => {
    const promo = data.promos.find((p) => p.code === btn.dataset.edit);
    btn.addEventListener("click", () => openForm(promo));
  });
  root.querySelectorAll("[data-del]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      if (!confirm(`Удалить промокод ${btn.dataset.del}?`)) return;
      await api.del(`/api/admin/promos/${btn.dataset.del}`);
      toast("Удалено");
      await load();
    });
  });
}

function openForm(promo) {
  const isEdit = !!promo;
  showModal(
    `
    <p class="section-title">${isEdit ? "Изменить промокод" : "Новый промокод"}</p>
    <input class="input" id="f-code" placeholder="Код" value="${promo?.code || ""}" ${isEdit ? "disabled" : ""} />
    <input class="input" id="f-days" type="number" placeholder="Дней подписки" value="${promo?.value || ""}" />
    <input class="input" id="f-limit" type="number" placeholder="Лимит использований" value="${promo?.usage_limit || 1}" />
    <div class="btn-row">
      <button class="btn btn-primary" id="f-save">Сохранить</button>
      <button class="btn btn-secondary" id="f-cancel">Отмена</button>
    </div>
  `,
    (modal) => {
      modal.querySelector("#f-cancel").addEventListener("click", closeModal);
      modal.querySelector("#f-save").addEventListener("click", async () => {
        const code = modal.querySelector("#f-code").value.trim();
        const days = Number(modal.querySelector("#f-days").value);
        const usage_limit = Number(modal.querySelector("#f-limit").value);
        if (!code || !days || !usage_limit) {
          toast("Заполни все поля");
          return;
        }
        if (isEdit) {
          await api.put(`/api/admin/promos/${code}`, { code, days, usage_limit });
        } else {
          await api.post("/api/admin/promos", { code, days, usage_limit });
        }
        toast("Сохранено");
        closeModal();
        await load();
      });
    }
  );
}
