import CONFIG from "./config.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

async function apiRequest(url, options = {}) {
  const currentToken = localStorage.getItem("token");
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
    "Authorization": `Bearer ${currentToken}`
  };
  const res = await fetch(url, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "index.html";
    return null;
  }
  return res;
}

async function errorMessage(res, fallback) {
  try {
    const data = await res.json();
    return data?.detail || fallback;
  } catch {
    return fallback;
  }
}

let products = [];
let supermarkets = [];
let recipes = [];
let selectedIngredients = [];
let activeRecipe = null;

const euro = (v) => Number(v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
const img = (src) => src || "/static/images/placeholder.jpg";
const currentPrice = (p) => Number(p?.current_price ?? (p?.discounted_price || p?.original_price || 0));

function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2600);
}

async function loadAll() {
  const [productsRes, supermarketsRes, recipesRes] = await Promise.all([
    apiRequest(`${CONFIG.API_BASE_URL}/product`),
    apiRequest(`${CONFIG.API_BASE_URL}/supermarket`),
    apiRequest(`${CONFIG.API_BASE_URL}/smart-recipes`),
  ]);
  products = productsRes?.ok ? await productsRes.json() : [];
  supermarkets = supermarketsRes?.ok ? await supermarketsRes.json() : [];
  recipes = recipesRes?.ok ? await recipesRes.json() : [];
  renderRecipes();
  renderDaily();
}

function storeName(product) {
  const sm = supermarkets.find(s => s.id === product?.supermarket_id);
  return sm?.name || product?.supermarket_name || "Negozio";
}

function renderRecipes() {
  const q = document.getElementById("recipe-search").value.trim().toLowerCase();
  const list = recipes.filter(r => !q || r.name.toLowerCase().includes(q) || (r.description || "").toLowerCase().includes(q));
  const grid = document.getElementById("recipes-grid");

  if (!list.length) {
    grid.innerHTML = `<div class="empty-state">Nessuna ricetta ancora. Crea la prima selezionando prodotti reali del catalogo.</div>`;
    return;
  }

  grid.innerHTML = list.map(r => `
    <article class="recipe-card" data-id="${r.id}">
      <img src="${img(r.image)}" onerror="this.src='/static/images/placeholder.jpg'">
      <div class="recipe-body">
        <div class="recipe-title-row">
          <h3>${escapeHtml(r.name)}</h3>
          <span class="recipe-source">${r.source_type === "personal" ? "Personale" : "Sistema"}</span>
        </div>
        <p>${escapeHtml(r.description || "Ricetta personale pronta da aggiungere alla lista della spesa.")}</p>
        <div class="recipe-stats">
          <span>${r.items_count || 0} ingredienti</span>
          <span>${r.servings || 1} porz.</span>
          <span class="recipe-price">${euro(r.estimated_total)}</span>
        </div>
        <div class="recipe-card-actions">
          <button type="button" class="ghost-mini" data-action="view" data-id="${r.id}">Apri</button>
          <button type="button" class="ghost-mini" data-action="edit" data-id="${r.id}">Modifica</button>
          <button type="button" class="danger-mini" data-action="delete" data-id="${r.id}">Elimina</button>
        </div>
      </div>
    </article>
  `).join("");

  grid.querySelectorAll("[data-action]").forEach(btn => {
    btn.addEventListener("click", async (event) => {
      event.stopPropagation();
      const id = Number(btn.dataset.id);
      const action = btn.dataset.action;
      if (action === "view") return openDetail(id);
      if (action === "edit") return openEdit(id);
      if (action === "delete") return deleteRecipe(id);
    });
  });

  grid.querySelectorAll(".recipe-card").forEach(card => {
    card.addEventListener("click", () => openDetail(Number(card.dataset.id)));
  });
}

