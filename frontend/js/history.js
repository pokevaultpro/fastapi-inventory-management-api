import CONFIG from "./config.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

const state = {
  stats: null,
  chart: { monthlyPoints: [], supermarketSegments: [] },
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

function monthLabel(period) {
  if (!period || !period.includes("-")) return period || "N/D";
  const [year, month] = period.split("-");
  return `${month}/${year.slice(2)}`;
}

function setCanvasSize(canvas, cssHeight) {
  const parent = canvas.parentElement;
  const width = Math.max(320, parent ? parent.clientWidth : canvas.getBoundingClientRect().width || 320);
  const dpr = window.devicePixelRatio || 1;
  canvas.style.width = "100%";
  canvas.style.height = `${cssHeight}px`;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(cssHeight * dpr);
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, width, height: cssHeight, dpr };
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
  document.getElementById("refresh-btn")?.addEventListener("click", refresh);
  document.getElementById("range-select")?.addEventListener("change", refresh);

  const monthly = document.getElementById("monthly-chart");
  monthly?.addEventListener("mousemove", (event) => showMonthlyTooltip(event));
  monthly?.addEventListener("click", (event) => showMonthlyTooltip(event, true));
  monthly?.addEventListener("mouseleave", hideChartTooltip);
  monthly?.addEventListener("touchstart", (event) => showMonthlyTooltip(event.touches[0], true), { passive: true });

  const donut = document.getElementById("supermarket-chart");
  donut?.addEventListener("mousemove", (event) => showSupermarketTooltip(event));
  donut?.addEventListener("click", (event) => showSupermarketTooltip(event, true));
  donut?.addEventListener("mouseleave", hideChartTooltip);
  donut?.addEventListener("touchstart", (event) => showSupermarketTooltip(event.touches[0], true), { passive: true });
}

