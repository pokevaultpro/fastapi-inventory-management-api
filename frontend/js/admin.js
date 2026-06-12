import CONFIG from "./config.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

const state = { supermarkets: [], products: [], users: [], recipes: [], activeTab: "products" };

async function api(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
      Authorization: `Bearer ${localStorage.getItem("token")}`
    }
  });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "index.html";
    return null;
  }
  if (res.status === 403) {
    document.querySelector(".admin-desktop").innerHTML = `<section class="admin-hero"><div><p class="eyebrow">Accesso negato</p><h1>Solo admin</h1><p>Questa pagina è disponibile solo per utenti con ruolo admin.</p></div></section>`;
    return null;
  }
  return res;
}

const euro = v => Number(v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
const img = src => src || "/static/images/placeholder.jpg";

function toast(msg) {
  const el = document.getElementById("admin-toast");
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2400);
}

async function init() {
  bindTabs();
  bindForms();
  await loadAll();
}

function bindTabs() {
  document.querySelectorAll(".admin-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      state.activeTab = btn.dataset.adminTab;
      document.querySelectorAll(".admin-tab").forEach(x => x.classList.toggle("active", x === btn));
      document.querySelectorAll(".admin-panel").forEach(p => p.classList.toggle("active", p.id === `panel-${state.activeTab}`));
    });
  });
}

function bindForms() {
  document.getElementById("product-form").addEventListener("submit", saveProduct);
  document.getElementById("product-reset-btn").addEventListener("click", resetProductForm);
  document.getElementById("product-admin-search").addEventListener("input", debounce(loadProducts, 250));

  document.getElementById("supermarket-form").addEventListener("submit", saveSupermarket);
  document.getElementById("supermarket-reset-btn").addEventListener("click", resetSupermarketForm);

  document.getElementById("user-admin-search").addEventListener("input", debounce(loadUsers, 250));

  document.getElementById("admin-recipe-form").addEventListener("submit", saveRecipe);
  document.getElementById("admin-recipe-reset-btn").addEventListener("click", resetRecipeForm);
  document.getElementById("recipe-admin-search").addEventListener("input", debounce(loadRecipes, 250));
}

async function loadAll() {
  const summary = await api(`${CONFIG.API_BASE_URL}/admin/summary`);
  if (!summary?.ok) return;
  renderSummary(await summary.json());
  await loadSupermarkets();
  await Promise.all([loadProducts(), loadUsers(), loadRecipes()]);
}

function renderSummary(s) {
  document.getElementById("admin-summary").innerHTML = [
    ["Prodotti", s.products],
    ["Supermercati", s.supermarkets],
    ["Utenti", s.users],
    ["Ricette", s.recipes],
  ].map(([k,v]) => `<article class="summary-card"><small>${k}</small><strong>${v}</strong></article>`).join("");
}

async function loadSupermarkets() {
  const res = await api(`${CONFIG.API_BASE_URL}/admin/supermarkets`);
  if (!res?.ok) return;
  state.supermarkets = await res.json();
  renderSupermarketSelect();
  renderSupermarkets();
}

function renderSupermarketSelect() {
  const select = document.getElementById("product-supermarket");
  select.innerHTML = state.supermarkets.map(s => `<option value="${s.id}">${escapeHtml(s.name)}</option>`).join("");
}

async function loadProducts() {
  const q = document.getElementById("product-admin-search")?.value.trim() || "";
  const res = await api(`${CONFIG.API_BASE_URL}/admin/products?limit=120${q ? `&search=${encodeURIComponent(q)}` : ""}`);
  if (!res?.ok) return;
  state.products = await res.json();
  renderProducts();
}

