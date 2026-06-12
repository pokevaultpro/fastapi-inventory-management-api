import CONFIG from "./config.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

const state = {
  stats: null,
  expandedHistoryId: null,
};

const colors = ["#22c55e", "#2563eb", "#f97316", "#7c3aed", "#ef4444", "#14b8a6", "#eab308", "#0f172a"];

function euro(value) {
  return "€ " + Number(value || 0).toFixed(2).replace(".", ",");
}

function fmtDate(value) {
  if (!value) return "Data sconosciuta";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleDateString("it-IT", { day: "2-digit", month: "short", year: "numeric" });
}

function imgSrc(src) {
  if (!src) return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Crect width='100%25' height='100%25' rx='18' fill='%23e2e8f0'/%3E%3Ctext x='50%25' y='53%25' text-anchor='middle' font-size='24' fill='%2394a3b8'%3E🛒%3C/text%3E%3C/svg%3E";
  return src;
}

async function loadStats() {
  const range = document.getElementById("range-select").value;
  const qs = range === "all" ? "" : `?days=${range}`;
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/shopping-history/stats${qs}`, {
    headers: { "Authorization": "Bearer " + token }
  });
  if (!res || !res.ok) throw new Error("Impossibile caricare la cronologia");
  return res.json();
}

async function init() {
  bindEvents();
  await refresh();
}

function bindEvents() {
  document.getElementById("refresh-btn").addEventListener("click", refresh);
  document.getElementById("range-select").addEventListener("change", refresh);
}

async function refresh() {
  try {
    state.stats = await loadStats();
    renderAll();
  } catch (err) {
    console.error(err);
    document.querySelector(".history-page").insertAdjacentHTML("beforeend", `<div class="empty-state">Errore caricamento cronologia: ${err.message}</div>`);
  }
}

function renderAll() {
  renderKpis();
  drawMonthlyChart();
  renderRecentLists();
  renderCategoryBars();
  drawSupermarketChart();
  renderTopProducts();
}

function renderKpis() {
  const o = state.stats.overview;
  const cards = [
    { label: "Totale speso", value: euro(o.total_spent), sub: `${o.trips_count} liste finalizzate`, accent: "rgba(34,197,94,.18)" },
    { label: "Prodotti comprati", value: o.total_items, sub: `${euro(o.average_item_price)} medio/prodotto`, accent: "rgba(37,99,235,.16)" },
    { label: "Media per spesa", value: euro(o.average_trip), sub: "ticket medio", accent: "rgba(249,115,22,.18)" },
    { label: "Risparmio stimato", value: euro(o.estimated_savings), sub: `${o.discounted_lines} righe scontate`, accent: "rgba(124,58,237,.16)" },
  ];
  document.getElementById("kpi-grid").innerHTML = cards.map(c => `
    <article class="kpi-card" style="--accent:${c.accent}">
      <div class="kpi-label">${c.label}</div>
      <div class="kpi-value">${c.value}</div>
      <div class="kpi-sub">${c.sub}</div>
    </article>
  `).join("");
}

function drawMonthlyChart() {
  const canvas = document.getElementById("monthly-chart");
  const empty = document.getElementById("monthly-empty");
  const data = state.stats.monthly || [];
  if (!data.length) {
    canvas.style.display = "none";
    empty.style.display = "block";
    return;
  }
  canvas.style.display = "block";
  empty.style.display = "none";

  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = 220 * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = 220;
  const pad = { left: 44, right: 18, top: 20, bottom: 34 };
  const max = Math.max(...data.map(d => d.total), 1);
  const points = data.map((d, i) => {
    const x = pad.left + (data.length === 1 ? (w - pad.left - pad.right) / 2 : i * (w - pad.left - pad.right) / (data.length - 1));
    const y = h - pad.bottom - (d.total / max) * (h - pad.top - pad.bottom);
    return { x, y, ...d };
  });

  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  for (let i = 0; i < 4; i++) {
    const y = pad.top + i * (h - pad.top - pad.bottom) / 3;
    ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(w - pad.right, y); ctx.stroke();
  }

  const gradient = ctx.createLinearGradient(0, pad.top, 0, h - pad.bottom);
  gradient.addColorStop(0, "rgba(34,197,94,.28)");
  gradient.addColorStop(1, "rgba(34,197,94,0)");
  ctx.beginPath();
  points.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
  ctx.lineTo(points.at(-1).x, h - pad.bottom);
  ctx.lineTo(points[0].x, h - pad.bottom);
  ctx.closePath();
  ctx.fillStyle = gradient;
  ctx.fill();

  ctx.beginPath();
  points.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
  ctx.strokeStyle = "#16a34a";
  ctx.lineWidth = 4;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke();

  points.forEach((p) => {
    ctx.beginPath(); ctx.arc(p.x, p.y, 5, 0, Math.PI * 2); ctx.fillStyle = "#16a34a"; ctx.fill();
    ctx.beginPath(); ctx.arc(p.x, p.y, 9, 0, Math.PI * 2); ctx.strokeStyle = "rgba(22,163,74,.22)"; ctx.lineWidth = 4; ctx.stroke();
    ctx.fillStyle = "#64748b"; ctx.font = "700 11px Inter"; ctx.textAlign = "center";
    ctx.fillText(p.period.slice(5) + "/" + p.period.slice(2,4), p.x, h - 10);
  });
}

function renderRecentLists() {
  const container = document.getElementById("recent-lists");
  const latest = state.stats.latest || [];
  if (!latest.length) {
    container.innerHTML = `<div class="empty-state">Nessuna spesa finalizzata ancora.</div>`;
    return;
  }

  container.innerHTML = latest.map(h => `
    <article class="recent-item" data-history-id="${h.id}">
      <div class="recent-top">
        <div>
          <div class="recent-title">Spesa #${h.id}</div>
          <div class="recent-date">${fmtDate(h.created_at)} · ${h.total_items} prodotti</div>
        </div>
        <div class="recent-total">${euro(h.total_price)}</div>
      </div>
      <div class="preview-stack">
        ${(h.preview_items || []).map(i => `<img class="preview-img" src="${imgSrc(i.image)}" title="${i.name}">`).join("")}
      </div>
      <div class="recent-actions">
        <button class="restore-btn" data-action="restore" data-id="${h.id}">Ripristina lista</button>
        <button class="details-btn" data-action="details" data-id="${h.id}">Dettagli</button>
      </div>
      <div class="details-panel" id="details-${h.id}"></div>
    </article>
  `).join("");

  container.querySelectorAll("[data-action='restore']").forEach(btn => {
    btn.addEventListener("click", () => restoreList(Number(btn.dataset.id)));
  });
  container.querySelectorAll("[data-action='details']").forEach(btn => {
    btn.addEventListener("click", () => toggleDetails(Number(btn.dataset.id)));
  });
}

async function toggleDetails(historyId) {
  const panel = document.getElementById(`details-${historyId}`);
  if (!panel) return;
  if (panel.classList.contains("open")) {
    panel.classList.remove("open");
    return;
  }
  if (!panel.dataset.loaded) {
    panel.innerHTML = `<div class="empty-state">Carico dettagli...</div>`;
    const res = await apiFetch(`${CONFIG.API_BASE_URL}/shopping-history/${historyId}/items`, {
      headers: { "Authorization": "Bearer " + token }
    });
    const items = res && res.ok ? await res.json() : [];
    panel.innerHTML = items.map(item => `
      <div class="detail-row">
        <img src="${imgSrc(item.image)}" alt="">
        <div>
          <div class="detail-name">${item.name}</div>
          <div class="detail-meta">x${item.quantity || 1} · ${item.category || "Categoria n/d"} · ${item.supermarket_name || "N/D"}</div>
        </div>
        <div class="detail-price">${euro((item.price_paid || 0) * (item.quantity || 1))}</div>
      </div>
    `).join("") || `<div class="empty-state">Nessun dettaglio disponibile.</div>`;
    panel.dataset.loaded = "1";
  }
  panel.classList.add("open");
}

async function restoreList(historyId) {
  const clear = document.getElementById("clear-before-restore").checked;
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/shopping-history/${historyId}/restore-cart?clear_existing=${clear}&merge_duplicates=true`, {
    method: "POST",
    headers: { "Authorization": "Bearer " + token }
  });
  if (!res || !res.ok) {
    showToast({ error: true, message: "Non sono riuscito a ripristinare la lista." });
    return;
  }
  const data = await res.json();
  showToast(data);
}

