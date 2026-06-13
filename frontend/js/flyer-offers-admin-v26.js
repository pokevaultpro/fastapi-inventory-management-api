import CONFIG from "./config.js";

const state = {
  flyers: [],
  selectedFlyerId: null,
  offers: [],
  statusFilter: "",
  matchFilter: "",
  selectedOfferIds: new Set(),
  visibleLimit: 40,
};

const PLACEHOLDER_IMG =
  "data:image/svg+xml;charset=UTF-8," +
  encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="180" height="180" viewBox="0 0 180 180">
      <rect width="180" height="180" rx="22" fill="#f1f5f9"/>
      <text x="90" y="84" text-anchor="middle" font-family="Arial" font-size="15" font-weight="700" fill="#64748b">no image</text>
      <text x="90" y="108" text-anchor="middle" font-family="Arial" font-size="11" fill="#94a3b8">flyer offer</text>
    </svg>
  `);

const token = () => localStorage.getItem("token");
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
const euro = (v) => Number(v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });

function mediaUrl(path) {
  if (!path) return PLACEHOLDER_IMG;
  const value = String(path).trim();
  if (!value || value.toLowerCase().includes("placeholder")) return PLACEHOLDER_IMG;
  if (value.startsWith("data:")) return value;
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  if (value.startsWith("/static/")) return `${CONFIG.API_BASE_URL}${value}`;
  if (value.startsWith("static/")) return `${CONFIG.API_BASE_URL}/${value}`;
  return value;
}

function safeImgError(img) {
  img.onerror = null;
  img.src = PLACEHOLDER_IMG;
}

async function api(path, options = {}) {
  const headers = { Authorization: `Bearer ${token()}`, ...(options.headers || {}) };
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
    if (typeof data.detail === "string") return data.detail;
    return JSON.stringify(data.detail || data);
  } catch {
    return res.statusText || "Errore";
  }
}

function ensurePanel() {
  if (document.getElementById("panel-flyer-offers")) return;

  const tabs = document.querySelector(".admin-tabs");
  const desktop = document.querySelector(".admin-desktop") || document.querySelector("main") || document.body;

  if (tabs && !tabs.querySelector("[data-admin-tab='flyer-offers']")) {
    const btn = document.createElement("button");
    btn.className = "admin-tab";
    btn.dataset.adminTab = "flyer-offers";
    btn.textContent = "Offerte volantini";
    tabs.appendChild(btn);
    btn.addEventListener("click", () => {
      document.querySelectorAll(".admin-tab").forEach(x => x.classList.toggle("active", x === btn));
      document.querySelectorAll(".admin-panel").forEach(p => p.classList.toggle("active", p.id === "panel-flyer-offers"));
      loadFlyers();
    });
  }

  const panel = document.createElement("section");
  panel.className = "admin-panel flyer-offers-panel";
  panel.id = "panel-flyer-offers";
  panel.innerHTML = `
    <div class="panel-head">
      <div>
        <h2>Offerte volantini</h2>
        <p>Importa lo ZIP in bozza, associa ai prodotti esistenti e pubblica solo le offerte. Versione hotfix: caricamento leggero anti-freeze.</p>
      </div>
      <button type="button" class="primary-btn" id="flyer-offers-refresh">Aggiorna</button>
    </div>

    <section class="flyer-offers-upload">
      <div>
        <h3>Import ZIP in bozza</h3>
        <p>Non crea prodotti subito. Le immagini sono caricate in lazy mode per non bloccare la pagina.</p>
      </div>
      <input id="flyer-offers-zip" type="file" accept=".zip,application/zip">
      <input id="flyer-offers-import-name" placeholder="Nome import opzionale">
      <button type="button" class="primary-btn" id="flyer-offers-import-btn">Importa bozza</button>
      <div id="flyer-offers-import-status" class="flyer-import-status"></div>
    </section>

    <div class="flyer-offers-layout">
      <aside class="flyer-list-box">
        <h3>Volantini</h3>
        <div id="flyer-offers-flyers-list"></div>
      </aside>

      <section class="flyer-offers-main">
        <div class="flyer-offers-toolbar">
          <select id="flyer-offers-match-filter">
            <option value="">Tutti i match</option>
            <option value="auto_matched">Auto-match</option>
            <option value="needs_review">Da controllare</option>
            <option value="new_product_suggestion">Nuovi prodotti</option>
          </select>
          <select id="flyer-offers-status-filter">
            <option value="">Tutti gli stati</option>
            <option value="draft">Draft</option>
            <option value="approved">Approvate</option>
            <option value="published">Pubblicate</option>
            <option value="rejected">Scartate</option>
          </select>
          <button type="button" class="ghost-btn" id="flyer-offers-approve-auto">Approva auto-match</button>
          <button type="button" class="ghost-btn" id="flyer-offers-repair-images">Ripara immagini prodotti</button>
          <button type="button" class="primary-btn" id="flyer-offers-publish">Pubblica approvate</button>
        </div>

        <div class="flyer-bulk-toolbar">
          <label class="select-all-row">
            <input type="checkbox" id="flyer-offers-select-visible">
            Seleziona visibili
          </label>
          <span id="flyer-selected-count">0 selezionate</span>
          <button type="button" class="ghost-btn" id="bulk-approve">Approva selezionate</button>
          <button type="button" class="ghost-btn" id="bulk-associate">Associa suggeriti selezionati</button>
          <button type="button" class="primary-btn" id="bulk-create">Crea prodotti selezionati</button>
          <button type="button" class="delete-btn" id="bulk-reject">Scarta selezionate</button>
        </div>

        <div id="flyer-offers-list" class="flyer-offers-list">
          <div class="empty-state">Seleziona un volantino.</div>
        </div>
      </section>
    </div>
  `;
  desktop.appendChild(panel);

  bindEvents();
}

function bindEvents() {
  document.getElementById("flyer-offers-refresh")?.addEventListener("click", loadFlyers);
  document.getElementById("flyer-offers-import-btn")?.addEventListener("click", importZip);
  document.getElementById("flyer-offers-match-filter")?.addEventListener("change", (e) => {
    state.matchFilter = e.target.value;
    state.visibleLimit = 40;
    state.selectedOfferIds.clear();
    loadOffers();
  });
  document.getElementById("flyer-offers-status-filter")?.addEventListener("change", (e) => {
    state.statusFilter = e.target.value;
    state.visibleLimit = 40;
    state.selectedOfferIds.clear();
    loadOffers();
  });
  document.getElementById("flyer-offers-approve-auto")?.addEventListener("click", approveAuto);
  document.getElementById("flyer-offers-publish")?.addEventListener("click", publishFlyer);
  document.getElementById("flyer-offers-repair-images")?.addEventListener("click", repairImages);
  document.getElementById("flyer-offers-select-visible")?.addEventListener("change", toggleSelectVisible);
  document.getElementById("bulk-approve")?.addEventListener("click", bulkApprove);
  document.getElementById("bulk-associate")?.addEventListener("click", bulkAssociateSuggested);
  document.getElementById("bulk-create")?.addEventListener("click", bulkCreateProducts);
  document.getElementById("bulk-reject")?.addEventListener("click", bulkReject);

  document.getElementById("flyer-offers-list")?.addEventListener("click", handleListClick);
  document.getElementById("flyer-offers-list")?.addEventListener("change", handleListChange);
  document.getElementById("flyer-offers-list")?.addEventListener("error", (event) => {
    if (event.target?.matches?.("img")) safeImgError(event.target);
  }, true);
}

function setImportStatus(message, busy = false) {
  const el = document.getElementById("flyer-offers-import-status");
  const btn = document.getElementById("flyer-offers-import-btn");
  if (el) {
    el.textContent = message || "";
    el.classList.toggle("busy", busy);
  }
  if (btn) {
    btn.disabled = busy;
    btn.textContent = busy ? "Import in corso..." : "Importa bozza";
  }
}

async function importZip() {
  const file = document.getElementById("flyer-offers-zip")?.files?.[0];
  if (!file) return alert("Seleziona uno ZIP.");

  const form = new FormData();
  form.append("file", file);
  const importName = document.getElementById("flyer-offers-import-name")?.value?.trim();
  if (importName) form.append("import_name", importName);

  setImportStatus(`Sto caricando ${file.name} (${(file.size / 1024 / 1024).toFixed(1)} MB). Attendi...`, true);

  try {
    const res = await api("/admin/flyer-offers/import-zip", { method: "POST", body: form });
    if (!res.ok) {
      setImportStatus("Import fallito.");
      return alert(await readError(res));
    }

    const data = await res.json();
    setImportStatus(`Completato in ${data.elapsed_seconds ?? "?"}s: ${data.created_draft_offers} offerte, ${data.auto_matched} auto, ${data.needs_review} da controllare, ${data.new_product_suggestion} nuovi.`);
    state.selectedFlyerId = data.flyer_id;
    state.selectedOfferIds.clear();
    state.visibleLimit = 40;
    await loadFlyers();
    await loadOffers();
  } catch (err) {
    setImportStatus("Import interrotto. Controlla se il volantino compare nella lista.");
    alert(err?.message || "Errore durante import.");
  } finally {
    const btn = document.getElementById("flyer-offers-import-btn");
    if (btn) {
      btn.disabled = false;
      btn.textContent = "Importa bozza";
    }
  }
}

async function loadFlyers() {
  const res = await api("/admin/flyer-offers/flyers");
  if (!res.ok) return;
  state.flyers = await res.json();
  renderFlyers();
}

function renderFlyers() {
  const box = document.getElementById("flyer-offers-flyers-list");
  if (!box) return;

  if (!state.flyers.length) {
    box.innerHTML = `<div class="empty-state">Nessun volantino importato.</div>`;
    return;
  }

  box.innerHTML = state.flyers.map(f => `
    <button type="button" class="flyer-mini-card ${Number(state.selectedFlyerId) === Number(f.id) ? "active" : ""}" data-flyer-id="${f.id}">
      <strong>${esc(f.title || f.retailer)}</strong>
      <small>${esc(f.retailer)} · ${esc(f.valid_from || "?")} → ${esc(f.valid_to || "?")}</small>
      <span>${f.offers_count || 0} offerte · ${f.auto_matched_count || 0} auto · ${f.needs_review_count || 0} dubbi · ${f.new_product_count || 0} nuovi</span>
    </button>
  `).join("");

  box.querySelectorAll("[data-flyer-id]").forEach(btn => {
    btn.addEventListener("click", async () => {
      state.selectedFlyerId = Number(btn.dataset.flyerId);
      state.selectedOfferIds.clear();
      state.visibleLimit = 40;
      renderFlyers();
      await loadOffers();
    });
  });
}

async function loadOffers() {
  if (!state.selectedFlyerId) return;

  const params = new URLSearchParams();
  if (state.matchFilter) params.set("match_status", state.matchFilter);
  if (state.statusFilter) params.set("status_filter", state.statusFilter);

  const list = document.getElementById("flyer-offers-list");
  if (list) list.innerHTML = `<div class="empty-state">Caricamento offerte...</div>`;

  const res = await api(`/admin/flyer-offers/flyers/${state.selectedFlyerId}/offers?${params.toString()}`);
  if (!res.ok) return alert(await readError(res));
  state.offers = await res.json();
  renderOffers();
}

function matchLabel(offer) {
  if (String(offer.match_status || "").startsWith("auto_matched")) return "auto";
  if (offer.match_status === "bulk_matched") return "bulk";
  if (offer.match_status === "needs_review") return "controlla";
  if (offer.match_status === "new_product_suggestion") return "nuovo";
  if (offer.match_status === "manual_matched") return "manuale";
  if (offer.match_status === "created_product") return "creato";
  return offer.match_status || "n/d";
}

function visibleOffers() {
  return state.offers.slice(0, state.visibleLimit);
}

function updateSelectedCount() {
  const el = document.getElementById("flyer-selected-count");
  if (el) el.textContent = `${state.selectedOfferIds.size} selezionate`;

  const all = document.getElementById("flyer-offers-select-visible");
  if (all) {
    const ids = visibleOffers().map(o => Number(o.id));
    all.checked = ids.length > 0 && ids.every(id => state.selectedOfferIds.has(id));
  }
}

function toggleSelectVisible(e) {
  const checked = e.target.checked;
  visibleOffers().forEach(offer => {
    const id = Number(offer.id);
    if (checked) state.selectedOfferIds.add(id);
    else state.selectedOfferIds.delete(id);
  });
  renderOffers();
}

function selectedIds() {
  return Array.from(state.selectedOfferIds);
}

function renderOffers() {
  const box = document.getElementById("flyer-offers-list");
  if (!box) return;

  if (!state.offers.length) {
    box.innerHTML = `<div class="empty-state">Nessuna offerta con questi filtri.</div>`;
    updateSelectedCount();
    return;
  }

  const rows = visibleOffers();
  const hidden = Math.max(0, state.offers.length - rows.length);

  box.innerHTML = `
    <div class="flyer-list-meta">
      Mostrate ${rows.length} di ${state.offers.length} offerte. Le immagini vengono caricate solo quando visibili.
    </div>
    ${rows.map(offer => `
      <article class="offer-review-card" data-offer-id="${offer.id}">
        <label class="offer-check">
          <input type="checkbox" data-check-offer="${offer.id}" ${state.selectedOfferIds.has(Number(offer.id)) ? "checked" : ""}>
        </label>
        <img loading="lazy" decoding="async" src="${mediaUrl(offer.image)}" alt="" />
        <div class="offer-review-info">
          <div class="offer-review-top">
            <span class="match-pill ${esc(offer.match_status || "")}">${esc(matchLabel(offer))} · ${Math.round(Number(offer.match_score || 0) * 100)}%</span>
            <span class="status-pill">${esc(offer.status)}</span>
          </div>
          <h3>${esc(offer.raw_name)}</h3>
          <p>${esc(offer.category || "Altro")} · pag. ${offer.flyer_page || "?"} · ${esc(offer.price_type || "fixed")} / ${esc(offer.price_unit || offer.unit || "pz")}</p>
          <strong>${euro(offer.offer_price)}</strong>
          <small>Match: ${esc(offer.product_name || offer.suggested_product_name || "nessuno")}</small>
        </div>
        <div class="offer-review-actions">
          ${offer.suggested_product_id ? `<button type="button" class="ghost-btn" data-action="associate" data-offer="${offer.id}" data-product="${offer.suggested_product_id}">Associa suggerito</button>` : ""}
          <button type="button" class="ghost-btn" data-action="search" data-offer="${offer.id}">Cerca prodotto</button>
          <button type="button" class="primary-btn" data-action="create" data-offer="${offer.id}">Crea prodotto</button>
          <button type="button" class="delete-btn" data-action="reject" data-offer="${offer.id}">Scarta</button>
        </div>
      </article>
    `).join("")}
    ${hidden ? `<button type="button" class="ghost-btn load-more-offers" data-action="load-more">Mostra altre 40 (${hidden} rimanenti)</button>` : ""}
  `;

  updateSelectedCount();
}

function handleListChange(event) {
  const checkbox = event.target.closest("[data-check-offer]");
  if (!checkbox) return;
  const id = Number(checkbox.dataset.checkOffer);
  if (checkbox.checked) state.selectedOfferIds.add(id);
  else state.selectedOfferIds.delete(id);
  updateSelectedCount();
}

async function handleListClick(event) {
  const btn = event.target.closest("[data-action]");
  if (!btn) return;

  const action = btn.dataset.action;
  if (action === "load-more") {
    state.visibleLimit += 40;
    renderOffers();
    return;
  }

  const offerId = Number(btn.dataset.offer);
  if (action === "associate") return associateOffer(offerId, Number(btn.dataset.product));
  if (action === "create") return createProduct(offerId);
  if (action === "reject") return rejectOffer(offerId);
  if (action === "search") return manualSearch(offerId);
}

async function associateOffer(offerId, productId) {
  const res = await api(`/admin/flyer-offers/offers/${offerId}/associate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, create_alias: true }),
  });
  if (!res.ok) return alert(await readError(res));
  state.selectedOfferIds.delete(Number(offerId));
  await loadOffers();
}

