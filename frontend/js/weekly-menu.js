import CONFIG from "./config.js";
console.log("weekly-menu v27h menu notes loaded");

const DAYS = [
  { index: 0, label: "Lunedi", short: "Lun" },
  { index: 1, label: "Martedi", short: "Mar" },
  { index: 2, label: "Mercoledi", short: "Mer" },
  { index: 3, label: "Giovedi", short: "Gio" },
  { index: 4, label: "Venerdi", short: "Ven" },
  { index: 5, label: "Sabato", short: "Sab" },
  { index: 6, label: "Domenica", short: "Dom" },
];

const MEALS = [
  { id: "breakfast", label: "Colazione", emoji: "" },
  { id: "lunch", label: "Pranzo", emoji: "" },
  { id: "snack", label: "Spuntino", emoji: "" },
  { id: "dinner", label: "Cena", emoji: "" },
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
  if (url.startsWith("/")) return `${window.location.origin}${url}`;
  if (!/^https?:\/\//i.test(url)) return `${window.location.origin}/${url}`;

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

function getItems(dayIndex, mealType) {
  return (currentMenu?.items || []).filter(i => Number(i.day_index) === Number(dayIndex) && i.meal_type === mealType);
}

function getItem(dayIndex, mealType) {
  return getItems(dayIndex, mealType)[0] || null;
}

function getDayItems(dayIndex, includeEmpty = true) {
  const entries = MEALS.map(meal => ({ meal, items: getItems(dayIndex, meal.id) }));
  return includeEmpty ? entries : entries.filter(entry => entry.items.length > 0);
}

function renderStats() {
  const end = addDays(currentWeekStart, 6);
  $("weekRange").textContent = `${formatDate(currentWeekStart)} -> ${formatDate(end)}`;
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
  const items = getItems(day.index, meal.id);

  if (!items.length) {
    return `
      <section class="meal-slot meal-slot-empty-compact">
        <div class="slot-top">
          <button class="add-slot-btn" type="button" data-add-slot data-day="${day.index}" data-meal="${meal.id}">+ ${meal.label}</button>
        </div>
      </section>
    `;
  }

  return `
    <section class="meal-slot filled">
      <div class="slot-top">
        <span class="slot-label">${meal.label}</span>
        <button class="add-slot-btn" type="button" data-add-slot data-day="${day.index}" data-meal="${meal.id}">+ altra</button>
      </div>
      <div class="recipe-stack">
        ${items.map(item => {
          const recipe = item.recipe;
          return `
            <article class="recipe-slot-card">
              <img src="${escapeAttr(imageOrPlaceholder(recipe.image))}" alt="${escapeAttr(recipe.name)}" />
              <div>
                <h4>${escapeHTML(recipe.name)}</h4>
                ${item.notes ? `<p class="menu-item-note">${escapeHTML(item.notes)}</p>` : ""}
                <div class="recipe-meta">
                  <span>${recipe.prep_time_minutes ? `${recipe.prep_time_minutes} min` : "tempo n/d"}</span>
                  <span>${recipe.servings || 1} porz.</span>
                  <span>${money(recipe.estimated_total)}</span>
                </div>
              </div>
              <button class="remove-mini-btn" type="button" data-remove-item="${item.id}" title="Rimuovi">x</button>
            </article>
          `;
        }).join("")}
      </div>
    </section>
  `;
}

function openRecipeModal(dayIndex, mealType) {
  activeSlot = { dayIndex, mealType };
  const day = DAYS.find(d => d.index === dayIndex);
  const meal = MEALS.find(m => m.id === mealType);
  $("modalSlotLabel").textContent = `${day?.label || ""} - ${meal?.label || ""}`;
  $("recipeSearch").value = "";
  const noteEl = $("menuRecipeNote");
  if (noteEl) noteEl.value = "";
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
        <p>${recipe.items_count || 0} ingredienti - ${recipe.prep_time_minutes ? `${recipe.prep_time_minutes} min - ` : ""}${money(recipe.estimated_total)}</p>
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
        notes: $("menuRecipeNote")?.value?.trim() || null,
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
   PDF export
   1 pagina overview
   7 pagine giornaliere
   pagine finali con ingredienti ricetta per ricetta
   ========================= */

async function downloadPdf() {
  if (!currentMenu) return;
  if (!window.jspdf?.jsPDF) {
    showToast("PDF non disponibile: CDN jsPDF non caricata");
    return;
  }

  try {
    showToast("Creo PDF settimanale...");
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4", compress: true });

    await drawPlannerOverviewPage(doc);

    for (const day of DAYS) {
      doc.addPage("a4", "portrait");
      await drawDayPage(doc, day);
    }

    const usedItems = currentMenu.items.filter(i => i.recipe);
    if (usedItems.length) {
      doc.addPage("a4", "portrait");
      await drawRecipeDetailsSection(doc, usedItems);
    }

    doc.save(`menu-settimanale-${toISO(currentWeekStart)}.pdf`);
    showToast("PDF scaricato");
  } catch (err) {
    console.error(err);
    showToast("Errore PDF: " + (err.message || "impossibile generare"));
  }
}

async function drawPlannerOverviewPage(doc) {
  const pageW = 297;
  const pageH = 210;
  const margin = 9;
  const headerH = 25;
  const startY = 43;
  const colW = (pageW - margin * 2) / 7;
  const slotH = 33;

  doc.setFillColor(246, 251, 247);
  doc.rect(0, 0, pageW, pageH, "F");

  doc.setFillColor(...PDF_GREEN);
  doc.roundedRect(margin, 8, pageW - margin * 2, headerH, 5, 5, "F");

  doc.setFillColor(255, 255, 255);
  if (doc.setGState) doc.setGState(new doc.GState({ opacity: 0.14 }));
  doc.circle(pageW - 36, 20, 18, "F");
  doc.circle(pageW - 15, 12, 10, "F");
  if (doc.setGState) doc.setGState(new doc.GState({ opacity: 1 }));

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("Menu settimanale", margin + 7, 20);

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(
    `${fullDate(currentWeekStart)} -> ${fullDate(addDays(currentWeekStart, 6))}`,
    margin + 7,
    27
  );

  drawSummaryPill(doc, pageW - 111, 14, 32, 7, `${currentMenu.summary.planned_meals || 0} pasti`);
  drawSummaryPill(doc, pageW - 76, 14, 30, 7, `${countDaysWithMeals()} giorni`);
  drawSummaryPill(doc, pageW - 42, 14, 34, 7, money(currentMenu.summary.estimated_total || 0));

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
      const items = getItems(day.index, meal.id);
      await drawMiniSlot(doc, x + 2.5, y, colW - 5, slotH - 3.5, meal, items);
    }
  }

  doc.setTextColor(...PDF_MUTED);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.text("Pagina 1 - panoramica completa della settimana", pageW / 2, pageH - 5, { align: "center" });
}

function countDaysWithMeals() {
  let count = 0;
  for (const day of DAYS) {
    if (getDayItems(day.index, false).length > 0) count += 1;
  }
  return count;
}

function drawSummaryPill(doc, x, y, w, h, text) {
  doc.setFillColor(255, 255, 255);
  if (doc.setGState) doc.setGState(new doc.GState({ opacity: 0.22 }));
  doc.roundedRect(x, y, w, h, 3.5, 3.5, "F");
  if (doc.setGState) doc.setGState(new doc.GState({ opacity: 1 }));
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(6.8);
  doc.text(text, x + w / 2, y + 4.9, { align: "center" });
}

async function drawMiniSlot(doc, x, y, w, h, meal, items) {
  doc.setDrawColor(...PDF_LINE);
  doc.setFillColor(...PDF_BG);
  doc.roundedRect(x, y, w, h, 3, 3, "FD");

  doc.setTextColor(...PDF_GREEN_DARK);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(6.3);
  doc.text(`${meal.label}`, x + 2, y + 4.8);

  if (!items?.length) {
    doc.setTextColor(148, 163, 184);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.text("vuoto", x + w / 2, y + h / 2 + 2, { align: "center" });
    return;
  }

  const recipe = items[0].recipe;
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
  doc.setFontSize(6.45);
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
  doc.text(items.length > 1 ? `${items.length} ric.` : money(recipe.estimated_total), x + w - 4, y + h - 3.4, { align: "right" });
}

async function drawDayPage(doc, day) {
  const pageW = 210;
  const pageH = 297;
  const margin = 12;
  const gap = 6;
  const cardW = (pageW - margin * 2 - gap) / 2;
  const cardH = 109;
  const startY = 52;
  const pageDate = addDays(currentWeekStart, day.index);
  const entries = getDayItems(day.index, false);
  const filledCount = entries.reduce((sum, { items }) => sum + items.length, 0);
  const dayTotal = entries.reduce((sum, { items }) => sum + items.reduce((s, item) => s + Number(item?.recipe?.estimated_total || 0), 0), 0);

  doc.setFillColor(247, 252, 249);
  doc.rect(0, 0, pageW, pageH, "F");

  doc.setFillColor(...PDF_GREEN);
  doc.roundedRect(12, 10, pageW - 24, 26, 6, 6, "F");

  doc.setFillColor(255, 255, 255);
  if (doc.setGState) doc.setGState(new doc.GState({ opacity: 0.14 }));
  doc.circle(pageW - 28, 19, 15, "F");
  doc.circle(pageW - 12, 13, 7, "F");
  if (doc.setGState) doc.setGState(new doc.GState({ opacity: 1 }));

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text(day.label, 18, 21);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(fullDate(pageDate), 18, 28);

  drawHeaderMiniPill(doc, pageW - 69, 15, 25, 7, `${filledCount} ric.`);
  drawHeaderMiniPill(doc, pageW - 41, 15, 24, 7, money(dayTotal));

  if (!entries.length) {
    drawEmptyDayMessage(doc, pageW, pageH);
  }

  for (let i = 0; i < entries.length; i++) {
    const row = Math.floor(i / 2);
    const col = i % 2;
    const x = margin + col * (cardW + gap);
    const y = startY + row * (cardH + 8);
    await drawDayRecipeCard(doc, x, y, cardW, cardH, entries[i].meal, entries[i].items);
  }

  doc.setTextColor(...PDF_MUTED);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.text(`Pagina giorno - ${day.label}`, pageW / 2, pageH - 6, { align: "center" });
}

function drawEmptyDayMessage(doc, pageW, pageH) {
  doc.setFillColor(255, 255, 255);
  doc.setDrawColor(...PDF_LINE);
  doc.roundedRect(24, 86, pageW - 48, 74, 8, 8, "FD");
  doc.setTextColor(...PDF_MUTED);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.text("Nessuna ricetta pianificata", pageW / 2, 116, { align: "center" });
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text("Questo giorno resta libero nel menu settimanale.", pageW / 2, 128, { align: "center" });
}

function drawHeaderMiniPill(doc, x, y, w, h, text) {
  doc.setFillColor(255, 255, 255);
  if (doc.setGState) doc.setGState(new doc.GState({ opacity: 0.2 }));
  doc.roundedRect(x, y, w, h, 3, 3, "F");
  if (doc.setGState) doc.setGState(new doc.GState({ opacity: 1 }));
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(6.7);
  doc.text(text, x + w / 2, y + 4.8, { align: "center" });
}

async function drawDayRecipeCard(doc, x, y, w, h, meal, items) {
  doc.setFillColor(255, 255, 255);
  doc.setDrawColor(...PDF_LINE);
  doc.roundedRect(x, y, w, h, 6, 6, "FD");

  doc.setFillColor(...PDF_GREEN_SOFT);
  doc.roundedRect(x + 4, y + 4, 34, 8, 3, 3, "F");
  doc.setTextColor(...PDF_GREEN_DARK);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8.3);
  doc.text(`${meal.emoji} ${meal.label}`, x + 8, y + 9.2);

  const imageY = y + 16;
  const imageH = 48;
  doc.setFillColor(241, 245, 249);
  doc.roundedRect(x + 4, imageY, w - 8, imageH, 5, 5, "F");

  if (!items?.length) {
    return;
  }

  const recipe = items[0].recipe;
  const image = await loadPdfImage(recipe.image);
  if (image?.data) {
    try {
      doc.addImage(image.data, image.format, x + 4, imageY, w - 8, imageH, undefined, "FAST");
    } catch (err) {
      console.warn("PDF day image skipped", recipe.image, err);
    }
  }

  const textX = x + 5;
  let cursorY = imageY + imageH + 8;

  doc.setTextColor(...PDF_SLATE);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11.2);
  const titleLines = doc.splitTextToSize(recipe.name || "", w - 10).slice(0, 2);
  doc.text(titleLines, textX, cursorY);
  cursorY += 6.3 * titleLines.length + 1;

  const meta = [];
  if (recipe.prep_time_minutes) meta.push(`${recipe.prep_time_minutes} min`);
  meta.push(`${recipe.servings || 1} porz.`);
  meta.push(`${items.length} ricetta${items.length > 1 ? "e" : ""}`);
  meta.push(money(items.reduce((sum, item) => sum + Number(item?.recipe?.estimated_total || 0), 0)));

  drawInlineTags(doc, textX, cursorY, meta, w - 10);
  cursorY += 11;

  const menuNotes = items
    .map(item => item.notes ? `${item.recipe?.name || "Ricetta"}: ${item.notes}` : "")
    .filter(Boolean);

  if (menuNotes.length) {
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(textX - 1, cursorY - 4, w - 8, 18, 3, 3, "F");
    doc.setTextColor(...PDF_MUTED);
    doc.setFont("helvetica", "italic");
    doc.setFontSize(7.6);
    const noteLines = doc.splitTextToSize(menuNotes.join("  |  "), w - 12).slice(0, 3);
    doc.text(noteLines, textX + 1, cursorY + 1);
  }

  if (items.length > 1) {
    const extraNames = items.slice(1).map(item => `+ ${item.recipe?.name || "Ricetta"}`).join("  ");
    doc.setTextColor(...PDF_GREEN_DARK);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7.5);
    doc.text(doc.splitTextToSize(extraNames, w - 10).slice(0, 2), textX, y + h - 8);
  }
}