async function renderDaily() {
  const card = document.getElementById("daily-card");
  card.innerHTML = `<div class="skeleton"></div>`;

  const res = await apiRequest(`${CONFIG.API_BASE_URL}/smart-recipes/daily/today`);
  if (!res?.ok) {
    card.innerHTML = `<h3>Ricetta del giorno</h3><p>Non riesco a caricarla ora. Controlla che il backend sia avviato e che la migrazione DB sia stata fatta.</p>`;
    return;
  }

  const d = await res.json();
  card.innerHTML = `
    <img src="${img(d.image)}" onerror="this.style.display='none'">
    <h3>${escapeHtml(d.name)}</h3>
    <p>${escapeHtml(d.description || "Ricetta italiana locale abbinata al tuo catalogo prodotti.")}</p>
    <div class="daily-meta">
      <span class="chip green">${euro(d.estimated_total)} stimati</span>
      <span class="chip orange">${d.matched_items.length} prodotti trovati</span>
      <span class="chip">${d.missing_ingredients.length} mancanti</span>
    </div>
    <div class="daily-actions">
      <button type="button" class="primary-btn" id="add-daily">Aggiungi trovati</button>
      <button type="button" class="ghost-btn" id="daily-info">Dettagli</button>
    </div>
  `;

  document.getElementById("add-daily").addEventListener("click", async () => {
    const addRes = await apiRequest(`${CONFIG.API_BASE_URL}/smart-recipes/daily/add-to-cart`, { method: "POST", body: "{}" });
    if (!addRes?.ok) return toast("Non riesco ad aggiungere la ricetta del giorno");
    const out = await addRes.json();
    toast(`${out.added_count} prodotti aggiunti alla lista`);
  });

  document.getElementById("daily-info").addEventListener("click", () => {
    const lines = d.matched_items.map(m => `• ${m.ingredient}: ${m.product.name} (${euro(m.line_total)})`).join("\n");
    alert(`${d.name}\n\nProdotti trovati:\n${lines || "Nessuno"}\n\nMancanti: ${d.missing_ingredients.map(x => x.name).join(", ") || "nessuno"}\n\n${d.note || ""}`);
  });
}

function openBuilder(recipe = null) {
  activeRecipe = recipe;
  selectedIngredients = [];

  document.getElementById("builder-title").textContent = recipe ? "Modifica ricetta" : "Nuova ricetta";
  document.getElementById("recipe-submit-btn").textContent = recipe ? "Salva modifiche" : "Salva ricetta";
  document.getElementById("recipe-form").reset();

  document.getElementById("recipe-name").value = recipe?.name || "";
  document.getElementById("recipe-image").value = recipe?.image || "";
  document.getElementById("recipe-servings").value = recipe?.servings || 2;
  document.getElementById("recipe-time").value = recipe?.prep_time_minutes || "";
  document.getElementById("recipe-description").value = recipe?.description || "";
  document.getElementById("recipe-instructions").value = recipe?.instructions || "";

  if (recipe?.items?.length) {
    selectedIngredients = recipe.items
      .filter(it => it.product)
      .map(it => ({
        recipe_item_id: it.id,
        product_id: it.product_id,
        quantity: it.quantity || 1,
        cart_quantity: it.cart_quantity || it.quantity || 1,
        amount: it.amount,
        amount_unit: it.amount_unit || "",
        note: it.note || "",
        is_optional: Boolean(it.is_optional),
        product: it.product,
      }));
  }

  renderSelectedIngredients();
  document.getElementById("recipe-builder").classList.remove("hidden");
  setTimeout(() => document.getElementById("recipe-name").focus(), 50);
}

function closeBuilder() {
  document.getElementById("recipe-builder").classList.add("hidden");
  activeRecipe = null;
  selectedIngredients = [];
}

async function openEdit(id) {
  const res = await apiRequest(`${CONFIG.API_BASE_URL}/smart-recipes/${id}`);
  if (!res?.ok) return toast("Non riesco a caricare la ricetta da modificare");
  const recipe = await res.json();
  openBuilder(recipe);
}

async function deleteRecipe(id) {
  const recipe = recipes.find(r => r.id === id);
  const ok = confirm(`Eliminare la ricetta "${recipe?.name || id}"?`);
  if (!ok) return;

  const res = await apiRequest(`${CONFIG.API_BASE_URL}/smart-recipes/${id}`, { method: "DELETE" });
  if (!res?.ok) return toast(await errorMessage(res, "Non riesco a eliminare la ricetta"));
  toast("Ricetta eliminata");
  await loadAll();
}

function searchProducts() {
  const q = document.getElementById("product-search").value.trim().toLowerCase();
  const box = document.getElementById("product-results");

  if (!q) {
    box.innerHTML = `<div class="empty-state">Cerca un prodotto da usare come ingrediente.</div>`;
    return;
  }

  const found = products
    .filter(p => p.name.toLowerCase().includes(q) || (p.category || "").toLowerCase().includes(q) || (p.brand || "").toLowerCase().includes(q))
    .slice(0, 24);

  box.innerHTML = found.length ? found.map(p => `
    <div class="product-result">
      <img src="${img(p.image)}" onerror="this.src='/static/images/placeholder.jpg'">
      <div><b>${escapeHtml(p.name)}</b><small>${escapeHtml(storeName(p))} · ${escapeHtml(p.unit || "pz")} · ${euro(currentPrice(p))}</small></div>
      <button type="button" data-id="${p.id}">+</button>
    </div>
  `).join("") : `<div class="empty-state">Nessun prodotto trovato.</div>`;

  box.querySelectorAll("button[data-id]").forEach(btn => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      addIngredient(Number(btn.dataset.id));
    });
  });
}

