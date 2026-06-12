// Navigazione globale SmartGrocery + tab Admin desktop per utenti admin.

window.addEventListener("DOMContentLoaded", () => {
  ensureHistoryNavButton();
  ensureAdminNavButton();

  const current = document.body.dataset.page;
  document.querySelectorAll(".nav-pill").forEach(btn => {
    if (btn.dataset.tab === current) btn.classList.add("active");
  });
});

function decodeJwtPayload(token) {
  if (!token || !token.includes(".")) return {};
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(payload).split("").map(c => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2)).join("")
    );
    return JSON.parse(json);
  } catch {
    return {};
  }
}

function currentUserRole() {
  const token = localStorage.getItem("token");
  const payload = decodeJwtPayload(token);
  return payload.role || payload.user_role || "";
}

function ensureHistoryNavButton() {
  const nav = document.querySelector(".header-right");
  if (!nav || nav.querySelector('[data-tab="history"]')) return;

  const btn = document.createElement("button");
  btn.className = "nav-pill";
  btn.dataset.tab = "history";
  btn.textContent = "Storico";
  btn.onclick = () => navigate("history");

  const recipes = nav.querySelector('[data-tab="recipes"]');
  if (recipes) nav.insertBefore(btn, recipes);
  else nav.appendChild(btn);
}

function ensureAdminNavButton() {
  const nav = document.querySelector(".header-right");
  if (!nav || nav.querySelector('[data-tab="admin"]')) return;
  if (currentUserRole() !== "admin") return;

  const btn = document.createElement("button");
  btn.className = "nav-pill admin-nav-pill";
  btn.dataset.tab = "admin";
  btn.textContent = "Admin";
  btn.onclick = () => navigate("admin");

  nav.appendChild(btn);
}

function navigate(tab) {
  if (tab === "home") window.location.href = "dashboard.html";
  if (tab === "list") window.location.href = "shopping-list.html";
  if (tab === "products") window.location.href = "products.html";
  if (tab === "history") window.location.href = "history.html";
  if (tab === "recipes") window.location.href = "recipes.html";
  if (tab === "supermarkets") window.location.href = "supermarkets.html";
  if (tab === "profile") window.location.href = "profile.html";
  if (tab === "admin") window.location.href = "admin.html";
}
