import CONFIG from "./config.js";
import { openProductModal } from "./modal-function.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

let shoppingList = [];
let products = [];
let supermarkets = [];

document.getElementById("clear-cart-btn")?.addEventListener("click", clearCart);
document.getElementById("filter-status")?.addEventListener("change", renderList);
document.getElementById("filter-store")?.addEventListener("change", renderList);
document.getElementById("finalize-btn")?.addEventListener("click", finalizeCart);
document.getElementById("select-all-btn")?.addEventListener("click", selectAllVisible);

function formatEuro(value) {
  return Number(value || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
}

function euroInputValue(value) {
  return value == null ? "" : String(Number(value)).replace(".", ".");
}

function isDiscountActive(product) {
  if (!product) return false;
  const discounted = Number(product.discounted_price || 0);
  const original = Number(product.original_price || 0);
  if (!(discounted > 0 && original > 0 && discounted < original)) return false;
  const validTo = product.flyer_valid_to;
  if (!validTo) return true;
  const end = new Date(`${validTo}T23:59:59`);
  return Number.isNaN(end.getTime()) || end >= new Date();
}

function productPriceType(product) {
  const type = String(product?.price_type || "fixed").toLowerCase();
  return ["fixed", "weight", "manual"].includes(type) ? type : "fixed";
}

function productPriceUnit(product) {
  return product?.price_unit || product?.unit || (productPriceType(product) === "weight" ? "kg" : "pz");
}

function currentUnitPrice(product) {
  return isDiscountActive(product) ? Number(product.discounted_price || 0) : Number(product?.original_price || 0);
}

function itemWeight(item) {
  const actual = item.actual_weight;
  const estimated = item.estimated_weight;
  if (actual !== null && actual !== undefined && actual !== "") return Number(actual);
  if (estimated !== null && estimated !== undefined && estimated !== "") return Number(estimated);
  return null;
}

function lineTotal(item) {
  if (item.manual_price !== null && item.manual_price !== undefined && item.manual_price !== "") {
    return Number(item.manual_price || 0);
  }

  const product = item.product;
  const type = productPriceType(product);
  const unitPrice = currentUnitPrice(product);

  if (type === "weight") {
    const weight = itemWeight(item);
    return unitPrice * (weight ?? Number(item.quantity || 1));
  }

  return unitPrice * Number(item.quantity || 1);
}

function lineUnitText(item) {
  const product = item.product;
  const type = productPriceType(product);
  const unit = productPriceUnit(product);
  const price = currentUnitPrice(product);

  if (type === "manual") {
    return item.manual_price != null ? `Totale manuale ${formatEuro(item.manual_price)}` : "Prezzo finale da inserire";
  }

  if (type === "weight") {
    return `${formatEuro(price)} / ${unit}`;
  }

  return `${formatEuro(price)} / ${unit}`;
}

function variableSummary(item) {
  const type = productPriceType(item.product);
  if (type === "fixed") return "";

  if (type === "manual") {
    return item.manual_price != null ? `Prezzo finale: ${formatEuro(item.manual_price)}` : "Inserisci il prezzo finale prima di finalizzare";
  }

  const weight = itemWeight(item);
  const unit = productPriceUnit(item.product);
  return weight != null
    ? `Peso usato: ${String(weight).replace(".", ",")} ${unit}`
    : `Peso stimato: 1 ${unit}`;
}

function aisleOrder(item) {
  const value = Number(item?.product?.aisle_order);
  return Number.isFinite(value) ? value : 999999;
}

function sortForShopping(a, b, storeFilter) {
  if (storeFilter !== "all") {
    return aisleOrder(a) - aisleOrder(b) || String(a.product?.name || "").localeCompare(String(b.product?.name || ""), "it");
  }
  return String(a.supermarket?.name || "").localeCompare(String(b.supermarket?.name || ""), "it") ||
         String(a.product?.name || "").localeCompare(String(b.product?.name || ""), "it");
}

async function loadCart() {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/cart`, {
    headers: { Authorization: "Bearer " + token },
  });
  return res.ok ? res.json() : [];
}

async function loadProducts() {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/product`);
  return res.ok ? res.json() : [];
}

