// Attiva automaticamente il tab corretto e aggiunge il tab Storico sulle pagine vecchie.
window.addEventListener("DOMContentLoaded", () => {
  ensureHistoryNavButton();

  const current = document.body.dataset.page;
  const links = document.querySelectorAll(".nav-pill");

  links.forEach(btn => {
    if (btn.dataset.tab === current) {
      btn.classList.add("active");
    }
  });
});

function ensureHistoryNavButton() {
  const nav = document.querySelector(".header-right");
  if (!nav || nav.querySelector('[data-tab="history"]')) return;

  const btn = document.createElement("button");
  btn.className = "nav-pill";
  btn.dataset.tab = "history";
  btn.textContent = "Storico";
  btn.onclick = () => navigate("history");

  const profile = nav.querySelector('[data-tab="profile"]');
  if (profile) nav.insertBefore(btn, profile);
  else nav.appendChild(btn);
}

// Navigazione tra pagine
function navigate(tab) {
  if (tab === "home") window.location.href = "dashboard.html";
  if (tab === "list") window.location.href = "shopping-list.html";
  if (tab === "products") window.location.href = "products.html";
  if (tab === "history") window.location.href = "history.html";
  if (tab === "recipes") window.location.href = "recipes.html";
  if (tab === "supermarkets") window.location.href = "supermarkets.html";
  if (tab === "profile") window.location.href = "profile.html";
}
