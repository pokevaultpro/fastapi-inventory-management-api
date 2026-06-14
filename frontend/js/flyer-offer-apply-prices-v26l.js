import CONFIG from "./config.js";

const token = () => localStorage.getItem("token");

function activeFlyerId() {
  const active = document.querySelector(".flyer-card.active[data-flyer]");
  return active ? Number(active.dataset.flyer) : null;
}

async function readError(res) {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    return JSON.stringify(data);
  } catch {
    return res.statusText || "Errore";
  }
}

function injectPriceBox() {
  if (document.getElementById("applyFlyerPricesBoxV26L")) return;

  const panel = document.querySelector(".filters")?.parentElement;
  if (!panel) return;

  const box = document.createElement("section");
  box.id = "applyFlyerPricesBoxV26L";
  box.className = "apply-prices-box-v26l";
  box.innerHTML = `
    <div>
      <strong>Prezzi offerta nei prodotti</strong>
      <p>
        Dopo aver approvato/associato le offerte, usa questo bottone per scrivere nei Products:
        original_price = prezzo barrato/catalogo, discounted_price = prezzo volantino.
      </p>
    </div>
    <button id="publishApplyPricesBtnV26L" class="primary" type="button">Pubblica + applica prezzi</button>
    <button id="applyPricesBtnV26L" class="secondary" type="button">Solo applica prezzi</button>
    <pre id="applyPricesOutputV26L" class="apply-prices-output-v26l">Seleziona un volantino.</pre>
  `;

  panel.insertBefore(box, document.querySelector(".bulkbar"));

  document.getElementById("publishApplyPricesBtnV26L").addEventListener("click", () => runApply(true));
  document.getElementById("applyPricesBtnV26L").addEventListener("click", () => runApply(false));
}

async function runApply(publishFirst) {
  const flyerId = activeFlyerId();
  const output = document.getElementById("applyPricesOutputV26L");
  if (!flyerId) {
    alert("Seleziona prima un volantino.");
    return;
  }

  const endpoint = publishFirst
    ? `/admin/flyer-offer-prices/publish-and-apply/${flyerId}`
    : `/admin/flyer-offer-prices/apply/${flyerId}`;

  output.textContent = publishFirst
    ? "Pubblicazione e applicazione prezzi in corso..."
    : "Applicazione prezzi in corso...";

  const res = await fetch(`${CONFIG.API_BASE_URL}${endpoint}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token()}` },
  });

  if (res.status === 401) {
    localStorage.removeItem("token");
    window.location.href = "index.html";
    return;
  }

  if (!res.ok) {
    output.textContent = await readError(res);
    return;
  }

  const data = await res.json();
  output.textContent = JSON.stringify(data, null, 2);
  alert(`OK: ${data.applied ?? 0} prodotti aggiornati con prezzo offerta.`);
}

document.addEventListener("DOMContentLoaded", injectPriceBox);
setTimeout(injectPriceBox, 600);
