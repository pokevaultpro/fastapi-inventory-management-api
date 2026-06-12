import CONFIG from "./config.js";

(function () {
  const token = localStorage.getItem("token");

  function decodeJwtPayload(token) {
    if (!token || !token.includes(".")) return {};
    try {
      const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
      const json = decodeURIComponent(
        atob(payload)
          .split("")
          .map(c => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
          .join("")
      );
      return JSON.parse(json);
    } catch {
      return {};
    }
  }

  function getTokenRole() {
    const payload = decodeJwtPayload(token);
    return payload.role || payload.user_role || "user";
  }

  async function fetchCurrentRole() {
    if (!token) return { role: "guest", is_admin: false, source: "none" };

    try {
      const res = await fetch(`${CONFIG.API_BASE_URL}/profile/role`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const data = await res.json();
        return { ...data, source: "database" };
      }
    } catch {
      // fallback below
    }

    const role = getTokenRole();
    return { role, is_admin: role === "admin", source: "token" };
  }

  function injectStyle() {
    if (document.getElementById("profile-role-badge-style")) return;

    const style = document.createElement("style");
    style.id = "profile-role-badge-style";
    style.textContent = `
      .profile-role-card {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
        padding: 16px 18px;
        margin: 0 0 18px;
        border-radius: 24px;
        border: 1px solid rgba(226, 232, 240, 0.95);
        background:
          radial-gradient(circle at top left, rgba(34,197,94,.13), transparent 34%),
          linear-gradient(135deg, rgba(255,255,255,.95), rgba(248,250,252,.95));
        box-shadow: 0 18px 50px rgba(15,23,42,.08);
      }

      .profile-role-left {
        display: flex;
        align-items: center;
        gap: 13px;
      }

      .profile-role-icon {
        width: 48px;
        height: 48px;
        border-radius: 18px;
        display: grid;
        place-items: center;
        font-size: 24px;
        background: #0f172a;
        color: #fff;
        box-shadow: 0 14px 32px rgba(15,23,42,.18);
      }

      .profile-role-card p {
        margin: 0;
        color: #64748b;
        font-size: 13px;
        font-weight: 800;
      }

      .profile-role-card h3 {
        margin: 2px 0 0;
        font-size: 21px;
        letter-spacing: -.035em;
        color: #0f172a;
      }

      .profile-role-pill {
        border: 0;
        border-radius: 999px;
        padding: 10px 14px;
        font-weight: 950;
        letter-spacing: .02em;
        text-transform: uppercase;
        font-size: 12px;
        white-space: nowrap;
      }

      .profile-role-pill.admin {
        background: #dcfce7;
        color: #166534;
        border: 1px solid rgba(22,101,52,.18);
      }

      .profile-role-pill.user {
        background: #e0f2fe;
        color: #075985;
        border: 1px solid rgba(7,89,133,.18);
      }

      .profile-role-note {
        margin-top: 7px !important;
        font-size: 12px !important;
        color: #94a3b8 !important;
        font-weight: 700 !important;
      }

      @media (max-width: 720px) {
        .profile-role-card {
          margin: 12px 12px 18px;
          border-radius: 22px;
          align-items: flex-start;
        }

        .profile-role-card h3 {
          font-size: 18px;
        }

        .profile-role-pill {
          padding: 9px 11px;
          font-size: 11px;
        }

        .profile-role-icon {
          width: 44px;
          height: 44px;
          border-radius: 16px;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function findProfileContainer() {
    return (
      document.querySelector(".profile-page") ||
      document.querySelector("main") ||
      document.querySelector(".page-content") ||
      document.body
    );
  }

  function renderRoleCard(roleData) {
    injectStyle();

    const role = String(roleData.role || "user").toLowerCase();
    const isAdmin = role === "admin";
    const label = isAdmin ? "Admin" : "Utente";
    const icon = isAdmin ? "🛠️" : "👤";
    const subtitle = isAdmin
      ? "Hai accesso alla pagina Admin e alla gestione del database."
      : "Account standard: puoi gestire lista, storico, ricette e preferiti.";

    let card = document.getElementById("profile-role-card");
    if (!card) {
      card = document.createElement("section");
      card.id = "profile-role-card";
      card.className = "profile-role-card";

      const container = findProfileContainer();
      const firstSection = container.querySelector("section") || container.firstElementChild;
      if (firstSection && firstSection !== card) container.insertBefore(card, firstSection.nextSibling);
      else container.prepend(card);
    }

    const sourceNote = roleData.source === "database"
      ? "Ruolo letto dal database."
      : "Ruolo letto dal token: se hai appena cambiato ruolo, fai logout/login.";

    card.innerHTML = `
      <div class="profile-role-left">
        <div class="profile-role-icon">${icon}</div>
        <div>
          <p>Ruolo account</p>
          <h3>${label}</h3>
          <p class="profile-role-note">${sourceNote}</p>
        </div>
      </div>
      <span class="profile-role-pill ${isAdmin ? "admin" : "user"}">${label}</span>
    `;
  }

  document.addEventListener("DOMContentLoaded", async () => {
    renderRoleCard({ role: getTokenRole(), source: "token" });
    const roleData = await fetchCurrentRole();
    renderRoleCard(roleData);
  });
})();
