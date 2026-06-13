
import CONFIG from "./config.js";

const adminRoleToken = localStorage.getItem("token");

async function loadAdminRole() {
  const hero = document.querySelector(".admin-hero");
  if (!hero || document.getElementById("admin-role-card")) return;

  const card = document.createElement("div");
  card.id = "admin-role-card";
  card.className = "admin-role-card";
  card.innerHTML = `<small>Ruolo corrente</small><strong>Caricamento...</strong><p>Controllo permessi admin</p>`;
  hero.appendChild(card);

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/profile/role`, {
      headers: { Authorization: `Bearer ${adminRoleToken}` },
    });
    if (!res.ok) throw new Error("role endpoint not available");
    const data = await res.json();
    const isAdmin = data.role === "admin" || data.is_admin;
    card.classList.toggle("is-admin", isAdmin);
    card.innerHTML = `
      <small>Ruolo corrente</small>
      <strong>${isAdmin ? "Admin" : "Utente"}</strong>
      <p>${data.username || data.email || ""} · DB: ${data.db_role || data.role || "n/d"} · Token: ${data.token_role || "n/d"}</p>
    `;
  } catch {
    card.innerHTML = `<small>Ruolo corrente</small><strong>Non disponibile</strong><p>Endpoint /profile/role non raggiungibile.</p>`;
  }
}

document.addEventListener("DOMContentLoaded", loadAdminRole);