function drawInlineTags(doc, startX, y, tags, maxWidth) {
  let x = startX;
  for (const tag of tags) {
    const text = String(tag || "");
    const w = Math.min(34, Math.max(18, doc.getTextWidth(text) + 8));
    if (x + w > startX + maxWidth) break;
    doc.setFillColor(248, 250, 252);
    doc.setDrawColor(226, 232, 240);
    doc.roundedRect(x, y - 4.3, w, 6.8, 2.6, 2.6, "FD");
    doc.setTextColor(...PDF_MUTED);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(7);
    doc.text(text, x + w / 2, y, { align: "center" });
    x += w + 3;
  }
}

async function drawRecipeDetailsSection(doc, items) {
  const uniqueRecipes = dedupeRecipes(items.map(i => i.recipe).filter(Boolean));
  const notesByRecipeId = buildNotesByRecipeId(items);
  let pageIndex = 0;
  let y = 36;
  const pageW = 210;
  const pageH = 297;
  const cardH = 78;
  const gap = 7;

  renderRecipeSectionHeader(doc, pageIndex + 1);

  for (const recipe of uniqueRecipes) {
    if (y + cardH > 285) {
      doc.addPage("a4", "portrait");
      pageIndex += 1;
      renderRecipeSectionHeader(doc, pageIndex + 1);
      y = 36;
    }
    await drawRecipeDetailCard(doc, 12, y, pageW - 24, cardH, recipe, notesByRecipeId.get(recipe.id) || []);
    y += cardH + gap;
  }
}

