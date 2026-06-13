import CONFIG from "./config.js";

const token = localStorage.getItem("token");
const state = {
  users: [],
  histories: [],
  items: [],
  selectedUserId: null,
  selectedHistoryId: null,
  products: [],
  supermarkets: [],
};

function apiHeaders() {
  return {
    Authorization: `Bearer ${localStorage.getItem("token")}`,
    "Content-Type": "application/json",
  };
}

async function api(path, options = {}) {
  const res = await fetch(`${CONFIG.API_BASE_URL}${path}`, {
    ...options,
    headers: { ...apiHeaders(), ...(options.headers || {}) },
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "index.html";
  }
  return res;
}

async function readError(res) {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    return JSON.stringify(data.detail || data);
  } catch {
    return res.statusText || "Errore sconosciuto";
  }
}

const euro = (v) => Number(v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
const dateLabel = (v) => {
  if (!v) return "N/D";
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString("it-IT", { dateStyle: "medium", timeStyle: "short" });
};
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));

function injectAdminHistoryPanel() {
  if (document.getElementById("panel-history-admin")) return;

  const tabs = document.querySelector(".admin-tabs");
  const desktop = document.querySelector(".admin-desktop");
  if (!tabs || !desktop) return;

  const tab = document.createElement("button");
  tab.className = "admin-tab";
  tab.dataset.adminTab = "history-admin";
  tab.textContent = "Storico spese";
  tabs.appendChild(tab);

  const panel = document.createElement("section");
  panel.className = "admin-panel";
  panel.id = "panel-history-admin";
  panel.innerHTML = `
    <div class="panel-head">
      <div>
        <h2>Storico spese utenti</h2>
        <p>Modifica cronologia spese e prodotti acquistati per ogni utente. I totali vengono ricalcolati automaticamente.</p>
      </div>
      <button type="button" class="primary-btn" id="admin-history-refresh">Aggiorna</button>
    </div>

    <div class="admin-history-layout">
      <aside class="admin-history-users">
        <input id="admin-history-user-search" placeholder="Cerca utente...">
        <div id="admin-history-users-list"></div>
      </aside>

      <section class="admin-history-main">
        <div class="admin-history-subgrid">
          <div class="admin-history-box">
            <h3>Liste spesa passate</h3>
            <div id="admin-history-list" class="admin-history-list">
              <div class="empty-state">Seleziona un utente.</div>
            </div>
          </div>

          <div class="admin-history-box">
            <h3>Dettaglio prodotti</h3>
            <div id="admin-history-detail" class="admin-history-detail">
              <div class="empty-state">Seleziona una lista.</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  `;
  desktop.appendChild(panel);

  tab.addEventListener("click", () => activateHistoryTab());
  document.getElementById("admin-history-refresh")?.addEventListener("click", () => loadUsers());
  document.getElementById("admin-history-user-search")?.addEventListener("input", debounce(() => loadUsers(), 250));
}

function activateHistoryTab() {
  document.querySelectorAll(".admin-tab").forEach(t => t.classList.toggle("active", t.dataset.adminTab === "history-admin"));
  document.querySelectorAll(".admin-panel").forEach(p => p.classList.toggle("active", p.id === "panel-history-admin"));
  if (!state.users.length) loadUsers();
}

async function loadBaseData() {
  const [productsRes, supermarketsRes] = await Promise.all([
    api("/admin/products?limit=500"),
    api("/admin/supermarkets"),
  ]);
  state.products = productsRes.ok ? await productsRes.json() : [];
  state.supermarkets = supermarketsRes.ok ? await supermarketsRes.json() : [];
}

async function loadUsers() {
  const q = document.getElementById("admin-history-user-search")?.value.trim() || "";
  const res = await api(`/admin/history/users?limit=300${q ? `&search=${encodeURIComponent(q)}` : ""}`);
  if (!res.ok) {
    document.getElementById("admin-history-users-list").innerHTML = `<div class="empty-state">Errore utenti: ${esc(await readError(res))}</div>`;
    return;
  }
  state.users = await res.json();
  renderUsers();
}

