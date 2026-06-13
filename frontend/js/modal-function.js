function formatEuro(value) {
  return Number(value || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function parseFlyerSourceDates(source) {
  const text = String(source || "");
  const match = text.match(/(\d{4})[_-](\d{2})[_-](\d{2}).*?(\d{4})[_-](\d{2})[_-](\d{2})/);
  if (!match) return { from: null, to: null };
  return { from: `${match[1]}-${match[2]}-${match[3]}`, to: `${match[4]}-${match[5]}-${match[6]}` };
}

function flyerDates(item) {
  const parsed = parseFlyerSourceDates(item.flyer_source || item.offer_note || "");
  return {
    from: item.flyer_valid_from || parsed.from,
    to: item.flyer_valid_to || parsed.to,
  };
}

function isOfferActive(item) {
  const { to } = flyerDates(item);
  if (!to) return true;
  const end = new Date(`${to}T23:59:59`);
  if (Number.isNaN(end.getTime())) return true;
  return end >= new Date();
}

function hasDiscount(item) {
  return isOfferActive(item) && Number(item.discounted_price) > 0 && Number(item.discounted_price) < Number(item.original_price);
}

function discountPercent(item) {
  if (item.discount_percent) return Math.round(Number(item.discount_percent));
  if (!hasDiscount(item)) return 0;
  return Math.round((1 - Number(item.discounted_price) / Number(item.original_price)) * 100);
}

export function openProductModal(item, supermarket = {}) {
  document.getElementById("modal-image").src = item.image || "/static/images/placeholder.jpg";
  document.getElementById("modal-category").textContent = item.category || "Prodotto";
  document.getElementById("modal-name").textContent = item.name || "Prodotto";
  document.getElementById("modal-store").textContent = supermarket.name || "Negozio";
  document.getElementById("modal-location").textContent = item.location || "Non indicata";

  const lidlPlus = document.getElementById("modal-lidl-plus");
  lidlPlus.classList.toggle("hidden", !(hasDiscount(item) && item.is_lidl_plus));

  const sale = hasDiscount(item);
  if (sale) {
    document.getElementById("modal-price").innerHTML = `
      <span class="discounted">${formatEuro(item.original_price)}</span>
      <span class="final-price">${formatEuro(item.discounted_price)}</span>
    `;
    const badge = document.getElementById("modal-discount-badge");
    badge.textContent = `-${discountPercent(item)}%`;
    badge.classList.remove("hidden");
  } else {
    document.getElementById("modal-price").innerHTML = `<span class="final-price">${formatEuro(item.original_price)}</span>`;
    document.getElementById("modal-discount-badge").classList.add("hidden");
  }

  const flyerBox = document.getElementById("modal-flyer-box");
  const page = sale && item.flyer_page ? Number(item.flyer_page) : null;
  const dates = sale ? flyerDates(item) : { from: null, to: null };
  const hasFlyerInfo = sale && Boolean(page || dates.from || dates.to || item.is_lidl_plus);

  if (hasFlyerInfo) {
    flyerBox.classList.remove("hidden");
    document.getElementById("modal-flyer-page").textContent = page ? `Pagina ${page}` : "Pagina non indicata";
    const from = formatDate(dates.from);
    const to = formatDate(dates.to);
    document.getElementById("modal-flyer-validity").textContent = from && to ? `${from} – ${to}` : to ? `fino al ${to}` : "Data del volantino non salvata";
  } else {
    flyerBox.classList.add("hidden");
  }

  const grid = document.getElementById("modal-nutrition-grid");
  grid.innerHTML = "";

  const cards = [
    { label: "Calorie", value: item.calories, unit: "kcal" },
    { label: "Grassi", value: item.fat, unit: "g" },
    { label: "Carboidrati", value: item.carbs, unit: "g" },
    { label: "Proteine", value: item.protein, unit: "g" },
  ];

  cards.forEach((c) => {
    const div = document.createElement("div");
    div.className = "nutri-card";
    div.innerHTML = `
      <div class="nutri-label">${c.label}</div>
      <div class="nutri-value">${c.value ?? "-"} ${c.unit}</div>
    `;
    grid.appendChild(div);
  });

  document.getElementById("product-modal").classList.remove("hidden");
}

export function closeModal() {
  document.getElementById("product-modal")?.classList.add("hidden");
}