function renderProducts() {
  document.getElementById("products-table").innerHTML = state.products.map(p => `
    <div class="admin-row">
      <img src="${img(p.image)}" onerror="this.src='/static/images/placeholder.jpg'">
      <div><b>${escapeHtml(p.name)}</b><small>${escapeHtml(p.brand || p.category || "")}</small></div>
      <div>${escapeHtml(p.supermarket_name || "")}<small>${escapeHtml(p.unit || "pz")}</small></div>
      <div><b>${euro(p.discounted_price || p.original_price)}</b><small>${p.discounted_price ? `orig. ${euro(p.original_price)}` : ""}</small></div>
      <div>${p.flyer_page ? `Volantino p.${p.flyer_page}` : ""}</div>
      <div class="row-actions"><button class="edit-btn" data-edit-product="${p.id}">Edit</button><button class="delete-btn" data-delete-product="${p.id}">Del</button></div>
    </div>
  `).join("") || `<div class="empty-state">Nessun prodotto.</div>`;

  document.querySelectorAll("[data-edit-product]").forEach(btn => btn.addEventListener("click", () => editProduct(Number(btn.dataset.editProduct))));
  document.querySelectorAll("[data-delete-product]").forEach(btn => btn.addEventListener("click", () => deleteProduct(Number(btn.dataset.deleteProduct))));
}

function editProduct(id) {
  const p = state.products.find(x => x.id === id);
  if (!p) return;
  document.getElementById("product-id").value = p.id;
  document.getElementById("product-name").value = p.name || "";
  document.getElementById("product-category").value = p.category || "Altro";
  document.getElementById("product-brand").value = p.brand || "";
  document.getElementById("product-unit").value = p.unit || "pz";
  document.getElementById("product-original").value = p.original_price || "";
  document.getElementById("product-discounted").value = p.discounted_price || "";
  document.getElementById("product-supermarket").value = p.supermarket_id || "";
  document.getElementById("product-image").value = p.image || "";
  document.getElementById("product-flyer-page").value = p.flyer_page || "";
  document.getElementById("product-save-btn").textContent = "Aggiorna prodotto";
  window.scrollTo({ top: document.getElementById("panel-products").offsetTop - 80, behavior: "smooth" });
}

function resetProductForm() {
  document.getElementById("product-form").reset();
  document.getElementById("product-id").value = "";
  document.getElementById("product-category").value = "Altro";
  document.getElementById("product-unit").value = "pz";
  document.getElementById("product-save-btn").textContent = "Salva prodotto";
}

async function saveProduct(e) {
  e.preventDefault();
  const id = document.getElementById("product-id").value;
  const payload = {
    name: document.getElementById("product-name").value.trim(),
    category: document.getElementById("product-category").value.trim() || "Altro",
    brand: document.getElementById("product-brand").value.trim() || null,
    unit: document.getElementById("product-unit").value.trim() || "pz",
    original_price: Number(document.getElementById("product-original").value),
    discounted_price: document.getElementById("product-discounted").value ? Number(document.getElementById("product-discounted").value) : null,
    supermarket_id: Number(document.getElementById("product-supermarket").value),
    aisle_order: 999,
    image: document.getElementById("product-image").value.trim() || null,
    flyer_page: document.getElementById("product-flyer-page").value ? Number(document.getElementById("product-flyer-page").value) : null,
  };
  const url = id ? `${CONFIG.API_BASE_URL}/admin/products/${id}` : `${CONFIG.API_BASE_URL}/admin/products`;
  const method = id ? "PUT" : "POST";
  const res = await api(url, { method, body: JSON.stringify(payload) });
  if (!res?.ok) return toast("Errore salvataggio prodotto");
  toast(id ? "Prodotto aggiornato" : "Prodotto creato");
  resetProductForm();
  await loadProducts();
}

async function deleteProduct(id) {
  if (!confirm("Eliminare prodotto dal database? Verrà rimosso anche da carrelli/ricette.")) return;
  const res = await api(`${CONFIG.API_BASE_URL}/admin/products/${id}`, { method: "DELETE" });
  if (!res?.ok) return toast("Errore eliminazione prodotto");
  toast("Prodotto eliminato");
  await loadProducts();
}

