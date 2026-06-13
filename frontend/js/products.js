import CONFIG from "./config.js";
import { openProductModal } from "./modal-function.js";

const state = {
  products: [],
  supermarkets: [],
  favorites: [],
  category: "all",
  store: "all",
  mode: new URLSearchParams(window.location.search).get("sale") === "1" ? "sale" : "all",
  sort: "best-discount",
  visibleCount: window.innerWidth < 720 ? 24 : 60,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

const formatEuro = (value) => {
  const number = Number(value || 0);
  return number.toLocaleString("it-IT", { style: "currency", currency: "EUR" });
};

const formatDate = (value) => {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit" });
};


function parseFlyerSourceDates(source) {
  const text = String(source || "");
  const match = text.match(/(\d{4})[_-](\d{2})[_-](\d{2}).*?(\d{4})[_-](\d{2})[_-](\d{2})/);
  if (!match) return { from: null, to: null };
  return { from: `${match[1]}-${match[2]}-${match[3]}`, to: `${match[4]}-${match[5]}-${match[6]}` };
}

function flyerDates(product) {
  const parsed = parseFlyerSourceDates(product.flyer_source || product.offer_note || "");
  return {
    from: product.flyer_valid_from || parsed.from,
    to: product.flyer_valid_to || parsed.to,
  };
}

function isOfferActive(product) {
  const { to } = flyerDates(product);
  if (!to) return true;
  const end = new Date(`${to}T23:59:59`);
  if (Number.isNaN(end.getTime())) return true;
  return end >= new Date();
}

const hasDiscount = (p) => isOfferActive(p) && Number(p.discounted_price) > 0 && Number(p.discounted_price) < Number(p.original_price);
const finalPrice = (p) => hasDiscount(p) ? Number(p.discounted_price) : Number(p.original_price || 0);
const discountPercent = (p) => {
  if (p.discount_percent) return Math.round(Number(p.discount_percent));
  if (!hasDiscount(p)) return 0;
  return Math.round((1 - Number(p.discounted_price) / Number(p.original_price)) * 100);
};

const getSupermarket = (p) => state.supermarkets.find((s) => s.id === p.supermarket_id) || null;
const getSupermarketName = (p) => getSupermarket(p)?.name || "Negozio";

const imageSrc = (p) => {
  if (!p.image) return "/static/images/placeholder.jpg";
  return p.image;
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function debounce(fn, delay = 150) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

document.addEventListener("DOMContentLoaded", async () => {
  paintSkeletons();
  await Promise.all([loadProducts(), loadFavorites()]);
  populateStoreFilter();
  populateCategoryBar();
  bindEvents();
  setMode(state.mode);
  render();
});

async function loadProducts() {
  const [prodRes, supRes] = await Promise.all([
    apiFetch(`${CONFIG.API_BASE_URL}/product`),
    apiFetch(`${CONFIG.API_BASE_URL}/supermarket`),
  ]);

  state.products = prodRes?.ok ? await prodRes.json() : [];
  state.supermarkets = supRes?.ok ? await supRes.json() : [];
}

async function loadFavorites() {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/favorite`);
  state.favorites = res?.ok ? await res.json() : [];
}

function bindEvents() {
  $("#search-input")?.addEventListener("input", debounce(() => {
    state.visibleCount = window.innerWidth < 720 ? 24 : 60;
    render();
  }));

  $("#store-filter")?.addEventListener("change", (event) => {
    state.store = event.target.value;
    state.visibleCount = window.innerWidth < 720 ? 24 : 60;
    render();
  });

  $("#sort-select")?.addEventListener("change", (event) => {
    state.sort = event.target.value;
    render();
  });

  $("#category-bar")?.addEventListener("click", (event) => {
    const button = event.target.closest(".cat-pill");
    if (!button) return;
    state.category = button.dataset.cat;
    state.visibleCount = window.innerWidth < 720 ? 24 : 60;
    updateActiveCategory();
    render();
  });

  $$(".quick-filter").forEach((button) => {
    button.addEventListener("click", () => setMode(button.dataset.mode));
  });

  $("#load-more-btn")?.addEventListener("click", () => {
    state.visibleCount += window.innerWidth < 720 ? 24 : 60;
    render();
  });

  window.addEventListener("resize", debounce(() => render(), 200));
}

function setMode(mode) {
  state.mode = mode || "all";
  $$(".quick-filter").forEach((btn) => btn.classList.toggle("active", btn.dataset.mode === state.mode));
  render();
}

function populateStoreFilter() {
  const select = $("#store-filter");
  if (!select) return;
  select.innerHTML = `<option value="all">Tutti i negozi</option>`;
  state.supermarkets
    .slice()
    .sort((a, b) => a.name.localeCompare(b.name, "it"))
    .forEach((s) => {
      const option = document.createElement("option");
      option.value = s.id;
      option.textContent = s.name;
      select.appendChild(option);
    });
}

function populateCategoryBar() {
  const bar = $("#category-bar");
  if (!bar) return;
  const categories = Array.from(new Set(state.products.map((p) => p.category).filter(Boolean)))
    .sort((a, b) => a.localeCompare(b, "it"));

  bar.innerHTML = `<button class="cat-pill active" data-cat="all">Tutte le categorie</button>`;
  categories.forEach((category) => {
    const button = document.createElement("button");
    button.className = "cat-pill";
    button.dataset.cat = category;
    button.textContent = category;
    bar.appendChild(button);
  });
}

function updateActiveCategory() {
  $$(".cat-pill").forEach((btn) => btn.classList.toggle("active", btn.dataset.cat === state.category));
}

function getFilteredProducts() {
  const search = ($("#search-input")?.value || "").trim().toLowerCase();

  let result = state.products.filter((p) => {
    const name = String(p.name || "").toLowerCase();
    const category = String(p.category || "").toLowerCase();
    const store = getSupermarketName(p).toLowerCase();
    const matchesSearch = !search || name.includes(search) || category.includes(search) || store.includes(search);
    const matchesCategory = state.category === "all" || p.category === state.category;
    const matchesStore = state.store === "all" || String(p.supermarket_id) === String(state.store);
    const matchesMode =
      state.mode === "all" ||
      (state.mode === "sale" && hasDiscount(p)) ||
      (state.mode === "lidl-plus" && hasDiscount(p) && Boolean(p.is_lidl_plus)) ||
      (state.mode === "favorites" && state.favorites.includes(p.id));

    return matchesSearch && matchesCategory && matchesStore && matchesMode;
  });

  result.sort((a, b) => {
    switch (state.sort) {
      case "price-asc": return finalPrice(a) - finalPrice(b);
      case "price-desc": return finalPrice(b) - finalPrice(a);
      case "name-asc": return String(a.name).localeCompare(String(b.name), "it");
      case "category": return String(a.category || "").localeCompare(String(b.category || ""), "it") || String(a.name).localeCompare(String(b.name), "it");
      case "flyer-page": return ((hasDiscount(a) && a.flyer_page) ? Number(a.flyer_page) : 9999) - ((hasDiscount(b) && b.flyer_page) ? Number(b.flyer_page) : 9999) || String(a.name).localeCompare(String(b.name), "it");
      case "best-discount":
      default:
        return discountPercent(b) - discountPercent(a) || finalPrice(a) - finalPrice(b);
    }
  });

  return result;
}

function render() {
  const filtered = getFilteredProducts();
  renderStats();
  renderBestDeal();
  renderHeader(filtered);
  renderGrid(filtered);
}

function renderStats() {
  $("#stat-total").textContent = state.products.length;
  $("#stat-sale").textContent = state.products.filter(hasDiscount).length;
  $("#stat-stores").textContent = state.supermarkets.length;
}

function renderBestDeal() {
  const box = $("#best-deal-box");
  if (!box) return;

  const best = state.products.filter(hasDiscount).sort((a, b) => discountPercent(b) - discountPercent(a))[0];
  if (!best) {
    box.textContent = "Nessuna offerta importata.";
    return;
  }

  box.innerHTML = `
    <div class="best-deal-name">${escapeHtml(best.name)}</div>
    <div class="best-deal-price">${formatEuro(finalPrice(best))}</div>
    <div class="best-deal-meta">-${discountPercent(best)}% · ${best.flyer_page ? `pagina volantino ${best.flyer_page}` : getSupermarketName(best)}</div>
  `;
}

function renderHeader(filtered) {
  $("#result-count").textContent = filtered.length;

  const modeLabel = {
    all: "Tutto il catalogo",
    sale: "Solo prodotti in offerta",
    "lidl-plus": "Solo offerte Lidl Plus",
    favorites: "Solo preferiti",
  }[state.mode] || "Tutto il catalogo";

  const categoryLabel = state.category === "all" ? "" : ` · ${state.category}`;
  $("#active-filter-label").textContent = `${modeLabel}${categoryLabel}`;
}

function renderGrid(filtered) {
  const grid = $("#products-grid");
  const empty = $("#empty-state");
  const loadMore = $("#load-more-btn");
  if (!grid) return;

  grid.innerHTML = "";

  if (!filtered.length) {
    empty?.classList.remove("hidden");
    loadMore?.classList.add("hidden");
    return;
  }

  empty?.classList.add("hidden");

  const visible = filtered.slice(0, state.visibleCount);
  const fragment = document.createDocumentFragment();
  visible.forEach((product) => fragment.appendChild(createProductCard(product)));
  grid.appendChild(fragment);

  if (filtered.length > state.visibleCount) {
    loadMore?.classList.remove("hidden");
    loadMore.textContent = `Mostra altri ${Math.min(60, filtered.length - state.visibleCount)} prodotti`;
  } else {
    loadMore?.classList.add("hidden");
  }
}

function createProductCard(p) {
  const supermarket = getSupermarket(p);
  const sale = hasDiscount(p);
  const favorite = state.favorites.includes(p.id);
  const page = sale && p.flyer_page ? Number(p.flyer_page) : null;
  const dates = sale ? flyerDates(p) : { from: null, to: null };
  const validTo = sale ? formatDate(dates.to) : "";

  const card = document.createElement("article");
  card.className = "product-card";
  card.innerHTML = `
    <div class="card-image-shell">
      ${sale ? `<div class="discount-badge">-${discountPercent(p)}%</div>` : ""}
      ${page ? `<div class="flyer-page-badge">📄 Volantino p.${page}</div>` : ""}
      ${!isOfferActive(p) && p.discounted_price ? `<div class="expired-badge">offerta scaduta</div>` : ""}
      <button class="fav-icon ${favorite ? "active" : ""}" type="button" aria-label="Preferito">
        <svg viewBox="0 0 24 24" class="heart-svg"><path d="M12 21s-6-4.35-9-8.7C-1.5 7.5 1.5 3 6 3c2.25 0 4.5 1.5 6 3.75C13.5 4.5 15.75 3 18 3c4.5 0 7.5 4.5 3 9.3C18 16.65 12 21 12 21z"/></svg>
      </button>
      <img loading="lazy" src="${escapeHtml(imageSrc(p))}" class="product-img" alt="${escapeHtml(p.name)}" onerror="this.src='/static/images/placeholder.jpg'">
    </div>

    <div class="product-body">
      <div class="product-topline">
        <span class="store-chip">${escapeHtml(getSupermarketName(p))}</span>
        ${sale && p.is_lidl_plus ? `<span class="lidl-plus-chip">Lidl Plus</span>` : `<span class="category-chip">${escapeHtml(p.category || "Altro")}</span>`}
      </div>

      <div class="product-name">${escapeHtml(p.name)}</div>
      <div class="product-unit">${escapeHtml(p.unit || "pz")}</div>

      <div class="price-line">
        ${sale ? `<span class="old-price">${formatEuro(p.original_price)}</span><span class="new-price">${formatEuro(p.discounted_price)}</span>` : `<span class="regular-price">${formatEuro(p.original_price)}</span>`}
        <span class="unit-price">/ ${escapeHtml(p.unit || "pz")}</span>
      </div>

      <div class="card-footer">
        <div class="offer-context">
          ${sale && validTo ? `<span class="context-pill strong">offerta fino al ${validTo}</span>` : ""}
          ${sale && p.offer_note ? `<span class="context-pill">${escapeHtml(p.offer_note)}</span>` : ""}
          ${sale && page && !validTo ? `<span class="context-pill strong">Volantino p.${page}</span>` : ""}
        </div>
        <button class="add-btn" type="button" aria-label="Aggiungi alla lista">+</button>
      </div>
    </div>
  `;

  card.querySelector(".fav-icon").addEventListener("click", (event) => {
    event.stopPropagation();
    toggleFavorite(p.id);
  });

  card.querySelector(".add-btn").addEventListener("click", (event) => {
    event.stopPropagation();
    addToCart(p.id);
  });

  card.addEventListener("click", () => openProductModal(p, supermarket || { name: getSupermarketName(p) }));
  return card;
}

async function toggleFavorite(id) {
  const isFavorite = state.favorites.includes(id);
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/favorite${isFavorite ? `/${id}` : ""}`, {
    method: isFavorite ? "DELETE" : "POST",
    body: isFavorite ? undefined : JSON.stringify({ product_id: id }),
  });

  if (!res?.ok && res?.status !== 204) {
    showToast("Non riesco ad aggiornare i preferiti", false);
    return;
  }

  state.favorites = isFavorite ? state.favorites.filter((item) => item !== id) : [...state.favorites, id];
  render();
}

async function addToCart(productId) {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/cart`, {
    method: "POST",
    body: JSON.stringify({ product_id: productId, quantity: 1 }),
  });

  if (!res?.ok) {
    const err = await res?.json().catch(() => ({}));
    showToast(err?.detail || "Errore durante l'aggiunta", false);
    return;
  }

  showToast("Aggiunto alla lista spesa");
}

function showToast(message, success = true) {
  const toast = $("#toast");
  if (!toast) return;
  toast.textContent = message;
  toast.style.background = success ? "#16a34a" : "#dc2626";
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2200);
}

function paintSkeletons() {
  const grid = $("#products-grid");
  if (!grid) return;
  grid.innerHTML = Array.from({ length: 12 }).map(() => `
    <article class="product-card skeleton-card">
      <div class="card-image-shell"></div>
      <div class="product-body">
        <div class="product-name">Caricamento...</div>
        <div class="product-unit">—</div>
      </div>
    </article>
  `).join("");
}