function renderUsers() {
  const box = document.getElementById("admin-history-users-list");
  if (!box) return;

  if (!state.users.length) {
    box.innerHTML = `<div class="empty-state">Nessun utente trovato.</div>`;
    return;
  }

  box.innerHTML = state.users.map(u => `
    <button type="button" class="history-user-card ${state.selectedUserId === u.id ? "active" : ""}" data-user-id="${u.id}">
      <strong>${esc(u.username || u.email || `Utente #${u.id}`)}</strong>
      <small>${esc(u.email || "")}</small>
      <span>${u.histories_count || 0} spese · ${euro(u.history_total_spent)}</span>
    </button>
  `).join("");

  box.querySelectorAll("[data-user-id]").forEach(btn => {
    btn.addEventListener("click", () => selectUser(Number(btn.dataset.userId)));
  });
}

async function selectUser(userId) {
  state.selectedUserId = userId;
  state.selectedHistoryId = null;
  state.items = [];
  renderUsers();

  const res = await api(`/admin/history/user/${userId}?limit=300`);
  if (!res.ok) {
    document.getElementById("admin-history-list").innerHTML = `<div class="empty-state">Errore storico: ${esc(await readError(res))}</div>`;
    return;
  }

  state.histories = await res.json();
  renderHistories();
  document.getElementById("admin-history-detail").innerHTML = `<div class="empty-state">Seleziona una lista.</div>`;
}

function renderHistories() {
  const box = document.getElementById("admin-history-list");
  if (!state.histories.length) {
    box.innerHTML = `<div class="empty-state">Questo utente non ha spese passate.</div>`;
    return;
  }

  box.innerHTML = state.histories.map(h => `
    <article class="history-admin-card ${state.selectedHistoryId === h.id ? "active" : ""}" data-history-id="${h.id}">
      <div>
        <strong>Spesa #${h.id}</strong>
        <small>${dateLabel(h.created_at)}</small>
      </div>
      <div class="history-admin-card-total">
        <b>${euro(h.total_price)}</b>
        <span>${h.total_items || 0} prodotti</span>
      </div>
      <div class="history-preview-line">
        ${(h.preview_items || []).slice(0, 3).map(i => esc(i.name)).join(", ") || "Nessuna anteprima"}
      </div>
    </article>
  `).join("");

  box.querySelectorAll("[data-history-id]").forEach(card => {
    card.addEventListener("click", () => selectHistory(Number(card.dataset.historyId)));
  });
}

async function selectHistory(historyId) {
  state.selectedHistoryId = historyId;
  renderHistories();

  const res = await api(`/admin/history/${historyId}/items`);
  if (!res.ok) {
    document.getElementById("admin-history-detail").innerHTML = `<div class="empty-state">Errore prodotti: ${esc(await readError(res))}</div>`;
    return;
  }

  state.items = await res.json();
  renderItems();
}

function productOptions(selectedId = null) {
  return `<option value="">Prodotto manuale / snapshot</option>` + state.products.map(p => `
    <option value="${p.id}" ${Number(selectedId) === Number(p.id) ? "selected" : ""}>${esc(p.name)} · ${esc(p.supermarket_name || "")}</option>
  `).join("");
}

function renderItems() {
  const box = document.getElementById("admin-history-detail");
  const history = state.histories.find(h => h.id === state.selectedHistoryId);

  box.innerHTML = `
    <div class="history-detail-head">
      <div>
        <h3>Spesa #${history?.id || state.selectedHistoryId}</h3>
        <p>${dateLabel(history?.created_at)} · totale ${euro(history?.total_price || 0)}</p>
      </div>
      <div class="history-detail-actions">
        <button type="button" class="ghost-btn" id="history-recalc-btn">Ricalcola</button>
        <button type="button" class="delete-btn" id="history-delete-btn">Elimina lista</button>
      </div>
    </div>

    <div class="history-item-add">
      <select id="history-add-product">${productOptions()}</select>
      <input id="history-add-name" placeholder="Nome prodotto manuale">
      <input id="history-add-qty" type="number" min="1" value="1" placeholder="Q.tà">
      <input id="history-add-price" type="number" min="0" step="0.01" placeholder="Prezzo unitario">
      <button type="button" class="primary-btn" id="history-add-btn">Aggiungi</button>
    </div>

    <div class="history-items-table">
      ${state.items.length ? state.items.map(itemRow).join("") : `<div class="empty-state">Nessun prodotto in questa lista.</div>`}
    </div>
  `;

  box.querySelector("#history-recalc-btn")?.addEventListener("click", recalcSelectedHistory);
  box.querySelector("#history-delete-btn")?.addEventListener("click", deleteSelectedHistory);
  box.querySelector("#history-add-btn")?.addEventListener("click", addHistoryItem);

  box.querySelectorAll("[data-save-item]").forEach(btn => {
    btn.addEventListener("click", () => saveHistoryItem(Number(btn.dataset.saveItem)));
  });
  box.querySelectorAll("[data-delete-item]").forEach(btn => {
    btn.addEventListener("click", () => deleteHistoryItem(Number(btn.dataset.deleteItem)));
  });
}

function itemRow(item) {
  const type = item.price_type || "fixed";
  return `
    <div class="history-item-row" data-item-row="${item.id}">
      <img src="${item.image || "/static/images/placeholder.jpg"}" onerror="this.src='/static/images/placeholder.jpg'">

      <label>Prodotto
        <input data-field="name" value="${esc(item.name)}">
      </label>

      <label>Categoria
        <input data-field="category" value="${esc(item.category || "")}">
      </label>

      <label>Supermercato
        <input data-field="supermarket_name" value="${esc(item.supermarket_name || "")}">
      </label>

      <label>Q.tà
        <input data-field="quantity" type="number" min="1" value="${item.quantity || 1}">
      </label>

      <label>Prezzo unit.
        <input data-field="price_paid" type="number" min="0" step="0.01" value="${item.price_paid ?? 0}">
      </label>

      <label>Totale finale
        <input data-field="final_price_paid" type="number" min="0" step="0.01" value="${item.final_price_paid ?? ""}" placeholder="${euro(item.line_total)}">
      </label>

      <label>Tipo
        <select data-field="price_type">
          <option value="fixed" ${type === "fixed" ? "selected" : ""}>fisso</option>
          <option value="weight" ${type === "weight" ? "selected" : ""}>peso</option>
          <option value="manual" ${type === "manual" ? "selected" : ""}>manuale</option>
        </select>
      </label>

      <label>Peso
        <input data-field="weight_bought" type="number" min="0" step="0.001" value="${item.weight_bought ?? ""}">
      </label>

      <div class="history-item-actions">
        <strong>${euro(item.line_total)}</strong>
        <button type="button" class="edit-btn" data-save-item="${item.id}">Salva</button>
        <button type="button" class="delete-btn" data-delete-item="${item.id}">Elimina</button>
      </div>
    </div>
  `;
}

function getRowPayload(itemId) {
  const row = document.querySelector(`[data-item-row="${itemId}"]`);
  const payload = {};

  row.querySelectorAll("[data-field]").forEach(input => {
    const field = input.dataset.field;
    let value = input.value;

    if (["quantity"].includes(field)) value = Number(value || 1);
    else if (["price_paid", "final_price_paid", "weight_bought"].includes(field)) value = value === "" ? null : Number(value);
    else if (value === "") value = null;

    payload[field] = value;
  });

  return payload;
}

async function saveHistoryItem(itemId) {
  const payload = getRowPayload(itemId);
  const res = await api(`/admin/history/items/${itemId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
  if (!res.ok) return alert(`Errore salvataggio prodotto storico: ${await readError(res)}`);
  await selectHistory(state.selectedHistoryId);
  await refreshSelectedUser();
}

async function deleteHistoryItem(itemId) {
  if (!confirm("Eliminare questo prodotto dalla spesa passata?")) return;
  const res = await api(`/admin/history/items/${itemId}`, { method: "DELETE" });
  if (!res.ok) return alert(`Errore eliminazione: ${await readError(res)}`);
  await selectHistory(state.selectedHistoryId);
  await refreshSelectedUser();
}

async function addHistoryItem() {
  const productId = document.getElementById("history-add-product").value;
  const product = state.products.find(p => Number(p.id) === Number(productId));
  const name = document.getElementById("history-add-name").value.trim() || product?.name;
  const quantity = Number(document.getElementById("history-add-qty").value || 1);
  const price = Number(document.getElementById("history-add-price").value || product?.discounted_price || product?.original_price || 0);

  if (!name) return alert("Inserisci un prodotto o un nome manuale.");

  const payload = {
    product_id: product ? product.id : null,
    name,
    image: product?.image || null,
    unit: product?.unit || "pz",
    price_paid: price,
    quantity,
    category: product?.category || null,
    aisle_order: product?.aisle_order ?? null,
    supermarket_id: product?.supermarket_id || null,
    supermarket_name: product?.supermarket_name || null,
    price_type: product?.price_type || "fixed",
    price_unit: product?.price_unit || product?.unit || "pz",
  };

  const res = await api(`/admin/history/${state.selectedHistoryId}/items`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res.ok) return alert(`Errore aggiunta prodotto storico: ${await readError(res)}`);

  document.getElementById("history-add-name").value = "";
  document.getElementById("history-add-price").value = "";
  await selectHistory(state.selectedHistoryId);
  await refreshSelectedUser();
}

async function recalcSelectedHistory() {
  const res = await api(`/admin/history/${state.selectedHistoryId}/recalculate`, { method: "POST" });
  if (!res.ok) return alert(`Errore ricalcolo: ${await readError(res)}`);
  await refreshSelectedUser();
  await selectHistory(state.selectedHistoryId);
}

async function deleteSelectedHistory() {
  if (!confirm("Eliminare tutta questa lista dallo storico?")) return;
  const res = await api(`/admin/history/${state.selectedHistoryId}`, { method: "DELETE" });
  if (!res.ok) return alert(`Errore eliminazione lista: ${await readError(res)}`);
  state.selectedHistoryId = null;
  document.getElementById("admin-history-detail").innerHTML = `<div class="empty-state">Seleziona una lista.</div>`;
  await refreshSelectedUser();
}

async function refreshSelectedUser() {
  if (!state.selectedUserId) return;
  const userId = state.selectedUserId;
  await loadUsers();
  state.selectedUserId = userId;
  await selectUser(userId);
}

function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

document.addEventListener("DOMContentLoaded", async () => {
  injectAdminHistoryPanel();
  await loadBaseData();
});
