import CONFIG from "./config.js";

const DAYS = [
  { index: 0, label: "Lunedì", short: "Lun" },
  { index: 1, label: "Martedì", short: "Mar" },
  { index: 2, label: "Mercoledì", short: "Mer" },
  { index: 3, label: "Giovedì", short: "Gio" },
  { index: 4, label: "Venerdì", short: "Ven" },
  { index: 5, label: "Sabato", short: "Sab" },
  { index: 6, label: "Domenica", short: "Dom" },
];

const MEALS = [
  { id: "breakfast", label: "Colazione", emoji: "☕" },
  { id: "lunch", label: "Pranzo", emoji: "🍝" },
  { id: "snack", label: "Spuntino", emoji: "🍎" },
  { id: "dinner", label: "Cena", emoji: "🍽️" },
];

const PDF_GREEN = [22, 163, 74];
const PDF_GREEN_DARK = [21, 128, 61];
const PDF_GREEN_SOFT = [220, 252, 231];
const PDF_SLATE = [15, 23, 42];
const PDF_MUTED = [100, 116, 139];
const PDF_LINE = [226, 232, 240];
const PDF_BG = [248, 250, 252];

let currentWeekStart = getMonday(new Date());
let currentMenu = null;
let recipes = [];
let activeSlot = null;

const $ = (id) => document.getElementById(id);

document.addEventListener("DOMContentLoaded", async () => {
  $("weekStart").value = toISO(currentWeekStart);

  $("prevWeek").addEventListener("click", () => shiftWeek(-7));
  $("nextWeek").addEventListener("click", () => shiftWeek(7));
  $("weekStart").addEventListener("change", () => {
    currentWeekStart = getMonday(new Date(`${$("weekStart").value}T12:00:00`));
    $("weekStart").value = toISO(currentWeekStart);
    loadAll();
  });
  $("downloadPdf").addEventListener("click", downloadPdf);
  $("addToCart").addEventListener("click", addWeekToCart);
  $("duplicateWeek").addEventListener("click", duplicateNextWeek);
  $("recipeSearch").addEventListener("input", renderRecipePicker);
  document.querySelectorAll("[data-close-modal]").forEach(el => el.addEventListener("click", closeRecipeModal));

  await loadAll();
});

function token() {
  return localStorage.getItem("token");
}

