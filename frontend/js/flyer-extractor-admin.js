import CONFIG from "./config.js";

const state = {
  supermarkets: [],
  recent: [],
  current: null,
};

function token() {
  return localStorage.getItem("token");
}

function headers(extra = {}) {
  return { Authorization: `Bearer ${token()}`, ...extra };
}

async function api(path, options = {}) {
  const res = await fetch(`${CONFIG.API_BASE_URL}${path}`, {
    ...options,
    headers: { ...headers(options.headers || {}) },
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

const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (m) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));

function injectPanel() {
  if (document.getElementById("panel-flyer-extractor")) return;

  const tabs = document.querySelector(".admin-tabs");
  const desktop = document.querySelector(".admin-desktop");
  if (!tabs || !desktop) return;

  const tab = document.createElement("button");
  tab.className = "admin-tab";
  tab.dataset.adminTab = "flyer-extractor";
  tab.textContent = "Volantini";
  tabs.appendChild(tab);

  const panel = document.createElement("section");
  panel.className = "admin-panel flyer-extractor-panel";
  panel.id = "panel-flyer-extractor";
  panel.innerHTML = `
    <div class="panel-head">
      <div>
        <h2>Flyer Image Extractor</h2>
        <p>Estrae solo le immagini delle pagine. Nessun OCR, nessuna importazione prodotti automatica.</p>
      </div>
      <button type="button" class="primary-btn" id="flyer-health-btn">Controlla extractor</button>
    </div>

    <div class="flyer-extractor-grid">
      <section class="flyer-box">
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
        <h3>2. Carica PDF</h3>
        <p>Per Conad/Coop/MD quando hai un PDF vero.</p>
        <div class="flyer-upload-row">
          <input id="flyer-pdf" type="file" accept="application/pdf">
          <button type="button" class="primary-btn" id="flyer-upload-pdf-btn">Estrai pagine PDF</button>
        </div>
      </section>

      <section class="flyer-box">
        <h3>3. Carica ZIP immagini</h3>
        <p>Per Lidl o siti senza PDF: io ti preparo uno ZIP immagini e tu lo carichi qui.</p>
        <div class="flyer-upload-row">
          <input id="flyer-images-zip" type="file" accept=".zip,application/zip">
          <button type="button" class="primary-btn" id="flyer-upload-zip-btn">Importa immagini</button>
        </div>
      </section>

      <section class="flyer-box">
        <h3>4. URL diretto PDF/immagine</h3>
        <p>Funziona solo se il link finisce direttamente a un PDF o immagine. Non legge siti HTML.</p>
        <div class="flyer-upload-row">
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
  desktop.appendChild(panel);

  tab.addEventListener("click", activateTab);
  document.getElementById("flyer-health-btn")?.addEventListener("click", checkHealth);
  document.getElementById("flyer-upload-pdf-btn")?.addEventListener("click", uploadPdf);
  document.getElementById("flyer-upload-zip-btn")?.addEventListener("click", uploadImagesZip);
  document.getElementById("flyer-url-btn")?.addEventListener("click", importUrl);
  document.getElementById("flyer-refresh-recent-btn")?.addEventListener("click", loadRecent);
}

function activateTab() {
  document.querySelectorAll(".admin-tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.adminTab === "flyer-extractor"));
  document.querySelectorAll(".admin-panel").forEach((panel) => panel.classList.toggle("active", panel.id === "panel-flyer-extractor"));
  loadRecent();
}

async function loadSupermarkets() {
  const select = document.getElementById("flyer-supermarket");
  if (!select) return;

  try {
    const res = await api("/admin/supermarkets");
    state.supermarkets = res.ok ? await res.json() : [];
  } catch {
    state.supermarkets = [];
  }

  select.innerHTML = `<option value="">Nessuno / da decidere</option>` + state.supermarkets.map((sm) => `
    <option value="${sm.id}">${esc(sm.name)}</option>
  `).join("");
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
      <small>Sto creando le immagini pagina. Nessun OCR.</small>
    </div>
  `;
}

async function checkHealth() {
  const res = await api("/admin/flyer-extractor/health");
  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  alert(`Extractor OK: ${data.ok}\nPyMuPDF: ${data.pymupdf_available}\nPillow: ${data.pillow_available}\nNo OCR: ${data.no_ocr}`);
}

async function uploadPdf() {
  const file = document.getElementById("flyer-pdf")?.files?.[0];
  if (!file) return alert("Seleziona un PDF.");

  const data = commonFormData();
  data.append("file", file);

  setLoading("Estraggo pagine dal PDF...");
  const res = await api("/admin/flyer-extractor/pdf", { method: "POST", body: data, headers: {} });
  if (!res.ok) return showError(await readError(res));
  state.current = await res.json();
  renderResult(state.current);
  loadRecent();
}

async function uploadImagesZip() {
  const file = document.getElementById("flyer-images-zip")?.files?.[0];
  if (!file) return alert("Seleziona uno ZIP con immagini pagina.");

  const data = commonFormData();
  data.append("file", file);

  setLoading("Importo immagini dallo ZIP...");
  const res = await api("/admin/flyer-extractor/images-zip", { method: "POST", body: data, headers: {} });
  if (!res.ok) return showError(await readError(res));
  state.current = await res.json();
  renderResult(state.current);
  loadRecent();
}

async function importUrl() {
  const url = document.getElementById("flyer-url")?.value.trim();
  if (!url) return alert("Inserisci un URL diretto PDF o immagine.");

  const payload = { ...commonJson(), url };

  setLoading("Scarico URL diretto...");
  const res = await api("/admin/flyer-extractor/url", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) return showError(await readError(res));
  state.current = await res.json();
  renderResult(state.current);
  loadRecent();
}

function showError(message) {
  document.getElementById("flyer-result").innerHTML = `
    <div class="flyer-error">
      <strong>Errore</strong>
      <p>${esc(message)}</p>
    </div>
  `;
}

function absoluteUrl(path) {
  if (!path) return "";
  if (path.startsWith("http")) return path;
  return `${CONFIG.API_BASE_URL}${path}`;
}

function renderResult(manifest) {
  const result = document.getElementById("flyer-result");
  const pages = manifest.pages || [];

  result.innerHTML = `
    <div class="flyer-result-head">
      <div>
        <p class="flyer-kicker">Estrazione completata</p>
        <h3>${esc(manifest.title)}</h3>
        <p>${pages.length} pagine · ${esc(manifest.valid_from || "data inizio n/d")} → ${esc(manifest.valid_to || "data fine n/d")}</p>
      </div>
      <div class="flyer-actions">
        <a class="primary-btn" href="${absoluteUrl(manifest.zip_url)}" target="_blank" rel="noreferrer">Scarica ZIP pagine</a>
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

  state.recent = await res.json();
  if (!state.recent.length) {
    box.innerHTML = `<div class="empty-state">Nessuna estrazione recente.</div>`;
    return;
  }

  box.innerHTML = state.recent.map((item) => `
    <button type="button" class="flyer-recent-card" data-id="${esc(item.extraction_id)}">
      <strong>${esc(item.title)}</strong>
      <small>${item.pages_count || 0} pagine · ${esc(item.source_type)}</small>
    </button>
  `).join("");

  box.querySelectorAll("[data-id]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      const res = await api(`/admin/flyer-extractor/${id}/manifest`);
      if (!res.ok) return alert(await readError(res));
      state.current = await res.json();
      renderResult(state.current);
      activateTab();
    });
  });
}

document.addEventListener("DOMContentLoaded", async () => {
  injectPanel();
  await loadSupermarkets();
  await loadRecent();
});