function addIngredient(productId) {
  const p = products.find(x => x.id === productId);
  if (!p) return;
  if (selectedIngredients.some(i => i.product_id === productId)) return toast("Ingrediente già aggiunto");
  selectedIngredients.push({ product_id: p.id, quantity: 1, cart_quantity: 1, amount: null, amount_unit: "", note: "", is_optional: false, product: p });
  renderSelectedIngredients();
  toast("Ingrediente aggiunto alla bozza. Premi Salva per confermare.");
}

function renderSelectedIngredients() {
  const box = document.getElementById("selected-ingredients");

  if (!selectedIngredients.length) {
    box.innerHTML = `<div class="empty-state">Aggiungi prodotti dal catalogo. La ricetta sarà salvata solo quando premi “Salva ricetta”.</div>`;
  } else {
    box.innerHTML = selectedIngredients.map((i, idx) => `
      <div class="ingredient-row">
        <img src="${img(i.product.image)}" onerror="this.src='/static/images/placeholder.jpg'">
        <div><b>${escapeHtml(i.product.name)}</b><small>${escapeHtml(storeName(i.product))} · ${euro(currentPrice(i.product))}</small></div>
        <button type="button" data-remove="${idx}">×</button>
        <div class="ingredient-controls">
          <input data-field="amount" data-idx="${idx}" type="number" min="0" step="0.1" placeholder="Qtà ricetta" value="${i.amount ?? ""}">
          <input data-field="amount_unit" data-idx="${idx}" placeholder="g, ml, pz..." value="${escapeAttr(i.amount_unit || "")}">
          <input data-field="cart_quantity" data-idx="${idx}" type="number" min="1" step="1" value="${i.cart_quantity || 1}" title="Quantità da aggiungere al carrello">
          <label><input data-field="is_optional" data-idx="${idx}" type="checkbox" ${i.is_optional ? "checked" : ""}> opz.</label>
        </div>
      </div>
    `).join("");
  }

  updateBuilderTotal();

  box.querySelectorAll("[data-remove]").forEach(btn => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      selectedIngredients.splice(Number(btn.dataset.remove), 1);
      renderSelectedIngredients();
    });
  });

  box.querySelectorAll("input[data-field]").forEach(inp => {
    inp.addEventListener("input", () => {
      const idx = Number(inp.dataset.idx);
      const field = inp.dataset.field;
      if (field === "is_optional") selectedIngredients[idx][field] = inp.checked;
      else if (["amount", "cart_quantity"].includes(field)) selectedIngredients[idx][field] = inp.value ? Number(inp.value) : null;
      else selectedIngredients[idx][field] = inp.value;
      updateBuilderTotal();
    });
  });
}

function updateBuilderTotal() {
  document.getElementById("builder-total").textContent = euro(
    selectedIngredients.reduce((s, i) => s + currentPrice(i.product) * Number(i.cart_quantity || 1), 0)
  );
}

async function submitRecipe(e) {
  e.preventDefault();

  if (!selectedIngredients.length) {
    toast("Aggiungi almeno un ingrediente prima di salvare");
    return;
  }

  const payload = {
    name: document.getElementById("recipe-name").value.trim(),
    image: document.getElementById("recipe-image").value.trim() || null,
    servings: Number(document.getElementById("recipe-servings").value || 1),
    prep_time_minutes: document.getElementById("recipe-time").value ? Number(document.getElementById("recipe-time").value) : null,
    description: document.getElementById("recipe-description").value.trim() || null,
    instructions: document.getElementById("recipe-instructions").value.trim() || null,
    items: selectedIngredients.map(i => ({
      product_id: i.product_id,
      quantity: Number(i.quantity || 1),
      cart_quantity: Number(i.cart_quantity || 1),
      amount: i.amount,
      amount_unit: i.amount_unit || null,
      note: i.note || null,
      is_optional: Boolean(i.is_optional),
    }))
  };

  const isEdit = Boolean(activeRecipe?.id);
  const url = isEdit ? `${CONFIG.API_BASE_URL}/smart-recipes/${activeRecipe.id}` : `${CONFIG.API_BASE_URL}/smart-recipes`;
  const method = isEdit ? "PUT" : "POST";

  const res = await apiRequest(url, { method, body: JSON.stringify(payload) });
  if (!res?.ok) return toast(await errorMessage(res, "Errore salvataggio ricetta"));

  closeBuilder();
  toast(isEdit ? "Ricetta aggiornata" : "Ricetta salvata");
  await loadAll();
}

