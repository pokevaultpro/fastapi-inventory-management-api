import CONFIG from "./config.js";

const state = {
  flyers: [],
  flyerId: null,
  flyerTitle: "",
  items: [],
  total: 0,
  offset: 0,
  limit: 25,
  match: "",
  status: "",
  selected: new Set(),
};

const $ = (id) => document.getElementById(id);
const token = () => localStorage.getItem("token");

const placeholder =
  "data:image/svg+xml;charset=UTF-8," +
  encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="120" height="120">
      <rect width="120" height="120" rx="18" fill="#f1f5f9"/>
      <text x="60" y="58" text-anchor="middle" font-family="Arial" font-size="13" font-weight="700" fill="#64748b">no image</text>
      <text x="60" y="78" text-anchor="middle" font-family="Arial" font-size="10" fill="#94a3b8">offer</text>
    </svg>
  `);

function esc(v) {
  return String(v ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
}

function euro(v) {
  return Number(v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
}

function mediaUrl(path) {
  if (!path) return placeholder;
  const value = String(path).trim();
  if (!value || value.toLowerCase().includes("placeholder")) return placeholder;
  if (value.startsWith("data:")) return value;
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  if (value.startsWith("/static/")) return `${CONFIG.API_BASE_URL}${value}`;
  if (value.startsWith("static/")) return `${CONFIG.API_BASE_URL}/${value}`;
  return value;
}

async function api(path, options = {}) {
  const headers = {
    Authorization: `Bearer ${token()}`,
    ...(options.headers || {}),
  };

  const res = await fetch(`${CONFIG.API_BASE_URL}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "index.html";
  }

  return res;
}

async function readError(res) {
  try {
    const data = await res.json();
    return typeof data.detail === "string" ? data.detail : JSON.stringify(data);
  } catch {
    return res.statusText || "Errore";
  }
}

function labelMatch(status) {
  if (String(status || "").startsWith("auto_matched")) return "auto";
  if (status === "needs_review") return "controlla";
  if (status === "new_product_suggestion") return "nuovo";
  if (status === "manual_matched") return "manuale";
  if (status === "bulk_matched") return "bulk";
  if (status === "created_product") return "creato";
  return status || "n/d";
}

async function loadFlyers() {
  $("flyersList").innerHTML = `<div class="loading">Caricamento volantini...</div>`;

  const res = await api("/admin/flyer-offers-page/flyers");
  if (!res.ok) {
    $("flyersList").innerHTML = `<div class="error">${esc(await readError(res))}</div>`;
    return;
  }

  state.flyers = await res.json();
  renderFlyers();
}

function renderFlyers() {
  if (!state.flyers.length) {
    $("flyersList").innerHTML = `<div class="empty">Nessun volantino trovato.</div>`;
    return;
  }

  $("flyersList").innerHTML = state.flyers.map((f) => `
    <button class="flyer-card ${Number(f.id) === Number(state.flyerId) ? "active" : ""}" data-flyer="${f.id}" data-title="${esc(f.title || f.retailer || "")}">
      <strong>${esc(f.title || f.retailer || "Volantino")}</strong>
      <span>${esc(f.retailer)} · ${esc(f.valid_from || "?")} → ${esc(f.valid_to || "?")}</span>
      <small>
        ${f.offers_count || 0} offerte ·
        ${f.auto_matched_count || 0} auto ·
        ${f.needs_review_count || 0} dubbi ·
        ${f.new_product_count || 0} nuovi ·
        ${f.approved_count || 0} approved ·
        ${f.published_count || 0} published
      </small>
    </button>
  `).join("");

  document.querySelectorAll("[data-flyer]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.flyerId = Number(btn.dataset.flyer);
      state.flyerTitle = btn.dataset.title || "";
      state.offset = 0;
      state.selected.clear();
      $("currentFlyerLabel").textContent = state.flyerTitle;
      renderFlyers();
      loadOffers();
    });
  });
}

async function loadOffers() {
  if (!state.flyerId) return;

  $("offersList").className = "offers-list empty";
  $("offersList").innerHTML = "Caricamento offerte...";

  const params = new URLSearchParams({
    limit: state.limit,
    offset: state.offset,
  });
  if (state.match) params.set("match_status", state.match);
  if (state.status) params.set("status_filter", state.status);

  const res = await api(`/admin/flyer-offers-page/flyers/${state.flyerId}/offers?${params.toString()}`);
  if (!res.ok) {
    $("offersList").innerHTML = `<div class="error">${esc(await readError(res))}</div>`;
    return;
  }

  const data = await res.json();
  state.items = data.items || [];
  state.total = data.total || 0;

  // Deselect offers not on page to keep bulk actions predictable.
  const pageIds = new Set(state.items.map((x) => Number(x.id)));
  state.selected = new Set(Array.from(state.selected).filter((id) => pageIds.has(id)));

  renderOffers();
}

