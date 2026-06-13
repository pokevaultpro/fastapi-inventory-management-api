import CONFIG from "./config.js";

const token = () => localStorage.getItem("token");
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[m]));

async function api(path, options = {}) {
  const headers = {
    Authorization: `Bearer ${token()}`,
    ...(options.headers || {}),
  };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

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

function ensureCleanupBox() {
  if (document.getElementById("conad-cleanup-box-v26c")) return;

  const panel =
    document.getElementById("panel-flyer-offers") ||
    document.getElementById("panel-flyer-extractor") ||
    document.querySelector(".admin-desktop") ||
    document.querySelector("main") ||
    document.body;

  const box = document.createElement("section");
  box.id = "conad-cleanup-box-v26c";
  box.className = "conad-cleanup-box";
  box.innerHTML = `
    <div>
      <p class="eyebrow">Pulizia catalogo</p>
      <h3>Rimuovi prodotti Conad importati per errore</h3>
      <p>Usalo prima di reimportare il volantino nel nuovo workflow Offerte volantini.</p>
    </div>

    <div class="conad-cleanup-grid">
      <label>
        Validità da
        <input id="conad-cleanup-from" value="2026-06-15">
      </label>
      <label>
        Validità a
        <input id="conad-cleanup-to" value="2026-06-27">
      </label>
      <label class="check-row">
        <input id="conad-cleanup-images" type="checkbox">
        cancella anche immagini locali
      </label>
    </div>

    <div class="conad-cleanup-actions">
      <button type="button" class="ghost-btn" id="conad-cleanup-preview">Anteprima</button>
      <button type="button" class="delete-btn" id="conad-cleanup-execute">Cancella candidati</button>
    </div>

    <pre id="conad-cleanup-output" class="conad-cleanup-output">Prima fai Anteprima.</pre>
  `;

  panel.prepend(box);

  document.getElementById("conad-cleanup-preview")?.addEventListener("click", previewCleanup);
  document.getElementById("conad-cleanup-execute")?.addEventListener("click", executeCleanup);
}

function values() {
  return {
    valid_from: document.getElementById("conad-cleanup-from")?.value || "2026-06-15",
    valid_to: document.getElementById("conad-cleanup-to")?.value || "2026-06-27",
    delete_images: Boolean(document.getElementById("conad-cleanup-images")?.checked),
  };
}

function renderOutput(data) {
  const out = document.getElementById("conad-cleanup-output");
  if (!out) return;

  const first = (data.first_candidates || data.first_deleted || []).slice(0, 15);
  const deps = (data.dependency_counts || []).filter(x => Number(x.rows || 0) > 0);

  out.textContent = [
    `Modalità: ${data.mode}`,
    `Candidati: ${data.candidate_count}`,
    data.products_deleted != null ? `Prodotti cancellati: ${data.products_deleted}` : null,
    data.images_deleted != null ? `Immagini cancellate: ${data.images_deleted}` : null,
    "",
    "Prime righe:",
    ...first.map(p => `#${p.id} ${p.name} | pag=${p.flyer_page ?? ""} | valid=${p.flyer_valid_from ?? ""}->${p.flyer_valid_to ?? ""}`),
    "",
    "Righe collegate:",
    ...(deps.length ? deps.map(d => `${d.table}.${d.column}: ${d.rows}`) : ["nessuna"]),
  ].filter(x => x !== null).join("\n");
}

async function previewCleanup() {
  const v = values();
  const params = new URLSearchParams({ valid_from: v.valid_from, valid_to: v.valid_to });
  const res = await api(`/admin/cleanup/conad-flyer-products/preview?${params.toString()}`);
  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  renderOutput(data);
}

async function executeCleanup() {
  const v = values();
  const ok = confirm(
    `Vuoi cancellare davvero i prodotti Conad candidati con validità ${v.valid_from} → ${v.valid_to}?\n\nFai prima Anteprima se non l'hai già fatto.`
  );
  if (!ok) return;

  const res = await api("/admin/cleanup/conad-flyer-products/execute", {
    method: "POST",
    body: JSON.stringify({ ...v, confirm: true }),
  });
  if (!res.ok) return alert(await readError(res));
  const data = await res.json();
  renderOutput(data);
  alert(`Pulizia completata: ${data.products_deleted} prodotti cancellati.`);
}

document.addEventListener("DOMContentLoaded", ensureCleanupBox);
setTimeout(ensureCleanupBox, 700);
