import CONFIG from "./config.js";

const selected = new Set();
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, m => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[m]));
const token = () => localStorage.getItem("token");

function mediaUrl(path) {
  if (!path) return `${CONFIG.API_BASE_URL}/static/images/placeholder.jpg`;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  if (path.startsWith("/static/")) return `${CONFIG.API_BASE_URL}${path}`;
  if (path.startsWith("static/")) return `${CONFIG.API_BASE_URL}/${path}`;
  return path;
}

async function api(path, options = {}) {
  const headers = { Authorization: `Bearer ${token()}`, ...(options.headers || {}) };
  if (options.body && !(options.body instanceof FormData)) headers["Content-Type"] = "application/json";
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
  } catch { return res.statusText || "Errore"; }
}

function ensureBulkToolbar() {
  const list = document.getElementById("flyer-offers-list");
  if (!list || document.getElementById("flyer-bulk-toolbar-v26e")) return;
  const bar = document.createElement("div");
  bar.id = "flyer-bulk-toolbar-v26e";
  bar.className = "flyer-bulk-toolbar";
  bar.innerHTML = `
    <label class="select-all-row"><input type="checkbox" id="bulk-select-visible-v26e"> Seleziona visibili</label>
    <span id="bulk-selected-count-v26e">0 selezionate</span>
    <button type="button" class="ghost-btn" id="bulk-approve-v26e">Approva selezionate</button>
    <button type="button" class="ghost-btn" id="bulk-associate-v26e">Associa suggeriti selezionati</button>
    <button type="button" class="primary-btn" id="bulk-create-v26e">Crea prodotti selezionati</button>
    <button type="button" class="delete-btn" id="bulk-reject-v26e">Scarta selezionate</button>
    <button type="button" class="ghost-btn" id="repair-images-v26e">Ripara immagini prodotti</button>
  `;
  list.parentNode.insertBefore(bar, list);
  document.getElementById("bulk-select-visible-v26e").addEventListener("change", e => {
    document.querySelectorAll(".offer-review-card[data-offer-id]").forEach(card => {
      const id = Number(card.dataset.offerId);
      if (e.target.checked) selected.add(id); else selected.delete(id);
    });
    enhanceCards();
  });
  document.getElementById("bulk-approve-v26e").addEventListener("click", () => bulkPost("/admin/flyer-offers/v26e/offers/bulk-approve", "Approvazione completata"));
  document.getElementById("bulk-associate-v26e").addEventListener("click", () => {
    if (confirm("Associare le selezionate ai prodotti suggeriti e approvarle?")) bulkPost("/admin/flyer-offers/v26e/offers/bulk-associate-suggested", "Associazione completata");
  });
  document.getElementById("bulk-create-v26e").addEventListener("click", () => {
    if (confirm("Creare un Product per ogni offerta selezionata?")) bulkPost("/admin/flyer-offers/v26e/offers/bulk-create-products", "Creazione prodotti completata");
  });
  document.getElementById("bulk-reject-v26e").addEventListener("click", () => {
    if (confirm("Scartare le offerte selezionate?")) bulkPost("/admin/flyer-offers/v26e/offers/bulk-reject", "Scarto completato");
  });
  document.getElementById("repair-images-v26e").addEventListener("click", repairImages);
}

function updateCount() {
  const el = document.getElementById("bulk-selected-count-v26e");
  if (el) el.textContent = `${selected.size} selezionate`;
}

function enhanceCards() {
  ensureBulkToolbar();
  document.querySelectorAll(".offer-review-card[data-offer-id]").forEach(card => {
    const id = Number(card.dataset.offerId);
    if (!card.querySelector(".offer-check-v26e")) {
      const label = document.createElement("label");
      label.className = "offer-check-v26e";
      label.innerHTML = `<input type="checkbox" data-v26e-check="${id}">`;
      card.prepend(label);
      label.querySelector("input").addEventListener("change", e => {
        if (e.target.checked) selected.add(id); else selected.delete(id);
        updateCount();
      });
    }
    const chk = card.querySelector("[data-v26e-check]");
    if (chk) chk.checked = selected.has(id);
    card.querySelectorAll("img").forEach(img => {
      const raw = img.getAttribute("src") || "";
      if (raw.startsWith("/static/") || raw.startsWith("static/")) img.setAttribute("src", mediaUrl(raw));
      img.onerror = () => { img.src = `${CONFIG.API_BASE_URL}/static/images/placeholder.jpg`; };
    });
    card.querySelectorAll("[data-create]").forEach(btn => {
      if (btn.dataset.v26eBound) return;
      btn.dataset.v26eBound = "1";
      btn.addEventListener("click", async ev => {
        ev.preventDefault(); ev.stopImmediatePropagation();
        if (!confirm("Creare un nuovo prodotto con immagine crop corretta?")) return;
        const offerId = Number(btn.dataset.create);
        const res = await api(`/admin/flyer-offers/v26e/offers/${offerId}/create-product`, { method: "POST" });
        if (!res.ok) return alert(await readError(res));
        selected.delete(offerId);
        alert("Prodotto creato con immagine aggiornata.");
        document.getElementById("flyer-offers-refresh")?.click();
      }, true);
    });
    card.querySelectorAll("[data-associate]").forEach(btn => {
      if (btn.dataset.v26eBound) return;
      btn.dataset.v26eBound = "1";
      btn.addEventListener("click", async ev => {
        ev.preventDefault(); ev.stopImmediatePropagation();
        const offerId = Number(btn.dataset.associate);
        const productId = Number(btn.dataset.product);
        const res = await api(`/admin/flyer-offers/v26e/offers/${offerId}/associate`, {
          method: "POST",
          body: JSON.stringify({ product_id: productId, create_alias: true }),
        });
        if (!res.ok) return alert(await readError(res));
        selected.delete(offerId);
        alert("Offerta associata.");
        document.getElementById("flyer-offers-refresh")?.click();
      }, true);
    });
  });
  updateCount();
}

async function bulkPost(path, label) {
  const ids = [...selected];
  if (!ids.length) return alert("Seleziona almeno una offerta.");
  const res = await api(path, { method: "POST", body: JSON.stringify({ offer_ids: ids, create_alias: true }) });
  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  selected.clear();
  alert(`${label}:\n${JSON.stringify(data, null, 2)}`);
  document.getElementById("flyer-offers-refresh")?.click();
}

async function repairImages() {
  if (!confirm("Riparare immagini dei prodotti già creati/associati usando i crop del volantino?")) return;
  const active = document.querySelector(".flyer-mini-card.active");
  const flyerId = active ? Number(active.dataset.id) : null;
  const res = await api("/admin/flyer-offers/v26e/repair-product-images", {
    method: "POST",
    body: JSON.stringify({ flyer_id: flyerId }),
  });
  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  alert(`Riparazione immagini: ${data.repaired} aggiornate, ${data.skipped} saltate, ${data.checked} controllate.`);
}

const observer = new MutationObserver(enhanceCards);
observer.observe(document.documentElement, { childList: true, subtree: true });
document.addEventListener("DOMContentLoaded", enhanceCards);
setTimeout(enhanceCards, 800);