function showToast(data) {
  const el = document.getElementById("restore-toast");
  if (data.error) {
    el.innerHTML = `<h3>Errore</h3><p>${data.message}</p><button onclick="this.closest('#restore-toast').hidden=true">Chiudi</button>`;
    el.hidden = false;
    return;
  }

  const changes = data.price_changes || [];
  const missing = data.missing || [];
  el.innerHTML = `
    <h3>Lista ripristinata ✅</h3>
    <p>${data.restored_count} prodotti aggiunti, ${data.merged_count} già presenti aggiornati.</p>
    <p>Totale vecchio: <b>${euro(data.previous_total)}</b> · Totale attuale: <b>${euro(data.current_total)}</b> · Differenza: <b>${euro(data.total_delta)}</b></p>
    ${changes.length ? `<p><b>${changes.length} prezzi sono cambiati:</b></p><ul>${changes.slice(0,6).map(c => `<li>${c.name}: ${euro(c.old_unit_price)} → ${euro(c.current_unit_price)}</li>`).join("")}</ul>` : `<p>Nessun cambio prezzo rilevante.</p>`}
    ${missing.length ? `<p>${missing.length} prodotti non più presenti nel catalogo.</p>` : ""}
    <button onclick="this.closest('#restore-toast').hidden=true">Ok</button>
    <button onclick="window.location.href='shopping-list.html'">Vai al carrello</button>
  `;
  el.hidden = false;
}