function renderSupermarkets() {
  document.getElementById("supermarkets-table").innerHTML = state.supermarkets.map(s => `
    <div class="admin-row supermarket-row">
      <img src="${img(s.image)}" onerror="this.src='/static/images/placeholder.jpg'">
      <div><b>${escapeHtml(s.name)}</b><small>ID ${s.id}</small></div>
      <div>${escapeHtml(s.location || "")}</div>
      <div>${s.products_count || 0} prodotti</div>
      <div class="row-actions"><button class="edit-btn" data-edit-supermarket="${s.id}">Edit</button><button class="delete-btn" data-delete-supermarket="${s.id}">Del</button></div>
    </div>
  `).join("");

  document.querySelectorAll("[data-edit-supermarket]").forEach(btn => btn.addEventListener("click", () => editSupermarket(Number(btn.dataset.editSupermarket))));
  document.querySelectorAll("[data-delete-supermarket]").forEach(btn => btn.addEventListener("click", () => deleteSupermarket(Number(btn.dataset.deleteSupermarket))));
}

function editSupermarket(id) {
  const s = state.supermarkets.find(x => x.id === id);
  if (!s) return;
  document.getElementById("supermarket-id").value = s.id;
  document.getElementById("supermarket-name").value = s.name || "";
  document.getElementById("supermarket-location").value = s.location || "";
  document.getElementById("supermarket-image").value = s.image || "";
}

function resetSupermarketForm() {
  document.getElementById("supermarket-form").reset();
  document.getElementById("supermarket-id").value = "";
}

