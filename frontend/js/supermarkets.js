import CONFIG from "./config.js";
import { openProductModal } from "./modal-function.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

let supermarkets = [];
let products = [];
let selectedStore = null;

const pageList = document.getElementById("supermarkets-page");
const pageDetails = document.getElementById("supermarket-details");
const listContainer = document.getElementById("supermarket-list");
const headerContainer = document.getElementById("sm-header");
const productsGrid = document.getElementById("products-grid");
const backBtn = document.getElementById("back-btn");
const storeSearch = document.getElementById("store-search");
const storeSort = document.getElementById("store-sort");
const productSearch = document.getElementById("store-product-search");
const productSort = document.getElementById("store-product-sort");

const euro = (v) => Number(v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));

function image(src) {
  return src || "/static/images/placeholder.jpg";
}

function hasDiscount(p) {
  const original = Number(p.original_price || 0);
  const discounted = Number(p.discounted_price || 0);
  if (!(discounted > 0 && original > 0 && discounted < original)) return false;
  if (!p.flyer_valid_to) return true;
  const end = new Date(`${p.flyer_valid_to}T23:59:59`);
  return Number.isNaN(end.getTime()) || end >= new Date();
}

function priceType(p) {
  const value = String(p.price_type || "fixed").toLowerCase();
  return ["fixed", "weight", "manual"].includes(value) ? value : "fixed";
}

function priceUnit(p) {
  return p.price_unit || p.unit || (priceType(p) === "weight" ? "kg" : "pz");
}

function currentPrice(p) {
  return hasDiscount(p) ? Number(p.discounted_price || 0) : Number(p.original_price || 0);
}

function storeProducts(sm) {
  return products.filter(p => Number(p.supermarket_id) === Number(sm.id));
}

function storeStats(sm) {
  const rows = storeProducts(sm);
  const offers = rows.filter(hasDiscount).length;
  const categories = new Set(rows.map(p => p.category).filter(Boolean)).size;
  const cheapest = rows.length ? rows.reduce((best, p) => currentPrice(p) < currentPrice(best) ? p : best, rows[0]) : null;
  return { products: rows.length, offers, categories, cheapest };
}

async function loadSupermarkets() {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/supermarket`, {
    headers: { Authorization: "Bearer " + token }
  });
  return res.ok ? res.json() : [];
}

async function loadProducts() {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/product`, {
    headers: { Authorization: "Bearer " + token }
  });
  return res.ok ? res.json() : [];
}

async function init() {
  [supermarkets, products] = await Promise.all([loadSupermarkets(), loadProducts()]);
  document.getElementById("stores-count").textContent = supermarkets.length;
  showSupermarkets();
}

function filteredStores() {
  const q = storeSearch.value.trim().toLowerCase();
  let rows = supermarkets.filter(sm =>
    !q ||
    String(sm.name || "").toLowerCase().includes(q) ||
    String(sm.location || "").toLowerCase().includes(q)
  );

  const sort = storeSort.value;
  rows.sort((a, b) => {
    const sa = storeStats(a);
    const sb = storeStats(b);
    if (sort === "offers") return sb.offers - sa.offers || String(a.name).localeCompare(String(b.name), "it");
    if (sort === "products") return sb.products - sa.products || String(a.name).localeCompare(String(b.name), "it");
    return String(a.name).localeCompare(String(b.name), "it");
  });

  return rows;
}

function showSupermarkets() {
  pageDetails.classList.add("hidden");
  pageList.classList.remove("hidden");
  selectedStore = null;

  const rows = filteredStores();
  if (!rows.length) {
    listContainer.innerHTML = `<div class="empty-store-state">Nessun negozio trovato.</div>`;
    return;
  }

  listContainer.innerHTML = rows.map(sm => {
    const stats = storeStats(sm);
    return `
      <article class="store-card" data-store-id="${sm.id}">
        <div class="store-card-bg"></div>
        <div class="store-logo">
          <img src="${image(sm.image)}" onerror="this.src='/static/images/placeholder.jpg'">
        </div>
        <div class="store-card-body">
          <div>
            <h3>${esc(sm.name)}</h3>
            <p>${esc(sm.location || "Posizione non indicata")}</p>
          </div>
          <div class="store-stat-row">
            <span><b>${stats.products}</b> prodotti</span>
            <span><b>${stats.offers}</b> offerte</span>
            <span><b>${stats.categories}</b> categorie</span>
          </div>
          ${stats.cheapest ? `<small class="store-cheapest">Da ${euro(currentPrice(stats.cheapest))}: ${esc(stats.cheapest.name)}</small>` : ""}
        </div>
        <button class="store-open-btn">Apri</button>
      </article>
    `;
  }).join("");

  listContainer.querySelectorAll("[data-store-id]").forEach(card => {
    card.addEventListener("click", () => {
      const sm = supermarkets.find(s => Number(s.id) === Number(card.dataset.storeId));
      showDetails(sm);
    });
  });
}

