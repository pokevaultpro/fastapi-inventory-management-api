import CONFIG from "./config.js";

const token = localStorage.getItem("token");
const euro = (v) => "€ " + Number(v || 0).toFixed(2).replace(".", ",");
const img = (src) => src || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Crect width='100%25' height='100%25' rx='18' fill='%23e2e8f0'/%3E%3Ctext x='50%25' y='53%25' text-anchor='middle' font-size='24' fill='%2394a3b8'%3E🛒%3C/text%3E%3C/svg%3E";
const fmtDate = (v) => {
  if (!v) return "Data sconosciuta";
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
};

async function api(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}), Authorization: `Bearer ${token}` }
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "index.html";
    return null;
  }
  return res;
}

function openAllListsModal() {
  document.getElementById("all-lists-modal").hidden = false;
  loadAllLists();
}

function closeAllListsModal() {
  document.getElementById("all-lists-modal").hidden = true;
}

async function loadAllLists() {
  const body = document.getElementById("all-lists-body");
  const search = document.getElementById("all-lists-search").value.trim().toLowerCase();
  body.innerHTML = `<div class="empty-state">Carico tutte le liste...</div>`;

  const res = await api(`${CONFIG.API_BASE_URL}/shopping-history?limit=200`);
  if (!res?.ok) {
    body.innerHTML = `<div class="empty-state">Non riesco a caricare lo storico completo.</div>`;
    return;
  }

  let rows = await res.json();
  if (search) {
    rows = rows.filter(h => String(h.id).includes(search) || fmtDate(h.created_at).toLowerCase().includes(search));
  }

  if (!rows.length) {
    body.innerHTML = `<div class="empty-state">Nessuna lista trovata.</div>`;
    return;
  }

  body.innerHTML = rows.map(h => `
    <article class="all-list-card" data-history="${h.id}">
      <div>
        <h3>Spesa #${h.id}</h3>
        <p>${fmtDate(h.created_at)} · ${h.total_items || 0} prodotti</p>
      </div>
      <strong>${euro(h.total_price)}</strong>
      <div class="all-list-actions">
        <button type="button" data-view="${h.id}">Vedi lista</button>
        <button type="button" data-restore="${h.id}">Ripristina</button>
      </div>
      <div class="all-list-details" id="all-details-${h.id}"></div>
    </article>
  `).join("");

  body.querySelectorAll("[data-view]").forEach(btn => btn.addEventListener("click", () => toggleFullList(Number(btn.dataset.view))));
  body.querySelectorAll("[data-restore]").forEach(btn => btn.addEventListener("click", () => restoreFullList(Number(btn.dataset.restore))));
}

async function toggleFullList(id) {
  const panel = document.getElementById(`all-details-${id}`);
  if (!panel) return;

  if (panel.classList.contains("open")) {
    panel.classList.remove("open");
    return;
  }

  if (!panel.dataset.loaded) {
    panel.innerHTML = `<div class="empty-state">Carico prodotti...</div>`;
    const res = await api(`${CONFIG.API_BASE_URL}/shopping-history/${id}/items`);
    const items = res?.ok ? await res.json() : [];
    panel.innerHTML = items.map(item => `
      <div class="all-detail-row">
        <img src="${img(item.image)}" alt="">
        <div>
          <b>${escapeHtml(item.name)}</b>
          <small>x${item.quantity || 1} · ${escapeHtml(item.category || "Categoria n/d")} · ${escapeHtml(item.supermarket_name || "N/D")}</small>
        </div>
        <strong>${euro((item.price_paid || 0) * (item.quantity || 1))}</strong>
      </div>
    `).join("") || `<div class="empty-state">Nessun prodotto salvato.</div>`;
    panel.dataset.loaded = "1";
  }

  panel.classList.add("open");
}

async function restoreFullList(id) {
  const clear = document.getElementById("clear-before-restore")?.checked || document.getElementById("all-clear-before-restore")?.checked || false;
  const res = await api(`${CONFIG.API_BASE_URL}/shopping-history/${id}/restore-cart?clear_existing=${clear}&merge_duplicates=true`, { method: "POST" });
  if (!res?.ok) {
    showMiniToast("Non sono riuscito a ripristinare la lista.");
    return;
  }
  const data = await res.json();
  const changes = data.price_changes?.length || 0;
  showMiniToast(`Lista #${id} ripristinata: ${data.restored_count} aggiunti, ${data.merged_count} aggiornati${changes ? `, ${changes} prezzi cambiati` : ""}.`);
}

function showMiniToast(message) {
  const toast = document.getElementById("restore-toast");
  if (!toast) return alert(message);
  toast.innerHTML = `<h3>Storico</h3><p>${escapeHtml(message)}</p><button onclick="this.closest('#restore-toast').hidden=true">Ok</button><button onclick="window.location.href='shopping-list.html'">Vai al carrello</button>`;
  toast.hidden = false;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
}

document.getElementById("open-all-lists")?.addEventListener("click", openAllListsModal);
document.getElementById("close-all-lists")?.addEventListener("click", closeAllListsModal);
document.getElementById("all-lists-search")?.addEventListener("input", loadAllLists);
document.getElementById("all-clear-before-restore")?.addEventListener("change", () => {});
document.getElementById("all-lists-modal")?.addEventListener("click", (e) => {
  if (e.target.id === "all-lists-modal") closeAllListsModal();
});
