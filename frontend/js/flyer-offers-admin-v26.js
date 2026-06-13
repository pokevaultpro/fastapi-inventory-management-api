import CONFIG from "./config.js";

const state = {
  flyers: [],
  selectedFlyerId: null,
  offers: [],
  statusFilter: "",
  matchFilter: "",
};

const token = () => localStorage.getItem("token");
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));
const euro = (v) => Number(v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });

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
        <p>Importa lo ZIP prodotti+crop in bozza, associa automaticamente ai prodotti esistenti e pubblica solo le offerte.</p>
      </div>
      <button type="button" class="primary-btn" id="flyer-offers-refresh">Aggiorna</button>
    </div>

    <section class="flyer-offers-upload">
      <div>
        <h3>Import ZIP in bozza</h3>
        <p>Non crea prodotti subito. Crea offerte draft, con auto-match dove possibile.</p>
      </div>
      <input id="flyer-offers-zip" type="file" accept=".zip,application/zip">
      <input id="flyer-offers-import-name" placeholder="Nome import opzionale">
      <button type="button" class="primary-btn" id="flyer-offers-import-btn">Importa bozza</button>
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
          <button type="button" class="primary-btn" id="flyer-offers-publish">Pubblica approvate</button>
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
    loadOffers();
  });
  document.getElementById("flyer-offers-status-filter")?.addEventListener("change", (e) => {
    state.statusFilter = e.target.value;
    loadOffers();
  });
  document.getElementById("flyer-offers-approve-auto")?.addEventListener("click", approveAuto);
  document.getElementById("flyer-offers-publish")?.addEventListener("click", publishFlyer);
}

async function importZip() {
  const file = document.getElementById("flyer-offers-zip")?.files?.[0];
  if (!file) return alert("Seleziona uno ZIP.");

  const form = new FormData();
  form.append("file", file);
  const importName = document.getElementById("flyer-offers-import-name").value.trim();
  if (importName) form.append("import_name", importName);

  const res = await api("/admin/flyer-offers/import-zip", { method: "POST", body: form });
  if (!res.ok) return alert(await readError(res));

  const data = await res.json();
  alert(`Import completato: ${data.created_draft_offers} offerte draft, ${data.auto_matched} auto-match, ${data.needs_review} da controllare, ${data.new_product_suggestion} nuovi.`);
  state.selectedFlyerId = data.flyer_id;
  await loadFlyers();
  await loadOffers();
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
    <button type="button" class="flyer-mini-card ${Number(state.selectedFlyerId) === Number(f.id) ? "active" : ""}" data-id="${f.id}">
      <strong>${esc(f.title || f.retailer)}</strong>
      <small>${esc(f.retailer)} · ${esc(f.valid_from || "?")} → ${esc(f.valid_to || "?")}</small>
      <span>${f.offers_count || 0} offerte · ${f.auto_matched_count || 0} auto · ${f.needs_review_count || 0} dubbi · ${f.new_product_count || 0} nuovi</span>
    </button>
  `).join("");

  box.querySelectorAll("[data-id]").forEach(btn => {
    btn.addEventListener("click", async () => {
      state.selectedFlyerId = Number(btn.dataset.id);
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

  const res = await api(`/admin/flyer-offers/flyers/${state.selectedFlyerId}/offers?${params.toString()}`);
  if (!res.ok) return alert(await readError(res));
  state.offers = await res.json();
  renderOffers();
}

function matchLabel(offer) {
  if (String(offer.match_status || "").startsWith("auto_matched")) return "auto";
  if (offer.match_status === "needs_review") return "controlla";
  if (offer.match_status === "new_product_suggestion") return "nuovo";
  if (offer.match_status === "manual_matched") return "manuale";
  if (offer.match_status === "created_product") return "creato";
  return offer.match_status || "n/d";
}

function renderOffers() {
  const box = document.getElementById("flyer-offers-list");
  if (!state.offers.length) {
    box.innerHTML = `<div class="empty-state">Nessuna offerta con questi filtri.</div>`;
    return;
  }

  box.innerHTML = state.offers.map(offer => `
    <article class="offer-review-card" data-offer-id="${offer.id}">
      <img src="${offer.image || "/static/images/placeholder.jpg"}" onerror="this.src='/static/images/placeholder.jpg'">
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
        ${offer.suggested_product_id ? `<button type="button" class="ghost-btn" data-associate="${offer.id}" data-product="${offer.suggested_product_id}">Associa suggerito</button>` : ""}
        <button type="button" class="ghost-btn" data-search="${offer.id}">Cerca prodotto</button>
        <button type="button" class="primary-btn" data-create="${offer.id}">Crea prodotto</button>
        <button type="button" class="delete-btn" data-reject="${offer.id}">Scarta</button>
      </div>
    </article>
  `).join("");

  box.querySelectorAll("[data-associate]").forEach(btn => btn.addEventListener("click", () => associateOffer(Number(btn.dataset.associate), Number(btn.dataset.product))));
  box.querySelectorAll("[data-create]").forEach(btn => btn.addEventListener("click", () => createProduct(Number(btn.dataset.create))));
  box.querySelectorAll("[data-reject]").forEach(btn => btn.addEventListener("click", () => rejectOffer(Number(btn.dataset.reject))));
  box.querySelectorAll("[data-search]").forEach(btn => btn.addEventListener("click", () => manualSearch(Number(btn.dataset.search))));
}

async function associateOffer(offerId, productId) {
  const res = await api(`/admin/flyer-offers/offers/${offerId}/associate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_id: productId, create_alias: true }),
  });
  if (!res.ok) return alert(await readError(res));
  await loadOffers();
}

async function createProduct(offerId) {
  if (!confirm("Creare un nuovo prodotto dal dato del volantino?")) return;
  const res = await api(`/admin/flyer-offers/offers/${offerId}/create-product`, { method: "POST" });
  if (!res.ok) return alert(await readError(res));
  await loadOffers();
}

async function rejectOffer(offerId) {
  const res = await api(`/admin/flyer-offers/offers/${offerId}/reject`, { method: "POST" });
  if (!res.ok) return alert(await readError(res));
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

document.addEventListener("DOMContentLoaded", () => {
  ensurePanel();
  loadFlyers();
});