function renderCategoryBars() {
  const rows = state.stats.category_breakdown || [];
  const container = document.getElementById("category-bars");
  if (!rows.length) {
    container.innerHTML = `<div class="empty-state">Nessuna categoria ancora.</div>`;
    return;
  }
  const max = Math.max(...rows.map(r => r.total), 1);
  container.innerHTML = rows.map(r => `
    <div class="bar-row">
      <div class="bar-label" title="${r.category}">${r.category}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.max(4, (r.total / max) * 100)}%"></div></div>
      <div class="bar-value">${euro(r.total)}</div>
    </div>
  `).join("");
}

function drawSupermarketChart() {
  const canvas = document.getElementById("supermarket-chart");
  const legend = document.getElementById("supermarket-legend");
  const data = state.stats.supermarket_breakdown || [];
  const ctx = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = 220 * dpr;
  ctx.scale(dpr, dpr);
  const w = rect.width, h = 220;
  ctx.clearRect(0,0,w,h);

  if (!data.length) {
    legend.innerHTML = `<div class="empty-state">Nessun supermercato ancora.</div>`;
    return;
  }

  const total = data.reduce((a,b) => a + b.total, 0) || 1;
  const cx = w / 2, cy = h / 2, radius = Math.min(w,h) * .34;
  let start = -Math.PI / 2;
  data.forEach((row, idx) => {
    const angle = (row.total / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, start, start + angle);
    ctx.closePath();
    ctx.fillStyle = colors[idx % colors.length];
    ctx.fill();
    start += angle;
  });
  ctx.beginPath(); ctx.arc(cx, cy, radius * .58, 0, Math.PI * 2); ctx.fillStyle = "white"; ctx.fill();
  ctx.fillStyle = "#0f172a"; ctx.font = "900 22px Inter"; ctx.textAlign = "center"; ctx.fillText(euro(total), cx, cy + 4);
  ctx.fillStyle = "#64748b"; ctx.font = "800 11px Inter"; ctx.fillText("totale", cx, cy + 24);

  legend.innerHTML = data.map((row, idx) => `
    <span class="legend-pill"><span class="legend-dot" style="background:${colors[idx % colors.length]}"></span>${row.supermarket} · ${euro(row.total)}</span>
  `).join("");
}

function renderTopProducts() {
  const rows = state.stats.top_products || [];
  const container = document.getElementById("top-products");
  if (!rows.length) {
    container.innerHTML = `<div class="empty-state">Nessun prodotto ancora.</div>`;
    return;
  }
  container.innerHTML = rows.map((p, idx) => `
    <article class="top-product">
      <img src="${imgSrc(p.image)}" alt="">
      <div>
        <div class="top-product-name">#${idx + 1} ${p.name}</div>
        <div class="top-product-meta">x${p.quantity} · ${euro(p.total)} · ${p.category || "Categoria n/d"}</div>
      </div>
    </article>
  `).join("");
}

window.addEventListener("resize", () => {
  if (state.stats) {
    drawMonthlyChart();
    drawSupermarketChart();
  }
});

init();