function detailProducts(sm) {
  const q = productSearch.value.trim().toLowerCase();
  let rows = storeProducts(sm).filter(p =>
    !q ||
    String(p.name || "").toLowerCase().includes(q) ||
    String(p.category || "").toLowerCase().includes(q)
  );

  const sort = productSort.value;
  rows.sort((a, b) => {
    if (sort === "offers") return Number(hasDiscount(b)) - Number(hasDiscount(a)) || String(a.name).localeCompare(String(b.name), "it");
    if (sort === "name") return String(a.name).localeCompare(String(b.name), "it");
    if (sort === "price") return currentPrice(a) - currentPrice(b) || String(a.name).localeCompare(String(b.name), "it");
    return (Number(a.aisle_order) || 999999) - (Number(b.aisle_order) || 999999) || String(a.name).localeCompare(String(b.name), "it");
  });

  return rows;
}

function showDetails(sm) {
  selectedStore = sm;
  pageList.classList.add("hidden");
  pageDetails.classList.remove("hidden");

  const stats = storeStats(sm);
  headerContainer.innerHTML = `
    <div class="store-detail-logo"><img src="${image(sm.image)}" onerror="this.src='/static/images/placeholder.jpg'"></div>
    <div class="store-detail-copy">
      <p class="stores-kicker">Supermercato</p>
      <h1>${esc(sm.name)}</h1>
      <p>${esc(sm.location || "Posizione non indicata")}</p>
      <div class="store-detail-stats">
        <span><b>${stats.products}</b> prodotti</span>
        <span><b>${stats.offers}</b> offerte</span>
        <span><b>${stats.categories}</b> categorie</span>
      </div>
    </div>
  `;

  renderStoreProducts();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function renderStoreProducts() {
  const sm = selectedStore;
  if (!sm) return;

  const rows = detailProducts(sm);
  if (!rows.length) {
    productsGrid.innerHTML = `<div class="empty-store-state">Nessun prodotto trovato in questo negozio.</div>`;
    return;
  }

  productsGrid.innerHTML = rows.map(p => {
    const sale = hasDiscount(p);
    const type = priceType(p);
    const unit = priceUnit(p);
    return `
      <article class="store-product-card" data-id="${p.id}">
        <div class="store-product-img">
          ${sale ? `<span class="store-sale-badge">-${Math.round((1 - Number(p.discounted_price) / Number(p.original_price)) * 100)}%</span>` : ""}
          ${type === "weight" ? `<span class="store-variable-badge">al peso</span>` : ""}
          ${type === "manual" ? `<span class="store-variable-badge manual">manuale</span>` : ""}
          <img src="${image(p.image)}" onerror="this.src='/static/images/placeholder.jpg'">
        </div>
        <div class="store-product-body">
          <small>${esc(p.category || "Altro")}</small>
          <h4>${esc(p.name)}</h4>
          <p>${esc(p.location || "")}</p>
          <div class="store-product-bottom">
            <div class="store-price">
              ${sale ? `<span class="old">${euro(p.original_price)}</span><strong>${euro(p.discounted_price)}</strong>` : `<strong>${type === "manual" && !Number(p.original_price || 0) ? "Da inserire" : euro(p.original_price)}</strong>`}
              <em>${type === "manual" ? "in lista" : `/ ${esc(unit)}`}</em>
            </div>
            <span class="store-aisle">corsia ${p.aisle_order ?? "—"}</span>
          </div>
        </div>
      </article>
    `;
  }).join("");

  productsGrid.querySelectorAll(".store-product-card").forEach(card => {
    card.addEventListener("click", () => {
      const id = Number(card.dataset.id);
      const product = products.find(p => Number(p.id) === id);
      openProductModal(product, sm);
    });
  });
}

backBtn.addEventListener("click", showSupermarkets);
storeSearch.addEventListener("input", showSupermarkets);
storeSort.addEventListener("change", showSupermarkets);
productSearch.addEventListener("input", renderStoreProducts);
productSort.addEventListener("change", renderStoreProducts);

init();