async function loadSupermarkets() {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/supermarket`);
  return res.ok ? res.json() : [];
}

async function initCart() {
  products = await loadProducts();
  supermarkets = await loadSupermarkets();
  const rawCart = await loadCart();

  shoppingList = rawCart
    .map((item) => {
      const product = products.find((p) => p.id === item.product_id);
      if (!product) return null;
      const supermarket = supermarkets.find((s) => s.id === product.supermarket_id) || { name: "Negozio" };
      return { ...item, product, supermarket };
    })
    .filter(Boolean);

  renderList();
  populateStoreFilter();
}

initCart();

function renderList() {
  const listEl = document.getElementById("shopping-list");
  const boughtEl = document.getElementById("shopping-bought");
  if (!listEl || !boughtEl) return;

  listEl.innerHTML = "";
  boughtEl.innerHTML = "";

  const storeFilter = document.getElementById("filter-store").value;
  const statusFilter = document.getElementById("filter-status").value;

  let filtered = shoppingList.filter((item) => storeFilter === "all" || item.supermarket.name === storeFilter);
  if (statusFilter === "pending") filtered = filtered.filter((i) => !i.checked);
  if (statusFilter === "bought") filtered = filtered.filter((i) => i.checked);

  const pendingItems = filtered.filter((i) => !i.checked).sort((a, b) => sortForShopping(a, b, storeFilter));
  const boughtItems = filtered.filter((i) => i.checked).sort((a, b) => sortForShopping(a, b, storeFilter));

  [...pendingItems, ...boughtItems].forEach((item) => renderShoppingItem(item, listEl, boughtEl));

  updateTotals();
  updateSectionVisibility();
  updateSelectAllButtonState();
}

function renderShoppingItem(item, listEl, boughtEl) {
  const product = item.product;
  const supermarket = item.supermarket;
  const type = productPriceType(product);
  const hasDiscount = isDiscountActive(product);
  const subtotal = lineTotal(item);
  const summary = variableSummary(item);
  const unit = productPriceUnit(product);

  const div = document.createElement("div");
  div.className = "shopping-item" + (item.checked ? " bought" : "") + (type !== "fixed" ? " variable-price-item" : "");

  div.innerHTML = `
    <div class="check-circle" data-action="toggle" data-id="${item.id}">
      ${item.checked ? "✔" : ""}
    </div>

    <div class="item-info">
      <img src="${product.image || "/static/images/placeholder.jpg"}" class="item-img ${item.checked ? "bought-img" : ""}">
      <div class="name ${item.checked ? "bought-text" : ""}">
        ${escapeHtml(product.name)}
        ${hasDiscount ? `<span class="sale-badge">SALE</span>` : ""}
        ${type === "weight" ? `<span class="variable-badge">al peso</span>` : ""}
        ${type === "manual" ? `<span class="variable-badge manual">manuale</span>` : ""}
      </div>

      <div class="unit-line">
        <span class="unit-price ${hasDiscount ? "discounted-unit" : ""}">${lineUnitText(item)}</span>
        <span class="store-tag">${escapeHtml(supermarket.name)}</span>
      </div>

      ${summary ? `<div class="variable-summary">${escapeHtml(summary)}</div>` : ""}

      ${type !== "fixed" ? variableControlsHtml(item, type, unit) : ""}
    </div>

    <div class="item-right">
      <div class="qty-box">
        <button class="qty-btn" data-action="qty" data-delta="-1" data-id="${item.id}">−</button>
        <span>${item.quantity}</span>
        <button class="qty-btn" data-action="qty" data-delta="1" data-id="${item.id}">+</button>
      </div>

      <span class="price ${item.checked ? "bought-price" : ""} ${hasDiscount ? "discounted" : ""}">
        ${formatEuro(subtotal)}
      </span>

      <button class="remove-btn" data-action="remove" data-id="${item.id}">
        <img src="static/icons/trash.svg" class="trash-icon">
      </button>
    </div>
  `;

  div.addEventListener("click", (event) => {
    if (event.target.closest("[data-action]") || event.target.closest("[data-variable-field]")) return;
    openProductModal({ ...product, quantity: item.quantity, store: supermarket.name, location: product.location }, supermarket);
  });

  div.addEventListener("click", async (event) => {
    const target = event.target.closest("[data-action]");
    if (!target) return;
    event.stopPropagation();

    const id = Number(target.dataset.id);
    if (target.dataset.action === "toggle") await toggleBought(event, id);
    if (target.dataset.action === "qty") await handleQtyClick(event, id, Number(target.dataset.delta));
    if (target.dataset.action === "remove") await handleRemoveClick(event, id);
  });

  div.querySelectorAll("[data-variable-field]").forEach((input) => {
    input.addEventListener("click", (event) => event.stopPropagation());
    input.addEventListener("change", async (event) => {
      event.stopPropagation();
      await updateVariableField(item.id, event.target.dataset.variableField, event.target.value);
    });
  });

  if (item.checked) boughtEl.appendChild(div);
  else listEl.appendChild(div);
}

function variableControlsHtml(item, type, unit) {
  const weightControls = type === "weight" ? `
    <label>Peso stimato (${escapeHtml(unit)})
      <input data-variable-field="estimated_weight" type="number" step="0.001" min="0" value="${item.estimated_weight ?? ""}" placeholder="es. 0.750">
    </label>
    <label>Peso reale (${escapeHtml(unit)})
      <input data-variable-field="actual_weight" type="number" step="0.001" min="0" value="${item.actual_weight ?? ""}" placeholder="dallo scontrino">
    </label>
  ` : "";

  return `
    <div class="variable-price-controls">
      ${weightControls}
      <label>Prezzo finale (€)
        <input data-variable-field="manual_price" type="number" step="0.01" min="0" value="${item.manual_price ?? ""}" placeholder="${type === "manual" ? "obbligatorio" : "opzionale"}">
      </label>
    </div>
  `;
}

async function updateVariableField(id, field, rawValue) {
  const item = shoppingList.find((i) => i.id === id);
  if (!item) return;

  const value = rawValue === "" ? null : Number(rawValue);
  if (value !== null && (!Number.isFinite(value) || value < 0)) {
    alert("Inserisci un numero valido maggiore o uguale a 0.");
    renderList();
    return;
  }

  const res = await apiFetch(`${CONFIG.API_BASE_URL}/cart/${id}`, {
    method: "PUT",
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ [field]: value }),
  });

  if (!res.ok) {
    alert("Non riesco a salvare peso/prezzo.");
    renderList();
    return;
  }

  item[field] = value;
  renderList();
}

function updateSectionVisibility() {
  document.getElementById("label-pending").style.display = shoppingList.some((i) => !i.checked) ? "block" : "none";
  document.getElementById("shopping-list").style.display = shoppingList.some((i) => !i.checked) ? "block" : "none";
  document.getElementById("label-bought").style.display = shoppingList.some((i) => i.checked) ? "block" : "none";
  document.getElementById("shopping-bought").style.display = shoppingList.some((i) => i.checked) ? "block" : "none";
}

async function handleQtyClick(event, id, delta) {
  event.stopPropagation();
  await updateQty(id, delta);
}

async function updateQty(id, delta) {
  const item = shoppingList.find((i) => i.id === id);
  if (!item) return;

  const newQty = Math.max(1, Number(item.quantity || 1) + delta);

  const res = await apiFetch(`${CONFIG.API_BASE_URL}/cart/${id}`, {
    method: "PUT",
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ quantity: newQty }),
  });

  if (!res.ok) return;
  item.quantity = newQty;
  renderList();
}

async function handleRemoveClick(event, id) {
  event.stopPropagation();
  await removeItem(id);
}

async function removeItem(id) {
  await apiFetch(`${CONFIG.API_BASE_URL}/cart/${id}`, {
    method: "DELETE",
    headers: { Authorization: "Bearer " + token },
  });

  shoppingList = shoppingList.filter((i) => i.id !== id);
  renderList();
  populateStoreFilter();
}

async function toggleBought(event, id) {
  event.stopPropagation();

  const item = shoppingList.find((i) => i.id === id);
  if (!item) return;

  const newValue = !item.checked;

  const res = await apiFetch(`${CONFIG.API_BASE_URL}/cart/${id}`, {
    method: "PUT",
    headers: {
      Authorization: "Bearer " + token,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ checked: newValue }),
  });

  if (!res.ok) return;
  item.checked = newValue;
  renderList();
}

function updateTotals() {
  const storeFilter = document.getElementById("filter-store").value;
  const filtered = shoppingList.filter((item) => storeFilter === "all" || item.supermarket.name === storeFilter);

  const total = filtered.reduce((acc, i) => acc + lineTotal(i), 0);
  const pending = filtered.filter((i) => !i.checked).reduce((acc, i) => acc + lineTotal(i), 0);

  document.getElementById("total-budget").textContent = formatEuro(total);
  document.getElementById("total-remaining").textContent = formatEuro(pending);
}

function populateStoreFilter() {
  const storeSelect = document.getElementById("filter-store");
  const currentValue = storeSelect.value;
  const stores = [...new Set(shoppingList.map((i) => i.supermarket.name))];

  storeSelect.innerHTML = `<option value="all">Tutti i negozi</option>`;
  stores.forEach((store) => {
    storeSelect.innerHTML += `<option value="${escapeHtml(store)}">${escapeHtml(store)}</option>`;
  });

  storeSelect.value = [...storeSelect.options].some((opt) => opt.value === currentValue) ? currentValue : "all";
}

async function clearCart() {
  if (!confirm("Vuoi davvero svuotare tutto il carrello?")) return;

  await apiFetch(`${CONFIG.API_BASE_URL}/cart`, {
    method: "DELETE",
    headers: { Authorization: "Bearer " + token },
  });

  shoppingList = [];
  renderList();
  populateStoreFilter();
  updateTotals();
}

async function finalizeCart() {
  const purchased = shoppingList.filter((i) => i.checked);
  if (purchased.length === 0) return;

  const missingManual = purchased.find((i) => productPriceType(i.product) === "manual" && i.manual_price == null && Number(i.product.original_price || 0) <= 0);
  if (missingManual) {
    alert(`Inserisci il prezzo finale per "${missingManual.product.name}" prima di finalizzare.`);
    return;
  }

  const res = await apiFetch(`${CONFIG.API_BASE_URL}/cart/finalize`, {
    method: "POST",
    headers: { Authorization: "Bearer " + token },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    alert(error.detail || "Errore durante la finalizzazione");
    return;
  }

  const data = await res.json();
  alert(`Hai finalizzato ${data.finalized_items} prodotti per ${formatEuro(data.total_price || 0)}!`);

  shoppingList = shoppingList.filter((i) => !i.checked);
  renderList();
  populateStoreFilter();
  updateTotals();
}

async function selectAllVisible() {
  const statusFilter = document.getElementById("filter-status").value;
  const storeFilter = document.getElementById("filter-store").value;

  const visibleItems = shoppingList.filter((item) => {
    if (statusFilter === "pending" && item.checked) return false;
    if (statusFilter === "bought" && !item.checked) return false;
    if (storeFilter !== "all" && item.supermarket.name !== storeFilter) return false;
    return true;
  });

  const allSelected = visibleItems.every((i) => i.checked);

  for (const item of visibleItems) {
    await apiFetch(`${CONFIG.API_BASE_URL}/cart/${item.id}`, {
      method: "PUT",
      headers: {
        Authorization: "Bearer " + token,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ checked: !allSelected }),
    });

    item.checked = !allSelected;
  }

  renderList();
  updateTotals();
}

function updateSelectAllButtonState() {
  const statusFilter = document.getElementById("filter-status").value;
  const storeFilter = document.getElementById("filter-store").value;

  const visibleItems = shoppingList.filter((item) => {
    if (statusFilter === "pending" && item.checked) return false;
    if (statusFilter === "bought" && !item.checked) return false;
    if (storeFilter !== "all" && item.supermarket.name !== storeFilter) return false;
    return true;
  });

  const btn = document.getElementById("select-all-btn");
  const textEl = document.getElementById("select-all-text");
  if (!btn || !textEl) return;

  if (visibleItems.length === 0) {
    btn.classList.remove("active");
    textEl.textContent = "Seleziona Tutto";
    return;
  }

  const allSelected = visibleItems.every((i) => i.checked);
  btn.classList.toggle("active", allSelected);
  textEl.textContent = allSelected ? "Deseleziona Tutto" : "Seleziona Tutto";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
}