function renderOffers() {
  $("offersMeta").textContent = `${state.total} offerte totali · mostrate ${state.items.length} · offset ${state.offset}`;

  if (!state.items.length) {
    $("offersList").className = "offers-list empty";
    $("offersList").innerHTML = "Nessuna offerta con questi filtri.";
    updateSelection();
    updatePager();
    return;
  }

  $("offersList").className = "offers-list";
  $("offersList").innerHTML = state.items.map((o) => `
    <article class="offer-row" data-id="${o.id}">
      <label class="check"><input type="checkbox" data-check="${o.id}" ${state.selected.has(Number(o.id)) ? "checked" : ""}></label>

      <button class="image-btn" data-img="${esc(mediaUrl(o.image))}">Mostra img</button>

      <div class="offer-main">
        <div class="badges">
          <span class="badge match ${esc(o.match_status || "")}">${esc(labelMatch(o.match_status))} · ${Math.round(Number(o.match_score || 0) * 100)}%</span>
          <span class="badge">${esc(o.status)}</span>
          <span class="badge">pag. ${esc(o.flyer_page || "?")}</span>
        </div>
        <h3>${esc(o.raw_name)}</h3>
        <p>${esc(o.category || "Altro")} · ${esc(o.unit || o.price_unit || "pz")} · ${esc(o.price_type || "fixed")}</p>
        <p class="matchline">Match: <strong>${esc(o.product_name || o.suggested_product_name || "nessuno")}</strong></p>
      </div>

      <div class="price">${euro(o.offer_price)}</div>

      <div class="row-actions">
        ${o.suggested_product_id ? `<button class="secondary" data-action="associate" data-product="${o.suggested_product_id}">Associa suggerito</button>` : ""}
        <button class="secondary" data-action="search">Cerca</button>
        <button class="primary" data-action="create">Crea prodotto</button>
        <button class="danger" data-action="reject">Scarta</button>
      </div>
    </article>
  `).join("");

  updateSelection();
  updatePager();
}

function updateSelection() {
  $("selectedCount").textContent = `${state.selected.size} selezionate`;
  const pageIds = state.items.map((x) => Number(x.id));
  $("selectPage").checked = pageIds.length > 0 && pageIds.every((id) => state.selected.has(id));
}

function updatePager() {
  const page = Math.floor(state.offset / state.limit) + 1;
  const pages = Math.max(1, Math.ceil(state.total / state.limit));
  $("pageInfo").textContent = `Pagina ${page} / ${pages}`;
  $("prevPage").disabled = state.offset <= 0;
  $("nextPage").disabled = state.offset + state.limit >= state.total;
}

function selectedIds() {
  return Array.from(state.selected);
}

async function bulkPost(path, body, label) {
  const ids = selectedIds();
  if (!ids.length) return alert("Seleziona almeno una offerta.");

  const res = await api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ offer_ids: ids, create_alias: true, ...body }),
  });

  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  alert(`${label}\n${JSON.stringify(data, null, 2)}`);
  state.selected.clear();
  await loadFlyers();
  await loadOffers();
}

async function associateOffer(offerId, productId) {
  const res = await api(`/admin/flyer-offers-page/offers/${offerId}/associate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, create_alias: true }),
  });
  if (!res.ok) return alert(await readError(res));
  state.selected.delete(Number(offerId));
  await loadOffers();
}

async function createOfferProduct(offerId) {
  if (!confirm("Creare un nuovo Product da questa offerta?")) return;
  const res = await api(`/admin/flyer-offers-page/offers/${offerId}/create-product`, { method: "POST" });
  if (!res.ok) return alert(await readError(res));
  state.selected.delete(Number(offerId));
  await loadOffers();
}

async function rejectOffer(offerId) {
  const res = await api(`/admin/flyer-offers-page/offers/${offerId}/reject`, { method: "POST" });
  if (!res.ok) return alert(await readError(res));
  state.selected.delete(Number(offerId));
  await loadOffers();
}

async function manualSearch(offerId) {
  const offer = state.items.find((x) => Number(x.id) === Number(offerId));
  const q = prompt("Cerca prodotto:", offer?.raw_name || "");
  if (!q) return;

  const res = await api(`/admin/flyer-offers-page/products/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) return alert(await readError(res));

  const rows = await res.json();
  if (!rows.length) return alert("Nessun prodotto trovato.");

  const message = rows.map((p, i) => `${i + 1}. #${p.id} ${p.name} (${p.supermarket_name || ""})`).join("\n");
  const selected = Number(prompt(`Scegli numero prodotto:\n${message}`));
  if (!selected || !rows[selected - 1]) return;

  await associateOffer(offerId, rows[selected - 1].id);
}