async function createProduct(offerId) {
  if (!confirm("Creare un nuovo prodotto dal dato del volantino?")) return;
  const res = await api(`/admin/flyer-offers/offers/${offerId}/create-product`, { method: "POST" });
  if (!res.ok) return alert(await readError(res));
  state.selectedOfferIds.delete(Number(offerId));
  await loadOffers();
}

async function rejectOffer(offerId) {
  const res = await api(`/admin/flyer-offers/offers/${offerId}/reject`, { method: "POST" });
  if (!res.ok) return alert(await readError(res));
  state.selectedOfferIds.delete(Number(offerId));
  await loadOffers();
}

async function manualSearch(offerId) {
  const offer = state.offers.find(o => Number(o.id) === Number(offerId));
  const q = prompt("Cerca prodotto nel database:", offer?.raw_name || "");
  if (!q) return;

  const res = await api(`/admin/flyer-offers/products/search?q=${encodeURIComponent(q)}`);
  if (!res.ok) return alert(await readError(res));
  const rows = await res.json();

  if (!rows.length) return alert("Nessun prodotto trovato.");

  const message = rows.map((p, i) => `${i + 1}. #${p.id} ${p.name} (${p.supermarket_name || ""})`).join("\n");
  const selected = Number(prompt(`Scegli numero prodotto:\n${message}`));
  if (!selected || !rows[selected - 1]) return;

  await associateOffer(offerId, rows[selected - 1].id);
}

