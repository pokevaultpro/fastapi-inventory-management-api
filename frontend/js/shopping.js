import CONFIG from "./config.js";
import { openProductModal } from "./modal-function.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

let shoppingList = [];     // cart items
let products = [];         // full products
let supermarkets = [];     // full supermarkets

const totalAllEl = document.getElementById("total-budget");
const totalPendingEl = document.getElementById("total-remaining");

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

function currentProductPrice(product) {
  return isDiscountActive(product) ? Number(product.discounted_price) : Number(product?.original_price || 0);
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


document.getElementById("clear-cart-btn")
  .addEventListener("click", clearCart);

document.getElementById("filter-status")
  .addEventListener("change", renderList);

document.getElementById("filter-store")
  .addEventListener("change", renderList);


// =========================
// 1. LOAD DATA FROM BACKEND
// =========================

async function loadCart() {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/cart`, {
    headers: { "Authorization": "Bearer " + token }
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


// =========================
// 2. INIT PAGE
// =========================

async function initCart() {
  // Load all data
  products = await loadProducts();
  supermarkets = await loadSupermarkets();
  const rawCart = await loadCart();

  // JOIN manuale cart → product → supermarket
  shoppingList = rawCart
    .map(item => {
      const product = products.find(p => p.id === item.product_id);
      if (!product) return null;
      const supermarket = supermarkets.find(s => s.id === product.supermarket_id) || { name: "Negozio" };

      return {
        ...item,
        product,
        supermarket
      };
    })
    .filter(Boolean);

  renderList();
  populateStoreFilter();
}

initCart();


// =========================
// 3. RENDER LIST
// =========================

function renderList() {
  const listEl = document.getElementById("shopping-list");
  const boughtEl = document.getElementById("shopping-bought");

  listEl.innerHTML = "";
  boughtEl.innerHTML = "";

  const storeFilter = document.getElementById("filter-store").value;

  // =========================
  // 1. FILTRO PER NEGOZIO
  // =========================
// 1. FILTRO PER NEGOZIO
let filtered = shoppingList.filter(item => {
  return storeFilter === "all" || item.supermarket.name === storeFilter;
});

// 2. FILTRO PER STATO (MANCAVA!)
const statusFilter = document.getElementById("filter-status").value;

if (statusFilter === "pending") {
  filtered = filtered.filter(i => !i.checked);
}

if (statusFilter === "bought") {
  filtered = filtered.filter(i => i.checked);
}

// 3. SPLIT PENDING / BOUGHT (solo per render)
let pendingItems = filtered.filter(i => !i.checked);
let boughtItems = filtered.filter(i => i.checked);


  // =========================
  // 3. ORDINAMENTO
  // =========================
  // "aisle_order" è l'ordine interno del supermercato/corsia.
  // Si usa SOLO quando scegli un supermercato specifico.
  // Non ha nulla a che vedere con la pagina del volantino.
  pendingItems.sort((a, b) => sortForShopping(a, b, storeFilter));
  boughtItems.sort((a, b) => sortForShopping(a, b, storeFilter));

  // =========================
  // 4. RENDER
  // =========================
  [...pendingItems, ...boughtItems].forEach(item => {
    const product = item.product;
    const supermarket = item.supermarket;

    const price = currentProductPrice(product);
    const subtotal = (price * item.quantity).toFixed(2);
    const hasDiscount = isDiscountActive(product);

    const div = document.createElement("div");
    div.className = "shopping-item" + (item.checked ? " bought" : "");

    div.addEventListener("click", (event) => {
      // Se clicchi un elemento con data-action, NON aprire il modal
      if (event.target.closest("[data-action]")) return;

      openProductModal(
        {
          ...product,
          quantity: item.quantity,
          store: supermarket.name,
          location: product.location,
          nutritional: product.nutritional
        },
        supermarket
      );
    });



div.innerHTML = `
  <div class="check-circle" data-action="toggle" data-id="${item.id}">
    ${item.checked ? "✔" : ""}
  </div>


  <div class="item-info">
    <img src="${product.image}" class="item-img ${item.checked ? "bought-img" : ""}">

    <div class="name ${item.checked ? "bought-text" : ""}">
      ${product.name}
      ${hasDiscount ? `<span class="sale-badge">SALE</span>` : ""}
    </div>

    <div class="unit-line">
      <span class="unit-price ${hasDiscount ? "discounted-unit" : ""}">
        ${price.toFixed(2).replace('.', ',')} € / pz
      </span>

      <span class="store-tag">${supermarket.name}</span>
    </div>
  </div>

  <div class="item-right">
<div class="qty-box">
  <button class="qty-btn" data-action="qty" data-delta="-1" data-id="${item.id}">−</button>
  <span>${item.quantity}</span>
  <button class="qty-btn" data-action="qty" data-delta="1" data-id="${item.id}">+</button>
</div>


    <span class="price ${item.checked ? "bought-price" : ""} ${hasDiscount ? "discounted" : ""}">
      € ${subtotal.replace('.', ',')}
    </span>

    <button class="remove-btn" data-action="remove" data-id="${item.id}">
      <img src="static/icons/trash.svg" class="trash-icon">
    </button>
  </div>
`;


        div.addEventListener("click", (event) => {
      const target = event.target.closest("[data-action]");
      if (!target) return;

      const id = Number(target.dataset.id);

      if (target.dataset.action === "toggle") {
        event.stopPropagation();
        toggleBought(event, id);
      }

      if (target.dataset.action === "qty") {
        event.stopPropagation();
        const delta = Number(target.dataset.delta);
        handleQtyClick(event, id, delta);
      }

      if (target.dataset.action === "remove") {
        event.stopPropagation();
        handleRemoveClick(event, id);
      }
    });


    if (item.checked) boughtEl.appendChild(div);
    else listEl.appendChild(div);
  });

  updateTotals();
  updateSectionVisibility();
  updateSelectAllButtonState();

}



// =========================
// 4. SECTION VISIBILITY
// =========================

function updateSectionVisibility() {
  document.getElementById("label-pending").style.display =
    shoppingList.some(i => !i.checked) ? "block" : "none";

  document.getElementById("shopping-list").style.display =
    shoppingList.some(i => !i.checked) ? "block" : "none";

  document.getElementById("label-bought").style.display =
    shoppingList.some(i => i.checked) ? "block" : "none";

  document.getElementById("shopping-bought").style.display =
    shoppingList.some(i => i.checked) ? "block" : "none";
}


// =========================
// 5. QUANTITY
// =========================

async function handleQtyClick(event, id, delta) {
  event.stopPropagation();
  await updateQty(id, delta);
}

async function updateQty(id, delta) {
  const item = shoppingList.find(i => i.id === id);
  if (!item) return;

  const newQty = Math.max(1, item.quantity + delta);

  await apiFetch(`${CONFIG.API_BASE_URL}/cart/${id}`, {
    method: "PUT",
    headers: {
      "Authorization": "Bearer " + token,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ quantity: newQty })
  });

  item.quantity = newQty;
  renderList();
}


// =========================
// 6. REMOVE ITEM
// =========================

async function handleRemoveClick(event, id) {
  event.stopPropagation();
  await removeItem(id);
}

async function removeItem(id) {
  await apiFetch(`${CONFIG.API_BASE_URL}/cart/${id}`, {
    method: "DELETE",
    headers: { "Authorization": "Bearer " + token }
  });

  shoppingList = shoppingList.filter(i => i.id !== id);
  renderList();
  populateStoreFilter();
}


// =========================
// 7. CHECKED / UNCHECKED
// =========================

async function toggleBought(event, id) {
  event.stopPropagation();

  const item = shoppingList.find(i => i.id === id);
  if (!item) return;

  const newValue = !item.checked;

  await apiFetch(`${CONFIG.API_BASE_URL}/cart/${id}`, {
    method: "PUT",
    headers: {
      "Authorization": "Bearer " + token,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ checked: newValue })
  });

  item.checked = newValue;
  renderList();
}


// =========================
// 8. TOTALS
// =========================

function updateTotals() {
  const storeFilter = document.getElementById("filter-store").value;

  const filtered = shoppingList.filter(item => {
    return storeFilter === "all" || item.supermarket.name === storeFilter;
  });

  const total = filtered.reduce((acc, i) => {
    const price = i.product.discounted_price ?? i.product.original_price;
    return acc + price * i.quantity;
  }, 0);

  const pending = filtered
    .filter(i => !i.checked)
    .reduce((acc, i) => {
      const price = i.product.discounted_price ?? i.product.original_price;
      return acc + price * i.quantity;
    }, 0);

  // aggiorna barra premium
  document.getElementById("total-budget").textContent =
    "€ " + total.toFixed(2).replace('.', ',');

  document.getElementById("total-remaining").textContent =
    "€ " + pending.toFixed(2).replace('.', ',');
}



// =========================
// 9. STORE FILTER
// =========================

function populateStoreFilter() {
  const storeSelect = document.getElementById("filter-store");
  const currentValue = storeSelect.value;

  const stores = [...new Set(shoppingList.map(i => i.supermarket.name))];

  storeSelect.innerHTML = `<option value="all">Tutti i negozi</option>`;

  stores.forEach(store => {
    storeSelect.innerHTML += `<option value="${store}">${store}</option>`;
  });

  if ([...storeSelect.options].some(opt => opt.value === currentValue)) {
    storeSelect.value = currentValue;
  } else {
    storeSelect.value = "all";
  }
}


// =========================
// 10. CLEAR CART
// =========================

async function clearCart() {

  if (!confirm("Vuoi davvero svuotare tutto il carrello?")) return;

  await apiFetch(`${CONFIG.API_BASE_URL}/cart`, {
    method: "DELETE",
    headers: { "Authorization": "Bearer " + token }
  });

  shoppingList = [];
  renderList();
  populateStoreFilter();
  updateTotals();
}
document.getElementById("finalize-btn").addEventListener("click", finalizeCart);

async function finalizeCart() {
  const purchased = shoppingList.filter(i => i.checked);
  if (purchased.length === 0) return;

  // UI loading

  const res = await apiFetch(`${CONFIG.API_BASE_URL}/cart/finalize`, {
    method: "POST",
    headers: { "Authorization": "Bearer " + token }
  });


  if (!res.ok) {
    alert("Errore durante la finalizzazione");
    return;
  }

  const data = await res.json();

  // Messaggio premium
  alert(`Hai finalizzato ${data.finalized_items} prodotti!`);

  // Aggiorna UI
  shoppingList = shoppingList.filter(i => !i.checked);
  renderList();
  populateStoreFilter();
  updateTotals();
}

document.getElementById("select-all-btn").addEventListener("click", async () => {
  const statusFilter = document.getElementById("filter-status").value;
  const storeFilter = document.getElementById("filter-store").value;

  // 1. Filtra gli item visibili
  let visibleItems = shoppingList.filter(item => {
    if (statusFilter === "pending" && item.checked) return false;
    if (statusFilter === "bought" && !item.checked) return false;
    if (storeFilter !== "all" && item.supermarket.name !== storeFilter) return false;
    return true;
  });

  // 2. Controlla se sono già tutti selezionati
  const allSelected = visibleItems.every(i => i.checked);

  // 3. Aggiorna backend per ogni item
  for (const item of visibleItems) {
    await apiFetch(`${CONFIG.API_BASE_URL}/cart/${item.id}`, {
      method: "PUT",
      headers: {
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ checked: !allSelected })
    });

    item.checked = !allSelected; // aggiorna anche localmente
  }

  // 4. Aggiorna UI
  renderList();
  updateTotals();

  // 5. Aggiorna bottone
  const btn = document.getElementById("select-all-btn");
  btn.classList.toggle("active", !allSelected);
  document.getElementById("select-all-text").textContent =
    allSelected ? "Seleziona Tutto" : "Deseleziona Tutto";
});



function updateSelectAllButtonState() {
  const statusFilter = document.getElementById("filter-status").value;
  const storeFilter = document.getElementById("filter-store").value;

  // stessi criteri di "visibile" usati nel click del bottone
  let visibleItems = shoppingList.filter(item => {
    if (statusFilter === "pending" && item.checked) return false;
    if (statusFilter === "bought" && !item.checked) return false;
    if (storeFilter !== "all" && item.supermarket.name !== storeFilter) return false;
    return true;
  });

  const btn = document.getElementById("select-all-btn");
  const textEl = document.getElementById("select-all-text");

  if (visibleItems.length === 0) {
    // niente da selezionare
    btn.classList.remove("active");
    textEl.textContent = "Seleziona Tutto";
    return;
  }

  const allSelected = visibleItems.every(i => i.checked);

  btn.classList.toggle("active", allSelected);
  textEl.textContent = allSelected ? "Deseleziona Tutto" : "Seleziona Tutto";
}