document.addEventListener("DOMContentLoaded", () => {
  $("refreshFlyers").addEventListener("click", loadFlyers);

  $("matchFilter").addEventListener("change", (e) => {
    state.match = e.target.value;
    state.offset = 0;
    state.selected.clear();
    loadOffers();
  });

  $("statusFilter").addEventListener("change", (e) => {
    state.status = e.target.value;
    state.offset = 0;
    state.selected.clear();
    loadOffers();
  });

  $("selectPage").addEventListener("change", (e) => {
    state.items.forEach((item) => {
      const id = Number(item.id);
      if (e.target.checked) state.selected.add(id);
      else state.selected.delete(id);
    });
    renderOffers();
  });

  $("prevPage").addEventListener("click", () => {
    state.offset = Math.max(0, state.offset - state.limit);
    state.selected.clear();
    loadOffers();
  });

  $("nextPage").addEventListener("click", () => {
    if (state.offset + state.limit < state.total) {
      state.offset += state.limit;
      state.selected.clear();
      loadOffers();
    }
  });

  $("approveAuto").addEventListener("click", async () => {
    if (!state.flyerId) return alert("Seleziona un volantino.");
    const res = await api(`/admin/flyer-offers-page/flyers/${state.flyerId}/approve-auto`, { method: "POST" });
    if (!res.ok) return alert(await readError(res));
    const data = await res.json();
    alert(`Auto-match approvati: ${data.approved}`);
    await loadFlyers();
    await loadOffers();
  });

  $("publishFlyer").addEventListener("click", async () => {
    if (!state.flyerId) return alert("Seleziona un volantino.");
    const res = await api(`/admin/flyer-offers-page/flyers/${state.flyerId}/publish`, { method: "POST" });
    if (!res.ok) return alert(await readError(res));
    const data = await res.json();
    alert(`Offerte pubblicate: ${data.published}`);
    await loadFlyers();
    await loadOffers();
  });

  $("repairImages").addEventListener("click", async () => {
    if (!state.flyerId) return alert("Seleziona un volantino.");
    if (!confirm("Riparare immagini prodotto usando i crop delle offerte?")) return;
    const res = await api("/admin/flyer-offers-page/repair-product-images", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ flyer_id: state.flyerId }),
    });
    if (!res.ok) return alert(await readError(res));
    const data = await res.json();
    alert(`Controllate ${data.checked}, riparate ${data.repaired}, saltate ${data.skipped}`);
    await loadOffers();
  });

  $("bulkApprove").addEventListener("click", () =>
    bulkPost("/admin/flyer-offers-page/offers/bulk-approve", {}, "Approvazione completata.")
  );

  $("bulkAssociate").addEventListener("click", () => {
    if (confirm("Associare le selezionate al prodotto suggerito?")) {
      bulkPost("/admin/flyer-offers-page/offers/bulk-associate-suggested", {}, "Associazione completata.");
    }
  });

  $("bulkCreate").addEventListener("click", () => {
    if (confirm("Creare prodotti nuovi per le offerte selezionate?")) {
      bulkPost("/admin/flyer-offers-page/offers/bulk-create-products", {}, "Creazione prodotti completata.");
    }
  });

  $("bulkReject").addEventListener("click", () => {
    if (confirm("Scartare le offerte selezionate?")) {
      bulkPost("/admin/flyer-offers-page/offers/bulk-reject", {}, "Scarto completato.");
    }
  });

  $("offersList").addEventListener("change", (e) => {
    const check = e.target.closest("[data-check]");
    if (!check) return;
    const id = Number(check.dataset.check);
    if (check.checked) state.selected.add(id);
    else state.selected.delete(id);
    updateSelection();
  });

  $("offersList").addEventListener("click", async (e) => {
    const imageBtn = e.target.closest(".image-btn");
    if (imageBtn) {
      const url = imageBtn.dataset.img;
      imageBtn.outerHTML = `<img class="thumb" loading="lazy" src="${esc(url)}" alt="" />`;
      return;
    }

    const btn = e.target.closest("[data-action]");
    if (!btn) return;

    const row = btn.closest("[data-id]");
    const offerId = Number(row.dataset.id);

    if (btn.dataset.action === "associate") return associateOffer(offerId, Number(btn.dataset.product));
    if (btn.dataset.action === "create") return createOfferProduct(offerId);
    if (btn.dataset.action === "reject") return rejectOffer(offerId);
    if (btn.dataset.action === "search") return manualSearch(offerId);
  });

  loadFlyers();
});
