import CONFIG from "./config.js";

(function () {
  function getToken() {
    return localStorage.getItem("token");
  }

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

  function tokenRole() {
    const payload = decodeJwtPayload(getToken());
    return payload.role || payload.user_role || "user";
  }

  function addStyles() {
    if (document.getElementById("profile-role-v14-style")) return;
    const style = document.createElement("style");
    style.id = "profile-role-v14-style";
    style.textContent = `
      .profile-role-v14 {
        width: min(1180px, calc(100% - 32px));
        margin: 18px auto;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 18px;
        padding: 18px 20px;
        border-radius: 26px;
        border: 1px solid rgba(226, 232, 240, 0.95);
        background: radial-gradient(circle at 0% 0%, rgba(34,197,94,.16), transparent 35%), linear-gradient(135deg, rgba(255,255,255,.98), rgba(248,250,252,.96));
        box-shadow: 0 18px 55px rgba(15,23,42,.10);
        position: relative;
        z-index: 5;
      }
      .profile-role-v14-left { display:flex; align-items:center; gap:14px; }
      .profile-role-v14-icon { width:54px; height:54px; border-radius:20px; display:grid; place-items:center; background:#0f172a; color:white; font-size:26px; box-shadow:0 12px 35px rgba(15,23,42,.18); }
      .profile-role-v14 small { display:block; margin-bottom:3px; color:#64748b; font-weight:900; text-transform:uppercase; letter-spacing:.09em; font-size:11px; }
      .profile-role-v14 h3 { margin:0; color:#0f172a; font-size:23px; letter-spacing:-.04em; }
      .profile-role-v14 p { margin:4px 0 0; color:#64748b; font-size:13px; font-weight:700; }
      .profile-role-v14-badge { border-radius:999px; padding:11px 15px; font-size:12px; text-transform:uppercase; letter-spacing:.04em; font-weight:950; white-space:nowrap; }
      .profile-role-v14-badge.admin { color:#166534; background:#dcfce7; border:1px solid rgba(22,101,52,.18); }
      .profile-role-v14-badge.user { color:#075985; background:#e0f2fe; border:1px solid rgba(7,89,133,.18); }
      @media (max-width:720px){
        .profile-role-v14{width:calc(100% - 24px); margin:12px auto 16px; padding:15px; border-radius:22px; align-items:flex-start;}
        .profile-role-v14-icon{width:48px;height:48px;border-radius:18px;font-size:23px;}
        .profile-role-v14 h3{font-size:19px;}
        .profile-role-v14-badge{padding:9px 11px;font-size:11px;}
      }
    `;
    document.head.appendChild(style);
  }

  function ensureCard() {
    addStyles();
    let card = document.getElementById("profile-role-v14");
    if (card) return card;

    card = document.createElement("section");
    card.id = "profile-role-v14";
    card.className = "profile-role-v14";

    const main = document.querySelector("main") || document.querySelector(".profile-page") || document.body;
    if (main.firstElementChild) main.insertBefore(card, main.firstElementChild.nextSibling);
    else main.prepend(card);

    return card;
  }

  function render(data) {
    const role = String(data?.role || "user").toLowerCase();
    const isAdmin = role === "admin";
    const label = isAdmin ? "Admin" : "Utente";
    const card = ensureCard();

    const detail = isAdmin ? "Hai accesso alla pagina Admin." : "Non sei admin: la pagina Admin resta bloccata.";
    const source = data?.db_role
      ? `Database: ${data.db_role}${data.token_role ? ` · Token: ${data.token_role}` : ""}`
      : "Se hai appena cambiato ruolo, fai logout/login.";

    card.innerHTML = `
      <div class="profile-role-v14-left">
        <div class="profile-role-v14-icon">${isAdmin ? "🛠️" : "👤"}</div>
        <div>
          <small>Ruolo account</small>
          <h3>${label}</h3>
          <p>${detail} <span>${source}</span></p>
        </div>
      </div>
      <span class="profile-role-v14-badge ${isAdmin ? "admin" : "user"}">${label}</span>
    `;
  }

  async function loadRole() {
    render({ role: tokenRole() });

    const token = getToken();
    if (!token) return;

    try {
      const res = await fetch(`${CONFIG.API_BASE_URL}/profile/role`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) render(await res.json());
    } catch {}
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", loadRole);
  else loadRole();
})();