async function refresh() {
  try {
    state.stats = await loadStats();
    renderAll();
  } catch (err) {
    console.error(err);
    document.querySelector(".history-page")?.insertAdjacentHTML("beforeend", `<div class="empty-state">Errore caricamento cronologia: ${err.message}</div>`);
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
  const o = state.stats.overview || {};
  const cards = [
    { label: "Totale speso", value: euro(o.total_spent), sub: `${o.trips_count || 0} liste finalizzate`, accent: "rgba(34,197,94,.18)", icon: "€" },
    { label: "Prodotti comprati", value: o.total_items || 0, sub: `${euro(o.average_item_price)} medio/prodotto`, accent: "rgba(37,99,235,.16)", icon: "🛒" },
    { label: "Media per spesa", value: euro(o.average_trip), sub: "ticket medio", accent: "rgba(249,115,22,.18)", icon: "📈" },
    { label: "Risparmio stimato", value: euro(o.estimated_savings), sub: `${o.discounted_lines || 0} righe scontate`, accent: "rgba(124,58,237,.16)", icon: "✨" },
  ];
  document.getElementById("kpi-grid").innerHTML = cards.map(c => `
    <article class="kpi-card" style="--accent:${c.accent}">
      <div class="kpi-icon">${c.icon}</div>
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
  state.chart.monthlyPoints = [];

  if (!data.length) {
    canvas.style.display = "none";
    empty.style.display = "block";
    return;
  }
  canvas.style.display = "block";
  empty.style.display = "none";

  const { ctx, width: w, height: h } = setCanvasSize(canvas, window.innerWidth < 720 ? 250 : 300);
  const pad = { left: 56, right: 26, top: 28, bottom: 48 };
  const max = Math.max(...data.map(d => Number(d.total || 0)), 1);
  const minPlot = 4;
  const plotW = w - pad.left - pad.right;
  const plotH = h - pad.top - pad.bottom;
  const barGap = 14;
  const barW = Math.max(20, Math.min(64, plotW / data.length - barGap));

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#f8fafc";
  ctx.fillRect(0, 0, w, h);

  ctx.strokeStyle = "#e2e8f0";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#64748b";
  ctx.font = "800 11px Inter, system-ui";
  ctx.textAlign = "right";

  for (let i = 0; i <= 4; i++) {
    const y = pad.top + i * plotH / 4;
    const value = max - (i * max / 4);
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(w - pad.right, y);
    ctx.stroke();
    ctx.fillText(euro(value), pad.left - 10, y + 4);
  }

  const points = data.map((d, i) => {
    const slot = plotW / data.length;
    const x = pad.left + slot * i + slot / 2;
    const barHeight = Math.max(minPlot, (Number(d.total || 0) / max) * plotH);
    const y = h - pad.bottom - barHeight;
    return { x, y, barHeight, barW, ...d };
  });

  points.forEach((p) => {
    const x = p.x - barW / 2;
    const y = h - pad.bottom - p.barHeight;
    const radius = 10;
    const grd = ctx.createLinearGradient(0, y, 0, h - pad.bottom);
    grd.addColorStop(0, "#22c55e");
    grd.addColorStop(1, "#bbf7d0");
    ctx.fillStyle = grd;
    roundRect(ctx, x, y, barW, p.barHeight, radius);
    ctx.fill();

    ctx.fillStyle = "#0f172a";
    ctx.font = "900 11px Inter, system-ui";
    ctx.textAlign = "center";
    if (p.barHeight > 34) ctx.fillText(euro(p.total), p.x, y + 18);

    ctx.fillStyle = "#64748b";
    ctx.font = "800 11px Inter, system-ui";
    ctx.fillText(monthLabel(p.period), p.x, h - 18);
  });

  if (points.length > 1) {
    ctx.beginPath();
    points.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y));
    ctx.strokeStyle = "#2563eb";
    ctx.lineWidth = 3;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();
  }

  points.forEach((p) => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 7, 0, Math.PI * 2);
    ctx.fillStyle = "white";
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = "#2563eb";
    ctx.stroke();
    p.hitRadius = 18;
  });

  state.chart.monthlyPoints = points;
}

function roundRect(ctx, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r);
  ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r);
  ctx.closePath();
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
  state.chart.supermarketSegments = [];

  const { ctx, width: w, height: h } = setCanvasSize(canvas, window.innerWidth < 720 ? 240 : 280);
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#f8fafc";
  ctx.fillRect(0, 0, w, h);

  if (!data.length) {
    legend.innerHTML = `<div class="empty-state">Nessun supermercato ancora.</div>`;
    return;
  }

  const total = data.reduce((a,b) => a + Number(b.total || 0), 0) || 1;
  const cx = w / 2;
  const cy = h / 2;
  const radius = Math.min(w, h) * .34;
  let start = -Math.PI / 2;

  data.forEach((row, idx) => {
    const angle = (Number(row.total || 0) / total) * Math.PI * 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.arc(cx, cy, radius, start, start + angle);
    ctx.closePath();
    ctx.fillStyle = colors[idx % colors.length];
    ctx.fill();
    state.chart.supermarketSegments.push({ start, end: start + angle, row, color: colors[idx % colors.length], cx, cy, radius });
    start += angle;
  });

  ctx.beginPath();
  ctx.arc(cx, cy, radius * .58, 0, Math.PI * 2);
  ctx.fillStyle = "white";
  ctx.fill();
  ctx.fillStyle = "#0f172a";
  ctx.font = "900 22px Inter, system-ui";
  ctx.textAlign = "center";
  ctx.fillText(euro(total), cx, cy + 4);
  ctx.fillStyle = "#64748b";
  ctx.font = "800 11px Inter, system-ui";
  ctx.fillText("totale", cx, cy + 24);

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

function showChartTooltip(content, clientX, clientY) {
  const tooltip = document.getElementById("chart-tooltip");
  if (!tooltip) return;
  tooltip.innerHTML = content;
  tooltip.hidden = false;
  const pad = 14;
  const rect = tooltip.getBoundingClientRect();
  let left = clientX + pad;
  let top = clientY - rect.height - pad;
  if (left + rect.width > window.innerWidth - 10) left = clientX - rect.width - pad;
  if (top < 10) top = clientY + pad;
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
}

function hideChartTooltip() {
  const tooltip = document.getElementById("chart-tooltip");
  if (tooltip) tooltip.hidden = true;
}

function showMonthlyTooltip(event, force = false) {
  const canvas = document.getElementById("monthly-chart");
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const hit = state.chart.monthlyPoints.find(p => Math.hypot(p.x - x, p.y - y) <= (force ? 28 : 18) || (Math.abs(p.x - x) <= p.barW / 2 && y >= p.y));
  if (!hit) {
    if (!force) hideChartTooltip();
    return;
  }
  showChartTooltip(`<b>${monthLabel(hit.period)}</b><br>${euro(hit.total)}<br>${hit.trips || 0} liste · ${hit.items || 0} prodotti`, event.clientX, event.clientY);
}

function showSupermarketTooltip(event, force = false) {
  const canvas = document.getElementById("supermarket-chart");
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  const seg0 = state.chart.supermarketSegments[0];
  if (!seg0) return;
  const dx = x - seg0.cx;
  const dy = y - seg0.cy;
  const dist = Math.hypot(dx, dy);
  if (dist > seg0.radius || dist < seg0.radius * .58) {
    if (!force) hideChartTooltip();
    return;
  }
  let angle = Math.atan2(dy, dx);
  if (angle < -Math.PI / 2) angle += Math.PI * 2;
  const hit = state.chart.supermarketSegments.find(s => angle >= s.start && angle <= s.end);
  if (!hit) return;
  showChartTooltip(`<b>${hit.row.supermarket}</b><br>${euro(hit.row.total)}<br>${hit.row.quantity || 0} prodotti · ${hit.row.lines || 0} righe`, event.clientX, event.clientY);
}

window.addEventListener("resize", () => {
  if (state.stats) {
    drawMonthlyChart();
    drawSupermarketChart();
  }
});

init();
