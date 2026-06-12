import CONFIG from "./config.js";

const token = localStorage.getItem("token");
if (!token) window.location.href = "index.html";

const euro = (v) => Number(v || 0).toLocaleString("it-IT", { style: "currency", currency: "EUR" });
const dateFmt = (v) => v ? new Date(v).toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", year: "numeric" }) : "—";

function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2400);
}

async function loadProfile() {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/profile/summary`);
  if (!res?.ok) return toast("Non riesco a caricare il profilo");
  const data = await res.json();
  renderProfile(data);
}

function renderProfile(data) {
  const u = data.user || {};
  const display = [u.first_name, u.last_name].filter(Boolean).join(" ") || u.username || "Profilo";
  document.getElementById("profile-title").textContent = display;
  document.getElementById("profile-subtitle").textContent = u.email || "Account SmartGrocery";
  document.getElementById("profile-avatar").textContent = (u.first_name || u.username || "S")[0].toUpperCase();

  document.getElementById("first-name").value = u.first_name || "";
  document.getElementById("last-name").value = u.last_name || "";
  document.getElementById("username").value = u.username || "";
  document.getElementById("email").value = u.email || "";

  document.getElementById("stat-total-spent").textContent = euro(data.history?.total_spent || 0);
  document.getElementById("stat-trips").textContent = data.history?.trips_count || 0;
  document.getElementById("stat-cart").textContent = euro(data.cart?.estimated_total || 0);
  document.getElementById("stat-recipes").textContent = data.library?.recipes_count || 0;

  const cats = data.top_categories || [];
  document.getElementById("top-categories").innerHTML = cats.length ? cats.map(c => `
    <div class="cat-pill"><span>${c.category}</span><strong>${c.quantity}</strong></div>
  `).join("") : `<div class="cat-pill"><span>Nessuna categoria ancora</span><strong>—</strong></div>`;

  const latest = data.history?.latest || [];
  document.getElementById("latest-trips").innerHTML = latest.length ? latest.map(h => `
    <div class="trip-row">
      <div><b>Spesa #${h.id}</b><span>${dateFmt(h.created_at)} · ${h.total_items} prodotti</span></div>
      <div class="trip-price">${euro(h.total_price)}</div>
    </div>
  `).join("") : `<div class="trip-row"><div><b>Nessuna spesa finalizzata</b><span>Quando finalizzi una lista, comparirà qui.</span></div></div>`;
}

document.getElementById("profile-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const payload = {
    first_name: document.getElementById("first-name").value.trim(),
    last_name: document.getElementById("last-name").value.trim(),
    username: document.getElementById("username").value.trim(),
  };
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/profile`, { method: "PUT", body: JSON.stringify(payload) });
  if (!res?.ok) return toast("Errore salvataggio profilo");
  toast("Profilo aggiornato");
  loadProfile();
});

document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("token");
  window.location.href = "index.html";
});

loadProfile();