async function saveSupermarket(e) {
  e.preventDefault();
  const id = document.getElementById("supermarket-id").value;
  const payload = {
    name: document.getElementById("supermarket-name").value.trim(),
    location: document.getElementById("supermarket-location").value.trim() || null,
    image: document.getElementById("supermarket-image").value.trim() || null,
  };
  const res = await api(id ? `${CONFIG.API_BASE_URL}/admin/supermarkets/${id}` : `${CONFIG.API_BASE_URL}/admin/supermarkets`, { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
  if (!res?.ok) return toast("Errore salvataggio supermercato");
  toast(id ? "Supermercato aggiornato" : "Supermercato creato");
  resetSupermarketForm();
  await loadSupermarkets();
  await loadProducts();
}

async function deleteSupermarket(id) {
  const force = confirm("Vuoi eliminare anche tutti i prodotti collegati a questo supermercato? OK = sì, Annulla = prova eliminazione sicura.");
  const res = await api(`${CONFIG.API_BASE_URL}/admin/supermarkets/${id}?force=${force}`, { method: "DELETE" });
  if (!res?.ok) return toast("Errore eliminazione supermercato");
  toast("Supermercato eliminato");
  await loadSupermarkets();
}

async function loadUsers() {
  const q = document.getElementById("user-admin-search")?.value.trim() || "";
  const res = await api(`${CONFIG.API_BASE_URL}/admin/users?limit=200${q ? `&search=${encodeURIComponent(q)}` : ""}`);
  if (!res?.ok) return;
  state.users = await res.json();
  renderUsers();
}

function renderUsers() {
  document.getElementById("users-table").innerHTML = state.users.map(u => `
    <div class="admin-row user-row">
      <div><b>#${u.id}</b></div>
      <div><b>${escapeHtml(u.username || "")}</b><small>${escapeHtml(u.email || "")}</small></div>
      <div>${escapeHtml([u.first_name, u.last_name].filter(Boolean).join(" "))}</div>
      <select class="role-select" data-user-role="${u.id}"><option value="user" ${u.role === "user" ? "selected" : ""}>user</option><option value="admin" ${u.role === "admin" ? "selected" : ""}>admin</option></select>
      <select class="active-select" data-user-active="${u.id}"><option value="true" ${u.is_active ? "selected" : ""}>attivo</option><option value="false" ${!u.is_active ? "selected" : ""}>disattivo</option></select>
      <div class="row-actions"><button class="edit-btn" data-save-user="${u.id}">Salva</button></div>
    </div>
  `).join("");
  document.querySelectorAll("[data-save-user]").forEach(btn => btn.addEventListener("click", () => saveUser(Number(btn.dataset.saveUser))));
}

async function saveUser(id) {
  const role = document.querySelector(`[data-user-role="${id}"]`).value;
  const is_active = document.querySelector(`[data-user-active="${id}"]`).value === "true";
  const res = await api(`${CONFIG.API_BASE_URL}/admin/users/${id}`, { method: "PUT", body: JSON.stringify({ role, is_active }) });
  if (!res?.ok) return toast("Errore salvataggio utente");
  toast("Utente aggiornato");
  await loadUsers();
}

async function loadRecipes() {
  const q = document.getElementById("recipe-admin-search")?.value.trim() || "";
  const res = await api(`${CONFIG.API_BASE_URL}/admin/recipes?limit=200${q ? `&search=${encodeURIComponent(q)}` : ""}`);
  if (!res?.ok) return;
  state.recipes = await res.json();
  renderRecipes();
}

function renderRecipes() {
  document.getElementById("recipes-table").innerHTML = state.recipes.map(r => `
    <div class="admin-row recipe-row">
      <img src="${img(r.image)}" onerror="this.src='/static/images/placeholder.jpg'">
      <div><b>${escapeHtml(r.name)}</b><small>${escapeHtml(r.description || "")}</small></div>
      <div>Owner #${r.owner_id}<small>${escapeHtml(r.owner_username || "")}</small></div>
      <div>${r.items_count || 0} ingredienti</div>
      <div>${r.servings || 1} porz.</div>
      <div class="row-actions"><button class="edit-btn" data-edit-recipe="${r.id}">Edit</button><button class="delete-btn" data-delete-recipe="${r.id}">Del</button></div>
    </div>
  `).join("");
  document.querySelectorAll("[data-edit-recipe]").forEach(btn => btn.addEventListener("click", () => editRecipe(Number(btn.dataset.editRecipe))));
  document.querySelectorAll("[data-delete-recipe]").forEach(btn => btn.addEventListener("click", () => deleteRecipe(Number(btn.dataset.deleteRecipe))));
}

function editRecipe(id) {
  const r = state.recipes.find(x => x.id === id);
  if (!r) return;
  document.getElementById("admin-recipe-id").value = r.id;
  document.getElementById("admin-recipe-name").value = r.name || "";
  document.getElementById("admin-recipe-owner").value = r.owner_id || "";
  document.getElementById("admin-recipe-image").value = r.image || "";
  document.getElementById("admin-recipe-servings").value = r.servings || 1;
  document.getElementById("admin-recipe-time").value = r.prep_time_minutes || "";
  document.getElementById("admin-recipe-description").value = r.description || "";
  document.getElementById("admin-recipe-instructions").value = r.instructions || "";
}

function resetRecipeForm() {
  document.getElementById("admin-recipe-form").reset();
  document.getElementById("admin-recipe-id").value = "";
  document.getElementById("admin-recipe-servings").value = 1;
}

async function saveRecipe(e) {
  e.preventDefault();
  const id = document.getElementById("admin-recipe-id").value;
  const payload = {
    name: document.getElementById("admin-recipe-name").value.trim(),
    owner_id: Number(document.getElementById("admin-recipe-owner").value),
    image: document.getElementById("admin-recipe-image").value.trim() || null,
    servings: Number(document.getElementById("admin-recipe-servings").value || 1),
    prep_time_minutes: document.getElementById("admin-recipe-time").value ? Number(document.getElementById("admin-recipe-time").value) : null,
    description: document.getElementById("admin-recipe-description").value.trim() || null,
    instructions: document.getElementById("admin-recipe-instructions").value.trim() || null,
  };
  const res = await api(id ? `${CONFIG.API_BASE_URL}/admin/recipes/${id}` : `${CONFIG.API_BASE_URL}/admin/recipes`, { method: id ? "PUT" : "POST", body: JSON.stringify(payload) });
  if (!res?.ok) return toast("Errore salvataggio ricetta admin");
  toast(id ? "Ricetta aggiornata" : "Ricetta creata");
  resetRecipeForm();
  await loadRecipes();
}

async function deleteRecipe(id) {
  if (!confirm("Eliminare questa ricetta?")) return;
  const res = await api(`${CONFIG.API_BASE_URL}/admin/recipes/${id}`, { method: "DELETE" });
  if (!res?.ok) return toast("Errore eliminazione ricetta");
  toast("Ricetta eliminata");
  await loadRecipes();
}

function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
}

init();