async function approveAuto() {
  if (!state.selectedFlyerId) return;
  const res = await api(`/admin/flyer-offers/flyers/${state.selectedFlyerId}/approve-auto`, { method: "POST" });
  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  alert(`Approvate ${data.approved} offerte auto-match.`);
  await loadFlyers();
  await loadOffers();
}

async function publishFlyer() {
  if (!state.selectedFlyerId) return;
  const res = await api(`/admin/flyer-offers/flyers/${state.selectedFlyerId}/publish`, { method: "POST" });
  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  alert(`Pubblicate ${data.published} offerte.`);
  await loadFlyers();
  await loadOffers();
}

async function bulkPost(path, body, successLabel) {
  const ids = selectedIds();
  if (!ids.length) return alert("Seleziona almeno una offerta.");
  const res = await api(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ offer_ids: ids, create_alias: true, ...body }),
  });
  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  alert(`${successLabel}\n${JSON.stringify(data, null, 2)}`);
  state.selectedOfferIds.clear();
  await loadFlyers();
  await loadOffers();
}

async function bulkApprove() {
  await bulkPost("/admin/flyer-offers/offers/bulk-approve", {}, "Approvazione selezionate completata.");
}

async function bulkAssociateSuggested() {
  if (!confirm("Associare le offerte selezionate al prodotto suggerito e approvarle?")) return;
  await bulkPost("/admin/flyer-offers/offers/bulk-associate-suggested", {}, "Associazione suggeriti completata.");
}

async function bulkCreateProducts() {
  if (!confirm("Creare un nuovo Product per ogni offerta selezionata senza product_id?")) return;
  await bulkPost("/admin/flyer-offers/offers/bulk-create-products", {}, "Creazione prodotti completata.");
}

async function bulkReject() {
  if (!confirm("Scartare le offerte selezionate?")) return;
  await bulkPost("/admin/flyer-offers/offers/bulk-reject", {}, "Scarto completato.");
}

async function repairImages() {
  if (!confirm("Riparare le immagini dei prodotti già creati/associati usando i crop del volantino?")) return;
  const res = await api("/admin/flyer-offers/repair-product-images", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ flyer_id: state.selectedFlyerId || null }),
  });
  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  alert(`Riparazione immagini: ${data.repaired} aggiornate, ${data.skipped} saltate, ${data.checked} controllate.`);
  await loadOffers();
}

// Important: do NOT auto-load every offer on page opening.
// Only the flyer list is light; offers load only after selecting a flyer.
document.addEventListener("DOMContentLoaded", () => {
  ensurePanel();
  loadFlyers();
});