async function api(path, options = {}) {
  const headers = {
    ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
    ...(options.headers || {}),
    Authorization: `Bearer ${token()}`,
  };
  const res = await fetch(`${CONFIG.API_BASE_URL}${path}`, { ...options, headers });
  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "index.html";
    return null;
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = typeof data.detail === "string" ? data.detail : JSON.stringify(data);
    } catch {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

async function loadAll() {
  try {
    const week = toISO(currentWeekStart);
    const [menuData, recipesData] = await Promise.all([
      api(`/weekly-menus?week_start=${week}`),
      api("/weekly-menus/recipes"),
    ]);
    currentMenu = menuData;
    recipes = recipesData || [];
    renderStats();
    renderPlanner();
    renderRecipePicker();
  } catch (err) {
    showToast(err.message || "Errore caricamento menu");
  }
}

function shiftWeek(days) {
  currentWeekStart = addDays(currentWeekStart, days);
  $("weekStart").value = toISO(currentWeekStart);
  loadAll();
}

function getMonday(date) {
  const d = new Date(date);
  const day = d.getDay();
  const diff = (day === 0 ? -6 : 1) - day;
  d.setDate(d.getDate() + diff);
  d.setHours(12, 0, 0, 0);
  return d;
}

function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function toISO(date) {
  return date.toISOString().slice(0, 10);
}

function formatDate(date) {
  return new Intl.DateTimeFormat("it-IT", { day: "2-digit", month: "short" }).format(date);
}

function fullDate(date) {
  return new Intl.DateTimeFormat("it-IT", { weekday: "long", day: "2-digit", month: "long" }).format(date);
}

function money(value) {
  return new Intl.NumberFormat("it-IT", { style: "currency", currency: "EUR" }).format(Number(value || 0));
}

function normalizeImageUrl(path) {
  if (!path) return `${window.location.origin}/static/images/placeholder.jpg`;

  let url = String(path).trim();

  // Se è path relativo, usa sempre il dominio del frontend, non quello del backend.
  if (url.startsWith("/")) return `${window.location.origin}${url}`;
  if (!/^https?:\/\//i.test(url)) return `${window.location.origin}/${url}`;

  // Caso frequente: immagine assoluta su pokevaultpro.com ma pagina su www.pokevaultpro.com, o viceversa.
  // L'immagine si vede nel sito, ma il fetch per PDF può fallire per CORS.
  // Se hostname è lo stesso dominio base, forzo origin corrente.
  try {
    const parsed = new URL(url);
    const current = new URL(window.location.origin);
    const baseA = parsed.hostname.replace(/^www\./, "");
    const baseB = current.hostname.replace(/^www\./, "");
    if (baseA === baseB && parsed.pathname.startsWith("/static/")) {
      return `${window.location.origin}${parsed.pathname}${parsed.search || ""}`;
    }
  } catch {}

  return url;
}

function imageOrPlaceholder(path) {
  return path || "/static/images/placeholder.jpg";
}

function getItem(dayIndex, mealType) {
  return (currentMenu?.items || []).find(i => Number(i.day_index) === Number(dayIndex) && i.meal_type === mealType) || null;
}

function renderStats() {
  const end = addDays(currentWeekStart, 6);
  $("weekRange").textContent = `${formatDate(currentWeekStart)} → ${formatDate(end)}`;
  $("plannedCount").textContent = currentMenu?.summary?.planned_meals || 0;
  $("estimatedTotal").textContent = money(currentMenu?.summary?.estimated_total || 0);
  $("recipesCount").textContent = recipes.length;
}

function renderPlanner() {
  const grid = $("plannerGrid");
  const todayISO = toISO(new Date());
  grid.innerHTML = DAYS.map(day => {
    const dayDate = addDays(currentWeekStart, day.index);
    const isToday = toISO(dayDate) === todayISO;
    return `
      <article class="day-column ${isToday ? "today" : ""}">
        <header class="day-head">
          <div>
            <h3>${day.label}</h3>
            <span>${formatDate(dayDate)}</span>
          </div>
        </header>
        ${MEALS.map(meal => renderMealSlot(day, meal)).join("")}
      </article>
    `;
  }).join("");

  grid.querySelectorAll("[data-add-slot],[data-change-slot]").forEach(btn => {
    btn.addEventListener("click", () => openRecipeModal(Number(btn.dataset.day), btn.dataset.meal));
  });
  grid.querySelectorAll("[data-remove-item]").forEach(btn => {
    btn.addEventListener("click", () => removeItem(Number(btn.dataset.removeItem)));
  });
  grid.querySelectorAll("img").forEach(img => {
    img.addEventListener("error", () => {
      img.src = "/static/images/placeholder.jpg";
    });
  });
}

function renderMealSlot(day, meal) {
  const item = getItem(day.index, meal.id);
  const recipe = item?.recipe;

  if (!recipe) {
    return `
      <section class="meal-slot">
        <div class="slot-top">
          <span class="slot-label">${meal.emoji} ${meal.label}</span>
          <button class="add-slot-btn" type="button" data-add-slot data-day="${day.index}" data-meal="${meal.id}">+</button>
        </div>
        <div class="empty-slot">Aggiungi ricetta</div>
      </section>
    `;
  }

  return `
    <section class="meal-slot filled">
      <div class="slot-top">
        <span class="slot-label">${meal.emoji} ${meal.label}</span>
      </div>
      <div class="recipe-slot-card">
        <img src="${escapeAttr(imageOrPlaceholder(recipe.image))}" alt="${escapeAttr(recipe.name)}" />
        <div>
          <h4>${escapeHTML(recipe.name)}</h4>
          <div class="recipe-meta">
            <span>${recipe.prep_time_minutes ? `${recipe.prep_time_minutes} min` : "tempo n/d"}</span>
            <span>${recipe.servings || 1} porz.</span>
            <span>${money(recipe.estimated_total)}</span>
          </div>
        </div>
      </div>
      <div class="slot-actions">
        <button class="secondary-btn" type="button" data-change-slot data-day="${day.index}" data-meal="${meal.id}">Cambia</button>
        <button class="danger-btn" type="button" data-remove-item="${item.id}">Rimuovi</button>
      </div>
    </section>
  `;
}

function openRecipeModal(dayIndex, mealType) {
  activeSlot = { dayIndex, mealType };
  const day = DAYS.find(d => d.index === dayIndex);
  const meal = MEALS.find(m => m.id === mealType);
  $("modalSlotLabel").textContent = `${day?.label || ""} · ${meal?.label || ""}`;
  $("recipeSearch").value = "";
  renderRecipePicker();
  $("recipeModal").classList.remove("hidden");
}

function closeRecipeModal() {
  $("recipeModal").classList.add("hidden");
  activeSlot = null;
}

function renderRecipePicker() {
  const container = $("recipePickerList");
  if (!container) return;

  const q = ($("recipeSearch")?.value || "").trim().toLowerCase();
  const filtered = recipes.filter(r => !q || `${r.name || ""} ${r.description || ""}`.toLowerCase().includes(q));

  if (!filtered.length) {
    container.innerHTML = `
      <div class="empty-slot" style="grid-column:1/-1;min-height:150px;">
        Nessuna ricetta trovata. Crea prima una ricetta nella sezione Ricette.
      </div>
    `;
    return;
  }

  container.innerHTML = filtered.map(recipe => `
    <article class="recipe-picker-card">
      <img src="${escapeAttr(imageOrPlaceholder(recipe.image))}" alt="${escapeAttr(recipe.name)}" />
      <div>
        <h3>${escapeHTML(recipe.name)}</h3>
        <p>${recipe.items_count || 0} ingredienti · ${recipe.prep_time_minutes ? `${recipe.prep_time_minutes} min · ` : ""}${money(recipe.estimated_total)}</p>
      </div>
      <button type="button" data-select-recipe="${recipe.id}">Scegli</button>
    </article>
  `).join("");

  container.querySelectorAll("img").forEach(img => {
    img.addEventListener("error", () => {
      img.src = "/static/images/placeholder.jpg";
    });
  });
  container.querySelectorAll("[data-select-recipe]").forEach(btn => {
    btn.addEventListener("click", () => selectRecipe(Number(btn.dataset.selectRecipe)));
  });
}

async function selectRecipe(recipeId) {
  if (!activeSlot) return;
  try {
    currentMenu = await api("/weekly-menus/item", {
      method: "POST",
      body: JSON.stringify({
        week_start: toISO(currentWeekStart),
        day_index: activeSlot.dayIndex,
        meal_type: activeSlot.mealType,
        recipe_id: recipeId,
      }),
    });
    renderStats();
    renderPlanner();
    closeRecipeModal();
    showToast("Ricetta aggiunta al menu");
  } catch (err) {
    showToast(err.message || "Errore inserimento ricetta");
  }
}

async function removeItem(itemId) {
  try {
    currentMenu = await api(`/weekly-menus/item/${itemId}`, { method: "DELETE" });
    renderStats();
    renderPlanner();
    showToast("Ricetta rimossa");
  } catch (err) {
    showToast(err.message || "Errore rimozione");
  }
}

async function addWeekToCart() {
  if (!currentMenu?.menu?.id) return;
  if (!confirm("Aggiungo tutti gli ingredienti del menu settimanale alla lista della spesa?")) return;

  try {
    const data = await api(`/weekly-menus/${currentMenu.menu.id}/add-to-cart`, {
      method: "POST",
      body: JSON.stringify({ replace_cart: false }),
    });
    showToast(`${data.added_count} prodotti aggiunti alla lista`);
  } catch (err) {
    showToast(err.message || "Errore lista spesa");
  }
}

async function duplicateNextWeek() {
  if (!currentMenu?.menu?.id) return;
  try {
    const data = await api(`/weekly-menus/${currentMenu.menu.id}/duplicate-next-week`, { method: "POST" });
    currentWeekStart = new Date(`${data.menu.week_start}T12:00:00`);
    $("weekStart").value = toISO(currentWeekStart);
    currentMenu = data;
    renderStats();
    renderPlanner();
    showToast("Menu duplicato sulla prossima settimana");
  } catch (err) {
    showToast(err.message || "Errore duplicazione");
  }
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => toast.classList.remove("show"), 2800);
}

/* =========================
   PDF bello + immagini robuste
   ========================= */

async function downloadPdf() {
  if (!currentMenu) return;
  if (!window.jspdf?.jsPDF) {
    showToast("PDF non disponibile: CDN jsPDF non caricata");
    return;
  }

  try {
    showToast("Creo PDF...");
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4", compress: true });

    drawPlannerPage(doc);

    const usedItems = currentMenu.items.filter(i => i.recipe);
    if (usedItems.length) {
      doc.addPage("a4", "portrait");
      await drawRecipeDetails(doc, usedItems);
    }

    doc.save(`menu-settimanale-${toISO(currentWeekStart)}.pdf`);
    showToast("PDF scaricato");
  } catch (err) {
    console.error(err);
    showToast("Errore PDF: " + (err.message || "impossibile generare"));
  }
}

async function drawPlannerPage(doc) {
  const pageW = 297;
  const pageH = 210;
  const margin = 9;
  const headerH = 25;
  const startY = 43;
  const colW = (pageW - margin * 2) / 7;
  const slotH = 33;

  // Background
  doc.setFillColor(246, 251, 247);
  doc.rect(0, 0, pageW, pageH, "F");

  // Header band
  doc.setFillColor(...PDF_GREEN);
  doc.roundedRect(margin, 8, pageW - margin * 2, headerH, 5, 5, "F");

  doc.setFillColor(255, 255, 255);
  doc.setGState?.(new doc.GState({ opacity: 0.14 }));
  doc.circle(pageW - 36, 20, 18, "F");
  doc.circle(pageW - 15, 12, 10, "F");
  doc.setGState?.(new doc.GState({ opacity: 1 }));

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("Menu settimanale", margin + 7, 20);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(
    `${fullDate(currentWeekStart)} → ${fullDate(addDays(currentWeekStart, 6))}`,
    margin + 7,
    27
  );

  // Summary pills
  drawPill(doc, pageW - 93, 14, 34, 7, `${currentMenu.summary.planned_meals || 0} pasti`);
  drawPill(doc, pageW - 55, 14, 38, 7, money(currentMenu.summary.estimated_total || 0));

  // Day columns
  for (const day of DAYS) {
    const x = margin + day.index * colW;
    const dayDate = addDays(currentWeekStart, day.index);

    doc.setFillColor(255, 255, 255);
    doc.setDrawColor(...PDF_LINE);
    doc.roundedRect(x + 1, startY - 6, colW - 2, pageH - startY - 12, 4, 4, "FD");

    doc.setFillColor(...PDF_GREEN_SOFT);
    doc.setDrawColor(187, 247, 208);
    doc.roundedRect(x + 2.5, startY - 3.5, colW - 5, 12, 3, 3, "FD");

    doc.setTextColor(...PDF_SLATE);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(9.5);
    doc.text(day.short, x + 5, startY + 3.8);

    doc.setTextColor(...PDF_GREEN_DARK);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.text(formatDate(dayDate), x + colW - 5, startY + 3.8, { align: "right" });

    for (let mi = 0; mi < MEALS.length; mi++) {
      const meal = MEALS[mi];
      const y = startY + 12 + mi * slotH;
      const item = getItem(day.index, meal.id);
      await drawPdfSlot(doc, x + 2.5, y, colW - 5, slotH - 3.5, meal, item);
    }
  }

  doc.setTextColor(...PDF_MUTED);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.text("Creato con SmartGrocery", pageW / 2, pageH - 5, { align: "center" });
}

function drawPill(doc, x, y, w, h, text) {
  doc.setFillColor(255, 255, 255);
  doc.setGState?.(new doc.GState({ opacity: 0.22 }));
  doc.roundedRect(x, y, w, h, 3.5, 3.5, "F");
  doc.setGState?.(new doc.GState({ opacity: 1 }));
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(7);
  doc.text(text, x + w / 2, y + 4.9, { align: "center" });
}

async function drawPdfSlot(doc, x, y, w, h, meal, item) {
  doc.setDrawColor(...PDF_LINE);
  doc.setFillColor(...PDF_BG);
  doc.roundedRect(x, y, w, h, 3, 3, "FD");

  doc.setTextColor(...PDF_GREEN_DARK);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(6.4);
  doc.text(`${meal.label}`, x + 2, y + 4.8);

  if (!item?.recipe) {
    doc.setTextColor(148, 163, 184);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.text("vuoto", x + w / 2, y + h / 2 + 2, { align: "center" });
    return;
  }

  const recipe = item.recipe;
  const image = await loadPdfImage(recipe.image);

  const imgX = x + 2;
  const imgY = y + 7;
  const imgSize = 11.5;

  doc.setFillColor(...PDF_GREEN_SOFT);
  doc.roundedRect(imgX, imgY, imgSize, imgSize, 2.2, 2.2, "F");

  if (image?.data) {
    try {
      doc.addImage(image.data, image.format, imgX, imgY, imgSize, imgSize, undefined, "FAST");
    } catch (err) {
      console.warn("PDF image skipped", recipe.image, err);
    }
  }

  doc.setTextColor(...PDF_SLATE);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(6.6);
  const titleLines = doc.splitTextToSize(recipe.name || "", w - 17);
  doc.text(titleLines.slice(0, 3), x + 15.2, y + 9.5);

  doc.setFillColor(255, 255, 255);
  doc.roundedRect(x + 2, y + h - 7, w - 4, 5, 2, 2, "F");

  doc.setTextColor(...PDF_MUTED);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(5.8);
  doc.text(`${recipe.servings || 1} porz.`, x + 4, y + h - 3.4);

  doc.setTextColor(...PDF_GREEN_DARK);
  doc.setFont("helvetica", "bold");
  doc.text(money(recipe.estimated_total), x + w - 4, y + h - 3.4, { align: "right" });
}

async function drawRecipeDetails(doc, items) {
  const pageW = 210;
  const pageH = 297;
  let y = 15;

  doc.setFillColor(246, 251, 247);
  doc.rect(0, 0, pageW, pageH, "F");

  doc.setFillColor(...PDF_GREEN);
  doc.roundedRect(12, 10, pageW - 24, 20, 5, 5, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(16);
  doc.text("Dettaglio ricette", 18, 23);

  y = 40;

  const unique = [];
  const seen = new Set();
  for (const item of items) {
    if (!item.recipe || seen.has(item.recipe.id)) continue;
    seen.add(item.recipe.id);
    unique.push(item.recipe);
  }

  for (const recipe of unique) {
    if (y > 238) {
      doc.addPage("a4", "portrait");
      doc.setFillColor(246, 251, 247);
      doc.rect(0, 0, pageW, pageH, "F");
      y = 15;
    }

    doc.setFillColor(255, 255, 255);
    doc.setDrawColor(...PDF_LINE);
    doc.roundedRect(12, y, pageW - 24, 52, 6, 6, "FD");

    const image = await loadPdfImage(recipe.image);
    doc.setFillColor(...PDF_GREEN_SOFT);
    doc.roundedRect(17, y + 7, 36, 36, 4, 4, "F");
    if (image?.data) {
      try {
        doc.addImage(image.data, image.format, 17, y + 7, 36, 36, undefined, "FAST");
      } catch (err) {
        console.warn("PDF detail image skipped", recipe.image, err);
      }
    }

    doc.setTextColor(...PDF_SLATE);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    doc.text(doc.splitTextToSize(recipe.name || "", 132).slice(0, 2), 60, y + 13);

    doc.setFont("helvetica", "normal");
    doc.setTextColor(...PDF_MUTED);
    doc.setFontSize(8);
    doc.text(`${recipe.items_count || 0} ingredienti · ${recipe.servings || 1} porzioni · ${money(recipe.estimated_total)}`, 60, y + 26);

    const ingredients = (recipe.items || [])
      .slice(0, 6)
      .map(i => `• ${i.product?.name || "Ingrediente"} x${i.cart_quantity || i.quantity || 1}`);
    doc.text(doc.splitTextToSize(ingredients.join("\n"), 132), 60, y + 35);

    y += 60;
  }
}

const imageCache = new Map();

async function loadPdfImage(path) {
  if (!path) return null;

  const url = normalizeImageUrl(path);
  if (imageCache.has(url)) return imageCache.get(url);

  // 1) Fetch diretto: funziona bene per same-origin e server con CORS.
  try {
    const res = await fetch(url, { mode: "cors", cache: "force-cache" });
    if (res.ok) {
      const blob = await res.blob();
      const data = await blobToDataURL(blob);
      const format = detectImageFormat(data, blob.type);
      const result = { data, format };
      imageCache.set(url, result);
      return result;
    }
  } catch (err) {
    console.warn("PDF fetch image failed, trying canvas", url, err);
  }

  // 2) Fallback canvas: spesso risolve immagini visibili nel sito ma non fetchabili.
  try {
    const data = await imageToCanvasDataURL(url);
    const result = { data, format: "JPEG" };
    imageCache.set(url, result);
    return result;
  } catch (err) {
    console.warn("PDF canvas image failed", url, err);
  }

  imageCache.set(url, null);
  return null;
}

function detectImageFormat(dataUrl, mimeType = "") {
  const s = `${mimeType} ${dataUrl}`.toLowerCase();
  if (s.includes("image/png")) return "PNG";
  if (s.includes("image/webp")) return "WEBP";
  return "JPEG";
}

function imageToCanvasDataURL(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();

    // Per same-origin non dà problemi; per cross-origin serve header CORS.
    try {
      const parsed = new URL(url);
      if (parsed.origin !== window.location.origin) {
        img.crossOrigin = "anonymous";
      }
    } catch {}

    img.onload = () => {
      try {
        const size = 420;
        const canvas = document.createElement("canvas");
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext("2d");

        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, size, size);

        const scale = Math.max(size / img.naturalWidth, size / img.naturalHeight);
        const w = img.naturalWidth * scale;
        const h = img.naturalHeight * scale;
        const x = (size - w) / 2;
        const y = (size - h) / 2;

        ctx.drawImage(img, x, y, w, h);
        resolve(canvas.toDataURL("image/jpeg", 0.88));
      } catch (err) {
        reject(err);
      }
    };

    img.onerror = reject;
    img.src = url;
  });
}

function blobToDataURL(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttr(value) {
  return escapeHTML(value).replaceAll('"', "&quot;");
}