function renderRecipeSectionHeader(doc, pageNumber) {
  const pageW = 210;
  const pageH = 297;
  doc.setFillColor(247, 252, 249);
  doc.rect(0, 0, pageW, pageH, "F");
  doc.setFillColor(...PDF_GREEN);
  doc.roundedRect(12, 10, pageW - 24, 18, 5, 5, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.text("Ingredienti ricetta per ricetta", 18, 22);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7.8);
  doc.text(`Sezione finale - pagina ${pageNumber}`, pageW - 18, 22, { align: "right" });
}

function dedupeRecipes(list) {
  const seen = new Set();
  const out = [];
  for (const recipe of list) {
    if (!recipe?.id || seen.has(recipe.id)) continue;
    seen.add(recipe.id);
    out.push(recipe);
  }
  return out;
}

function buildNotesByRecipeId(items) {
  const map = new Map();
  for (const item of items) {
    if (!item?.recipe?.id || !item.notes) continue;
    if (!map.has(item.recipe.id)) map.set(item.recipe.id, []);
    map.get(item.recipe.id).push(item.notes);
  }
  return map;
}

async function drawRecipeDetailCard(doc, x, y, w, h, recipe, menuNotes = []) {
  doc.setFillColor(255, 255, 255);
  doc.setDrawColor(...PDF_LINE);
  doc.roundedRect(x, y, w, h, 6, 6, "FD");

  const imgX = x + 5;
  const imgY = y + 6;
  const imgW = 45;
  const imgH = 45;

  doc.setFillColor(...PDF_GREEN_SOFT);
  doc.roundedRect(imgX, imgY, imgW, imgH, 4, 4, "F");
  const image = await loadPdfImage(recipe.image);
  if (image?.data) {
    try {
      doc.addImage(image.data, image.format, imgX, imgY, imgW, imgH, undefined, "FAST");
    } catch (err) {
      console.warn("PDF detail image skipped", recipe.image, err);
    }
  }

  const textX = x + 55;
  doc.setTextColor(...PDF_SLATE);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(11.8);
  doc.text(doc.splitTextToSize(recipe.name || "", w - 62).slice(0, 2), textX, y + 12);

  doc.setTextColor(...PDF_MUTED);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  const metaLine = `${recipe.items_count || 0} ingredienti - ${recipe.servings || 1} porzioni - ${recipe.prep_time_minutes ? `${recipe.prep_time_minutes} min - ` : ""}${money(recipe.estimated_total)}`;
  doc.text(metaLine, textX, y + 22);

  const ingredientLines = buildIngredientLines(recipe.items || []);
  doc.setTextColor(...PDF_SLATE);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8.1);
  doc.text(doc.splitTextToSize(ingredientLines.join("\\n"), w - 62).slice(0, 7), textX, y + 31);

  if (menuNotes.length) {
    doc.setFillColor(248, 250, 252);
    doc.roundedRect(x + 5, y + 56, w - 10, 16, 3, 3, "F");
    doc.setTextColor(...PDF_MUTED);
    doc.setFont("helvetica", "italic");
    doc.setFontSize(7.4);
    doc.text(doc.splitTextToSize(cleanSnippet(menuNotes.join(" | ")), w - 16).slice(0, 2), x + 8, y + 63);
  }
}

function buildIngredientLines(items) {
  if (!items.length) return ["- Nessun ingrediente salvato"];
  const lines = items.slice(0, 8).map(i => {
    const productName = i.product?.name || i.ingredient_name || "Ingrediente";
    const qty = i.cart_quantity || i.quantity || 1;
    const unit = i.unit || "";
    return `- ${productName} x ${qty}${unit ? ` ${unit}` : ""}`;
  });
  if (items.length > 8) lines.push(`- + altri ${items.length - 8} ingredienti`);
  return lines;
}

function cleanSnippet(text) {
  return String(text || "")
    .replace(/\s+/g, " ")
    .replace(/\\n+/g, " ")
    .trim();
}

const imageCache = new Map();

async function loadPdfImage(path) {
  if (!path) return null;

  const url = normalizeImageUrl(path);
  if (imageCache.has(url)) return imageCache.get(url);

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

    try {
      const parsed = new URL(url);
      if (parsed.origin !== window.location.origin) img.crossOrigin = "anonymous";
    } catch {}

    img.onload = () => {
      try {
        const size = 720;
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
        resolve(canvas.toDataURL("image/jpeg", 0.9));
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
