
import CONFIG from "./config.js";

const historyProductsState = {
  data: null,
  query: "",
};

const hpToken = localStorage.getItem("token");

function hpEuro(value) {
  return Number(value || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
}

function hpDate(value) {
  if (!value) return "Mai";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric" });
}

function hpImg(src) {
  return src || "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='90' height='90'%3E%3Crect width='100%25' height='100%25' rx='18' fill='%23e2e8f0'/%3E%3Ctext x='50%25' y='54%25' text-anchor='middle' font-size='24' fill='%2394a3b8'%3E🛒%3C/text%3E%3C/svg%3E";
}

function hpEscape(value) {
  return String(value ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
}

async function hpApi(url) {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${hpToken}` },
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "index.html";
    return null;
  }
  return res;
}

function ensureHistoryProductsSection() {
  if (document.getElementById("history-products-section")) return;

  const main = document.querySelector(".history-page") || document.querySelector("main") || document.body;
  const section = document.createElement("section");
  section.id = "history-products-section";
  section.className = "analytics-card full-width purchased-products-card";
  section.innerHTML = `
    <div class="card-header purchased-head">
      <div>
        <p class="card-kicker">Prodotti acquistati</p>
        <h2>Tutti i prodotti comprati</h2>
        <p class="section-subcopy">A schermo vedi i più ricorrenti. Con “Vedi tutti” apri l’archivio completo.</p>
      </div>
      <div class="purchased-actions">
        <button type="button" class="all-lists-btn" id="open-all-products">Vedi tutti</button>
      </div>
    </div>

    <div class="extra-stats-grid" id="extra-history-stats"></div>
    <div id="purchased-products-preview" class="purchased-products-grid"></div>
  `;
  main.appendChild(section);

  const modal = document.createElement("section");
  modal.id = "all-products-modal";
  modal.className = "all-lists-modal";
  modal.hidden = true;
  modal.innerHTML = `
    <div class="all-lists-panel all-products-panel">
      <div class="all-lists-head">
        <div>
          <p class="card-kicker">Archivio prodotti</p>
          <h2>Tutti i prodotti acquistati</h2>
          <p>Ricerca tra tutti i prodotti che hai comprato nella storia dell’app o nel periodo selezionato.</p>
        </div>
        <button type="button" id="close-all-products" class="modal-close-btn">×</button>
      </div>
      <div class="all-lists-tools">
        <input id="all-products-search" placeholder="Cerca prodotto, categoria o supermercato...">
      </div>
      <div id="all-products-body" class="all-products-body"></div>
    </div>
  `;
  document.body.appendChild(modal);

  document.getElementById("open-all-products")?.addEventListener("click", () => {
    modal.hidden = false;
    renderAllPurchasedProducts();
  });
  document.getElementById("close-all-products")?.addEventListener("click", () => modal.hidden = true);
  document.getElementById("all-products-search")?.addEventListener("input", (event) => {
    historyProductsState.query = event.target.value.trim().toLowerCase();
    renderAllPurchasedProducts();
  });
  modal.addEventListener("click", (event) => {
    if (event.target.id === "all-products-modal") modal.hidden = true;
  });
}

async function loadPurchasedProducts() {
  ensureHistoryProductsSection();

  const range = document.getElementById("range-select")?.value || "all";
  const qs = range === "all" ? "" : `?days=${encodeURIComponent(range)}`;
  const res = await hpApi(`${CONFIG.API_BASE_URL}/shopping-history/products${qs}`);
  if (!res?.ok) {
    document.getElementById("purchased-products-preview").innerHTML = `<div class="empty-state">Non riesco a caricare i prodotti acquistati.</div>`;
    return;
  }

  historyProductsState.data = await res.json();
  renderExtraStats();
  renderPurchasedPreview();
}

function renderExtraStats() {
  const box = document.getElementById("extra-history-stats");
  const o = historyProductsState.data?.overview || {};

  const cards = [
    { label: "Prodotti unici", value: o.unique_products || 0, sub: "prodotti diversi acquistati", icon: "🧾" },
    { label: "Più comprato", value: o.favorite_product?.name || "—", sub: `${o.favorite_product?.quantity || 0} pezzi`, icon: "⭐" },
    { label: "Categoria preferita", value: o.favorite_category?.name || "—", sub: hpEuro(o.favorite_category?.total || 0), icon: "🏷️" },
    { label: "Acquisti scontati", value: `${o.discounted_share || 0}%`, sub: `${o.discounted_quantity || 0} pezzi in offerta`, icon: "🔥" },
    { label: "Supermercato principale", value: o.favorite_supermarket?.name || "—", sub: hpEuro(o.favorite_supermarket?.total || 0), icon: "🏪" },
  ];

  box.innerHTML = cards.map(c => `
    <article class="mini-stat-card">
      <span>${c.icon}</span>
      <div>
        <small>${hpEscape(c.label)}</small>
        <strong>${hpEscape(c.value)}</strong>
        <p>${hpEscape(c.sub)}</p>
      </div>
    </article>
  `).join("");
}

function renderPurchasedPreview() {
  const box = document.getElementById("purchased-products-preview");
  const products = historyProductsState.data?.products || [];
  if (!products.length) {
    box.innerHTML = `<div class="empty-state">Nessun prodotto acquistato ancora.</div>`;
    return;
  }

  box.innerHTML = products.slice(0, 12).map(productCard).join("");
}

function productCard(p) {
  return `
    <article class="purchased-product-card">
      <img src="${hpImg(p.image)}" onerror="this.src='${hpImg(null)}'">
      <div>
        <b>${hpEscape(p.name)}</b>
        <small>${hpEscape(p.category || "Categoria n/d")} · ${hpEscape(p.supermarket_name || "N/D")}</small>
        <div class="purchased-product-meta">
          <span>${p.quantity || 0} pz</span>
          <span>${hpEuro(p.total)}</span>
          <span>ultimo: ${hpDate(p.last_bought_at)}</span>
        </div>
      </div>
    </article>
  `;
}

function renderAllPurchasedProducts() {
  const body = document.getElementById("all-products-body");
  const all = historyProductsState.data?.products || [];
  const q = historyProductsState.query || "";

  const rows = q
    ? all.filter(p =>
        String(p.name || "").toLowerCase().includes(q) ||
        String(p.category || "").toLowerCase().includes(q) ||
        String(p.supermarket_name || "").toLowerCase().includes(q)
      )
    : all;

  if (!rows.length) {
    body.innerHTML = `<div class="empty-state">Nessun prodotto trovato.</div>`;
    return;
  }

  body.innerHTML = rows.map(p => `
    <div class="all-product-row">
      <img src="${hpImg(p.image)}" onerror="this.src='${hpImg(null)}'">
      <div>
        <b>${hpEscape(p.name)}</b>
        <small>${hpEscape(p.category || "Categoria n/d")} · ${hpEscape(p.supermarket_name || "N/D")} · ${hpEscape(p.unit || "pz")}</small>
      </div>
      <div><strong>${p.quantity || 0}</strong><small>quantità</small></div>
      <div><strong>${p.lines || 0}</strong><small>acquisti</small></div>
      <div><strong>${hpEuro(p.total)}</strong><small>totale</small></div>
      <div><strong>${hpEuro(p.average_unit_price)}</strong><small>medio</small></div>
      <div><strong>${hpDate(p.last_bought_at)}</strong><small>ultimo</small></div>
    </div>
  `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
  ensureHistoryProductsSection();
  loadPurchasedProducts();
  document.getElementById("range-select")?.addEventListener("change", () => setTimeout(loadPurchasedProducts, 50));
  document.getElementById("refresh-btn")?.addEventListener("click", () => setTimeout(loadPurchasedProducts, 50));
});