async function openDetail(id) {
  const res = await apiRequest(`${CONFIG.API_BASE_URL}/smart-recipes/${id}`);
  if (!res?.ok) return toast("Ricetta non trovata");
  const r = await res.json();
  activeRecipe = r;

  const content = document.getElementById("detail-content");
  content.innerHTML = `
    <div class="detail-header">
      <img src="${img(r.image)}" onerror="this.src='/static/images/placeholder.jpg'">
      <div>
        <p class="eyebrow">${r.source_type === "personal" ? "Ricetta personale" : "Ricetta"}</p>
        <h2>${escapeHtml(r.name)}</h2>
        <p>${escapeHtml(r.description || "Seleziona cosa aggiungere e regola le quantità prima di creare la lista.")}</p>
        <div class="daily-meta"><span class="chip green">${euro(r.estimated_total)} totali</span><span class="chip">${r.servings} porzioni</span><span class="chip orange">${r.items_count} ingredienti</span></div>
        <div class="detail-top-actions">
          <button type="button" class="ghost-btn" id="edit-current-recipe">Modifica</button>
          <button type="button" class="danger-btn" id="delete-current-recipe">Elimina</button>
        </div>
      </div>
    </div>
    <div class="ingredient-checks">
      ${r.items.map(it => `
        <label class="check-row">
          <input type="checkbox" data-item="${it.id}" checked>
          <img src="${img(it.product?.image)}" onerror="this.src='/static/images/placeholder.jpg'">
          <div>
            <b>${escapeHtml(it.product?.name || "Prodotto")}</b>
            <small>${escapeHtml([it.amount ? `${it.amount} ${it.amount_unit || ""}` : "", it.product?.supermarket_name || "", euro(it.product?.current_price || 0)].filter(Boolean).join(" · "))}</small>
            ${(it.cheaper_alternatives || []).length ? `<div class="alt-box">Risparmio possibile: ${escapeHtml(it.cheaper_alternatives[0].product.name)} (${euro(it.cheaper_alternatives[0].product.current_price)})</div>` : ""}
          </div>
          <input type="number" min="1" value="${it.cart_quantity || 1}" data-qty="${it.id}">
        </label>`).join("")}
    </div>
    <div class="detail-footer"><strong>Totale stimato: ${euro(r.estimated_total)}</strong><button type="button" class="primary-btn" id="add-recipe-cart">Aggiungi selezionati alla lista</button></div>
  `;

  document.getElementById("recipe-detail").classList.remove("hidden");
  document.getElementById("add-recipe-cart").addEventListener("click", addSelectedRecipeToCart);
  document.getElementById("edit-current-recipe").addEventListener("click", () => {
    document.getElementById("recipe-detail").classList.add("hidden");
    openBuilder(r);
  });
  document.getElementById("delete-current-recipe").addEventListener("click", async () => {
    document.getElementById("recipe-detail").classList.add("hidden");
    await deleteRecipe(r.id);
  });
}

async function addSelectedRecipeToCart() {
  if (!activeRecipe) return;
  const items = activeRecipe.items.map(it => {
    const checked = document.querySelector(`input[data-item="${it.id}"]`)?.checked;
    const qty = Number(document.querySelector(`input[data-qty="${it.id}"]`)?.value || 1);
    return { recipe_item_id: it.id, quantity: qty, excluded: !checked };
  });

  const res = await apiRequest(`${CONFIG.API_BASE_URL}/smart-recipes/${activeRecipe.id}/add-to-cart`, { method: "POST", body: JSON.stringify({ items, replace_cart: false }) });
  if (!res?.ok) return toast("Non riesco ad aggiungere la ricetta");
  const out = await res.json();
  document.getElementById("recipe-detail").classList.add("hidden");
  const changed = out.changed_prices?.length ? ` · ${out.changed_prices.length} prezzi cambiati` : "";
  toast(`${out.added_count} prodotti aggiunti${changed}`);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
}

function escapeAttr(value) {
  return escapeHtml(value).replace(/"/g, "&quot;");
}

document.getElementById("open-create").addEventListener("click", () => openBuilder());
document.getElementById("close-builder").addEventListener("click", closeBuilder);
document.getElementById("close-detail").addEventListener("click", () => document.getElementById("recipe-detail").classList.add("hidden"));
document.getElementById("product-search").addEventListener("input", searchProducts);
document.getElementById("recipe-search").addEventListener("input", renderRecipes);
document.getElementById("recipe-form").addEventListener("submit", submitRecipe);
document.getElementById("refresh-daily").addEventListener("click", renderDaily);

loadAll();
