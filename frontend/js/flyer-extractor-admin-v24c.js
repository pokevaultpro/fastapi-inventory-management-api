import CONFIG from "./config.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

const state = {
  supermarkets: [],
  recent: [],
};

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));

function authHeaders(extra = {}) {
  return { Authorization: `Bearer ${localStorage.getItem("token")}`, ...extra };
}

async function api(path, options = {}) {
  const res = await fetch(`${CONFIG.API_BASE_URL}${path}`, {
    ...options,
    headers: { ...authHeaders(options.headers || {}) },
  });

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
    return res.statusText || "Errore sconosciuto";
  }
}

function absoluteUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${CONFIG.API_BASE_URL}${path}`;
}

function findAdminContainer() {
  return (
    document.querySelector(".admin-desktop") ||
    document.querySelector(".admin-content") ||
    document.querySelector("main") ||
    document.body
  );
}

function findTabsContainer() {
  return (
    document.querySelector(".admin-tabs") ||
    document.querySelector(".admin-nav") ||
    document.querySelector("[data-admin-tabs]") ||
    document.querySelector(".tabs")
  );
}

function deactivateExistingPanels() {
  document.querySelectorAll(".admin-tab").forEach((tab) => tab.classList.remove("active"));
  document.querySelectorAll(".admin-panel").forEach((panel) => panel.classList.remove("active"));
}

function activateFlyerPanel() {
  deactivateExistingPanels();
  document.querySelectorAll("[data-admin-tab='flyer-extractor']").forEach((tab) => tab.classList.add("active"));
  const panel = document.getElementById("panel-flyer-extractor");
  if (panel) {
    panel.classList.add("active");
    panel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  loadRecent();
}

function ensureTab() {
  const tabs = findTabsContainer();
  if (!tabs) return false;

  let tab = tabs.querySelector("[data-admin-tab='flyer-extractor']");
  if (!tab) {
    tab = document.createElement("button");
    tab.type = "button";
    tab.className = "admin-tab";
    tab.dataset.adminTab = "flyer-extractor";
    tab.textContent = "Volantini";
    tabs.appendChild(tab);
  }

  tab.addEventListener("click", activateFlyerPanel);
  return true;
}

function createPanelHtml() {
  return `
    <div class="panel-head flyer-panel-head">
      <div>
        <h2>Flyer Image Extractor</h2>
        <p>Carica PDF o ZIP immagini. L'app crea solo immagini pagina, contact sheet e ZIP. Nessun OCR e nessuna importazione prodotti automatica.</p>
      </div>
      <button type="button" class="primary-btn" id="flyer-health-btn">Controlla extractor</button>
    </div>

    <div class="flyer-status-card" id="flyer-status-card">
      <strong>Backend extractor</strong>
      <span>In attesa di controllo...</span>
    </div>

    <div class="flyer-extractor-grid">
      <section class="flyer-box flyer-box-wide">
        <h3>1. Dati volantino</h3>
        <div class="flyer-form-grid">
          <label>Titolo
            <input id="flyer-title" placeholder="Es. Conad Super Risparmio">
          </label>
          <label>Supermercato
            <select id="flyer-supermarket">
              <option value="">Nessuno / da decidere</option>
            </select>
          </label>
          <label>Valido da
            <input id="flyer-valid-from" type="date">
          </label>
          <label>Valido fino a
            <input id="flyer-valid-to" type="date">
          </label>
        </div>
      </section>

      <section class="flyer-box">
        <h3>2. PDF volantino</h3>
        <p>Per Conad/Coop/MD quando hai un PDF vero.</p>
        <div class="flyer-upload-row">
          <input id="flyer-pdf" type="file" accept="application/pdf">
          <button type="button" class="primary-btn" id="flyer-upload-pdf-btn">Estrai pagine PDF</button>
        </div>
      </section>

      <section class="flyer-box">
        <h3>3. ZIP immagini</h3>
        <p>Per Lidl o siti senza PDF: carichi qui lo ZIP immagini pagina preparato fuori.</p>
        <div class="flyer-upload-row">
          <input id="flyer-images-zip" type="file" accept=".zip,application/zip">
          <button type="button" class="primary-btn" id="flyer-upload-zip-btn">Importa immagini</button>
        </div>
      </section>

      <section class="flyer-box flyer-box-wide">
        <h3>4. URL diretto PDF/immagine</h3>
        <p>Funziona solo se il link punta direttamente a un PDF o a una immagine. Non legge siti HTML.</p>
        <div class="flyer-upload-row flyer-url-row">
          <input id="flyer-url" placeholder="https://.../volantino.pdf">
          <button type="button" class="ghost-btn" id="flyer-url-btn">Scarica da URL</button>
        </div>
      </section>
    </div>

    <section class="flyer-result" id="flyer-result">
      <div class="empty-state">Nessuna estrazione ancora.</div>
    </section>

    <section class="flyer-box flyer-recent">
      <div class="flyer-recent-head">
        <h3>Estrazioni recenti</h3>
        <button type="button" class="ghost-btn" id="flyer-refresh-recent-btn">Aggiorna</button>
      </div>
      <div id="flyer-recent-list" class="flyer-recent-list"></div>
    </section>
  `;
}

function ensurePanel() {
  let panel = document.getElementById("panel-flyer-extractor");
  if (!panel) {
    panel = document.createElement("section");
    panel.className = "admin-panel flyer-extractor-panel";
    panel.id = "panel-flyer-extractor";
    panel.innerHTML = createPanelHtml();

    const container = findAdminContainer();
    container.appendChild(panel);
  }

  const hasTabs = ensureTab();

  // If we do not find a real admin tab area, show it directly inside admin page.
  if (!hasTabs) {
    panel.classList.add("active", "flyer-visible-fallback");
  }

  bindEvents();
  return panel;
}

function bindEvents() {
  document.getElementById("flyer-health-btn")?.addEventListener("click", checkHealth);
  document.getElementById("flyer-upload-pdf-btn")?.addEventListener("click", uploadPdf);
  document.getElementById("flyer-upload-zip-btn")?.addEventListener("click", uploadZip);
  document.getElementById("flyer-url-btn")?.addEventListener("click", importUrl);
  document.getElementById("flyer-refresh-recent-btn")?.addEventListener("click", loadRecent);
}

function commonFormData() {
  const data = new FormData();
  const title = document.getElementById("flyer-title")?.value.trim();
  const supermarketId = document.getElementById("flyer-supermarket")?.value;
  const validFrom = document.getElementById("flyer-valid-from")?.value;
  const validTo = document.getElementById("flyer-valid-to")?.value;

  if (title) data.append("title", title);
  if (supermarketId) data.append("supermarket_id", supermarketId);
  if (validFrom) data.append("valid_from", validFrom);
  if (validTo) data.append("valid_to", validTo);

  return data;
}

function commonJson() {
  const title = document.getElementById("flyer-title")?.value.trim();
  const supermarketId = document.getElementById("flyer-supermarket")?.value;
  const validFrom = document.getElementById("flyer-valid-from")?.value;
  const validTo = document.getElementById("flyer-valid-to")?.value;

  return {
    title: title || null,
    supermarket_id: supermarketId ? Number(supermarketId) : null,
    valid_from: validFrom || null,
    valid_to: validTo || null,
  };
}

function setLoading(message) {
  document.getElementById("flyer-result").innerHTML = `
    <div class="flyer-loading">
      <div class="spinner"></div>
      <strong>${esc(message)}</strong>
      <small>Nessun OCR: sto solo creando immagini pagina.</small>
    </div>
  `;
}

function showError(message) {
  document.getElementById("flyer-result").innerHTML = `
    <div class="flyer-error">
      <strong>Errore</strong>
      <p>${esc(message)}</p>
    </div>
  `;
}

async function checkHealth() {
  const box = document.getElementById("flyer-status-card");
  const res = await api("/admin/flyer-extractor/health");

  if (!res.ok) {
    box.className = "flyer-status-card error";
    box.innerHTML = `<strong>Extractor non disponibile</strong><span>${esc(await readError(res))}</span>`;
    return;
  }

  const data = await res.json();
  box.className = "flyer-status-card ok";
  box.innerHTML = `
    <strong>Extractor backend attivo</strong>
    <span>PyMuPDF: ${data.pymupdf_available ? "OK" : "MISSING"} · Pillow: ${data.pillow_available ? "OK" : "MISSING"} · No OCR: ${data.no_ocr ? "sì" : "no"}</span>
  `;
}

async function loadSupermarkets() {
  const select = document.getElementById("flyer-supermarket");
  if (!select) return;

  const endpoints = ["/admin/supermarkets", "/supermarket"];
  for (const endpoint of endpoints) {
    try {
      const res = await api(endpoint);
      if (res.ok) {
        state.supermarkets = await res.json();
        break;
      }
    } catch {}
  }

  select.innerHTML = `<option value="">Nessuno / da decidere</option>` + state.supermarkets.map((sm) => `
    <option value="${sm.id}">${esc(sm.name)}</option>
  `).join("");
}

async function uploadPdf() {
  const file = document.getElementById("flyer-pdf")?.files?.[0];
  if (!file) return alert("Seleziona un PDF.");

  const form = commonFormData();
  form.append("file", file);

  setLoading("Estraggo pagine dal PDF...");
  const res = await api("/admin/flyer-extractor/pdf", {
    method: "POST",
    body: form,
    headers: {},
  });

  if (!res.ok) return showError(await readError(res));
  renderResult(await res.json());
  loadRecent();
}

async function uploadZip() {
  const file = document.getElementById("flyer-images-zip")?.files?.[0];
  if (!file) return alert("Seleziona uno ZIP di immagini.");

  const form = commonFormData();
  form.append("file", file);

  setLoading("Importo immagini dallo ZIP...");
  const res = await api("/admin/flyer-extractor/images-zip", {
    method: "POST",
    body: form,
    headers: {},
  });

  if (!res.ok) return showError(await readError(res));
  renderResult(await res.json());
  loadRecent();
}

async function importUrl() {
  const url = document.getElementById("flyer-url")?.value.trim();
  if (!url) return alert("Inserisci un URL diretto PDF/immagine.");

  const payload = { ...commonJson(), url };

  setLoading("Scarico URL diretto...");
  const res = await api("/admin/flyer-extractor/url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) return showError(await readError(res));
  renderResult(await res.json());
  loadRecent();
}

function renderResult(manifest) {
  const pages = manifest.pages || [];

  document.getElementById("flyer-result").innerHTML = `
    <div class="flyer-result-head">
      <div>
        <p class="flyer-kicker">Estrazione completata</p>
        <h3>${esc(manifest.title)}</h3>
        <p>${pages.length} pagine · ${esc(manifest.valid_from || "inizio n/d")} → ${esc(manifest.valid_to || "fine n/d")}</p>
      </div>
      <div class="flyer-actions">
        <a class="primary-btn" href="${absoluteUrl(manifest.zip_url)}" target="_blank" rel="noreferrer">Scarica ZIP pagine</a>
        <a class="ghost-btn" href="${absoluteUrl(manifest.manifest_url)}" target="_blank" rel="noreferrer">Apri manifest</a>
        <button type="button" class="ghost-btn" id="copy-manifest-btn">Copia manifest</button>
      </div>
    </div>

    ${manifest.contact_sheet_url ? `
      <a class="flyer-contact-sheet" href="${absoluteUrl(manifest.contact_sheet_url)}" target="_blank" rel="noreferrer">
        <img src="${absoluteUrl(manifest.contact_sheet_url)}" alt="Contact sheet">
      </a>
    ` : ""}

    <div class="flyer-pages-grid">
      ${pages.map((page) => `
        <a class="flyer-page-card" href="${absoluteUrl(page.image_url)}" target="_blank" rel="noreferrer">
          <img src="${absoluteUrl(page.image_url)}" alt="Pagina ${page.page_number}">
          <span>Pagina ${page.page_number}</span>
        </a>
      `).join("")}
    </div>
  `;

  document.getElementById("copy-manifest-btn")?.addEventListener("click", async () => {
    await navigator.clipboard.writeText(JSON.stringify(manifest, null, 2));
    alert("Manifest copiato.");
  });
}

async function loadRecent() {
  const box = document.getElementById("flyer-recent-list");
  if (!box) return;

  const res = await api("/admin/flyer-extractor/recent");
  if (!res.ok) {
    box.innerHTML = `<div class="empty-state">Errore recenti: ${esc(await readError(res))}</div>`;
    return;
  }

  const rows = await res.json();
  state.recent = rows;

  if (!rows.length) {
    box.innerHTML = `<div class="empty-state">Nessuna estrazione recente.</div>`;
    return;
  }

  box.innerHTML = rows.map((item) => `
    <button type="button" class="flyer-recent-card" data-id="${esc(item.extraction_id)}">
      <strong>${esc(item.title)}</strong>
      <small>${item.pages_count || 0} pagine · ${esc(item.source_type)}</small>
    </button>
  `).join("");

  box.querySelectorAll("[data-id]").forEach((button) => {
    button.addEventListener("click", async () => {
      const res = await api(`/admin/flyer-extractor/${button.dataset.id}/manifest`);
      if (!res.ok) return alert(await readError(res));
      renderResult(await res.json());
      document.getElementById("flyer-result")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  ensurePanel();
  await checkHealth();
  await loadSupermarkets();
  await loadRecent();
});
