import CONFIG from "./config.js";
import { openProductModal } from "./modal-function.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

let allProducts = [];
let allSupermarkets = [];

const euro = (value) => Number(value || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
const hasDiscount = (p) => Number(p.discounted_price) > 0 && Number(p.discounted_price) < Number(p.original_price);
const finalPrice = (p) => hasDiscount(p) ? Number(p.discounted_price) : Number(p.original_price || 0);
const discountPercent = (p) => hasDiscount(p) ? Math.round((1 - Number(p.discounted_price) / Number(p.original_price)) * 100) : 0;
const smFor = (p) => allSupermarkets.find(s => s.id === p.supermarket_id) || { name: "Negozio", image: "" };

async function loadDashboard() {
  try {
    const [userRes, productsRes, recipesRes, supermarketsRes, statsRes] = await Promise.all([
      apiFetch(`${CONFIG.API_BASE_URL}/user`),
      apiFetch(`${CONFIG.API_BASE_URL}/product`),
      apiFetch(`${CONFIG.API_BASE_URL}/recipe?owner_id=1`),
      apiFetch(`${CONFIG.API_BASE_URL}/supermarket`),
      apiFetch(`${CONFIG.API_BASE_URL}/shopping-history/stats`).catch(() => null),
    ]);

    const user = userRes?.ok ? await userRes.json() : { first_name: "" };
    allProducts = productsRes?.ok ? await productsRes.json() : [];
    const recipes = recipesRes?.ok ? await recipesRes.json() : [];
    allSupermarkets = supermarketsRes?.ok ? await supermarketsRes.json() : [];
    const stats = statsRes?.ok ? await statsRes.json() : null;

    window.__allProducts = allProducts;
    window.__allSupermarkets = allSupermarkets;

    renderUser(user);
    renderHomeStats(stats);
    renderOffers();
    renderDashboardQuickActions();
    renderHistoryMini(stats);
    renderRecipe(recipes);
  } catch (err) {
    console.error(err);
  }
}

function renderUser(user) {
  const name = user.first_name || "";
  document.getElementById("user-greeting").textContent = name ? `Ciao, ${name} 👋` : "Ciao 👋";
  document.getElementById("user-avatar").textContent = name ? name[0].toUpperCase() : "S";
}

function renderHomeStats(stats) {
  const discounted = allProducts.filter(hasDiscount);
  document.getElementById("stat-products").textContent = allProducts.length;
  document.getElementById("stat-offers").textContent = discounted.length;
  document.getElementById("stat-spent").textContent = stats ? euro(stats.overview.total_spent) : "—";
  document.getElementById("stat-lists").textContent = stats ? stats.overview.trips_count : "—";

  const best = discounted.sort((a, b) => discountPercent(b) - discountPercent(a))[0];
  const hero = document.getElementById("hero-best-deal");
  if (best) hero.textContent = `${best.name}: ${euro(finalPrice(best))} · -${discountPercent(best)}%`;
  else hero.textContent = "Nessuna offerta attiva importata.";
}

function renderDashboardQuickActions() {
  const actions = [
    { id: "list", label: "Lista spesa", color: "green", icon: "M5 6h14M5 12h14M5 18h14" },
    { id: "products", label: "Prodotti", color: "blue", icon: "M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" },
    { id: "history", label: "Storico", color: "teal", icon: "M12 8v4l3 3M21 12a9 9 0 11-3.2-6.9M21 3v6h-6" },
    { id: "recipes", label: "Ricette", color: "orange", icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" },
    { id: "supermarkets", label: "Negozi", color: "purple", icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" },
    { id: "profile", label: "Profilo", color: "gray", icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" },
  ];

  const container = document.getElementById("quick-actions");
  container.innerHTML = actions.map(a => `
    <button class="action-btn" onclick="navigate('${a.id}')">
      <div class="action-icon ${a.color}">
        <svg class="icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${a.icon}" /></svg>
      </div>
      <span class="action-label">${a.label}</span>
    </button>
  `).join("");
}

function renderOffers() {
  const discounted = allProducts
    .filter(hasDiscount)
    .sort((a,b) => discountPercent(b) - discountPercent(a))
    .slice(0, 8);
  const container = document.getElementById("offers");
  if (!discounted.length) {
    container.innerHTML = `<div class="empty-mini">Nessuna offerta disponibile al momento.</div>`;
    return;
  }
  container.innerHTML = discounted.map(p => {
    const sm = smFor(p);
    return `
      <article class="offer-card" data-id="${p.id}">
        <div class="offer-img-wrapper">
          <img src="${p.image || "/static/images/placeholder.jpg"}" class="offer-img" onerror="this.src='/static/images/placeholder.jpg'">
          <span class="discount-badge">-${discountPercent(p)}%</span>
          ${p.flyer_page ? `<span class="flyer-badge">p.${p.flyer_page}</span>` : ""}
        </div>
        <div class="offer-content">
          <div class="offer-sm"><span class="offer-sm-icon">${sm.image ? `<img src="${sm.image}">` : "🏬"}</span>${sm.name}</div>
          <div class="offer-name">${p.name}</div>
          <div class="offer-price"><span class="new-price">${euro(p.discounted_price)}</span><span class="old-price">${euro(p.original_price)}</span></div>
        </div>
      </article>
    `;
  }).join("");
  container.querySelectorAll(".offer-card").forEach(card => {
    card.addEventListener("click", () => {
      const product = allProducts.find(p => p.id === Number(card.dataset.id));
      if (product) openProductModal(product, smFor(product));
    });
  });
}

function renderHistoryMini(stats) {
  const box = document.getElementById("history-mini");
  const latest = stats?.latest || [];
  if (!latest.length) {
    box.innerHTML = `<div class="empty-mini">Finalizza una spesa per vedere qui le ultime liste.</div>`;
    return;
  }
  box.innerHTML = latest.slice(0, 3).map(item => `
    <div class="history-mini-row" onclick="navigate('history')">
      <div><b>Spesa #${item.id}</b><span>${item.total_items} prodotti</span></div>
      <div class="history-mini-total">${euro(item.total_price)}</div>
    </div>
  `).join("");
}

function renderRecipe(recipes) {
  const section = document.getElementById("recipe-section");
  const card = document.getElementById("recipe-card");
  if (!recipes.length) {
    section.style.display = "block";
    card.innerHTML = `<div class="empty-mini">Nessuna ricetta ancora. Questa sezione resta pronta per il prossimo step.</div>`;
    return;
  }
  const r = recipes[0];
  card.innerHTML = `
    <img src="${r.image || ""}" onerror="this.style.display='none'">
    <div class="recipe-overlay">
      <h3>${r.name}</h3>
      <p>Idea veloce per trasformare la spesa in pasti concreti. Questa sezione la lasciamo attiva per il prossimo sviluppo ricette.</p>
    </div>
  `;
}

window.navigate = function navigate(tab) {
  if (tab === "home") window.location.href = "dashboard.html";
  if (tab === "products") window.location.href = "products.html";
  if (tab === "history") window.location.href = "history.html";
  if (tab === "recipes") window.location.href = "recipes.html";
  if (tab === "supermarkets") window.location.href = "supermarkets.html";
  if (tab === "profile") window.location.href = "profile.html";
  if (tab === "list") window.location.href = "shopping-list.html";
};

document.getElementById("see-all-offers")?.addEventListener("click", () => window.location.href = "products.html?sale=1");
document.getElementById("view-recipes")?.addEventListener("click", () => window.location.href = "recipes.html");

loadDashboard();
