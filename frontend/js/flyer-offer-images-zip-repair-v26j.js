import CONFIG from "./config.js";

const token = () => localStorage.getItem("token");

function activeFlyerId() {
  const active = document.querySelector(".flyer-card.active[data-flyer]");
  return active ? Number(active.dataset.flyer) : null;
}

async function readError(res) {
  try {
    const data = await res.json();
    return typeof data.detail === "string" ? data.detail : JSON.stringify(data);
  } catch {
    return res.statusText || "Errore";
  }
}

function injectZipRepairBox() {
  if (document.getElementById("zipImageRepairBox")) return;

  const panel = document.querySelector(".filters")?.parentElement;
  if (!panel) return;

  const box = document.createElement("section");
  box.id = "zipImageRepairBox";
  box.className = "zip-repair-box";
  box.innerHTML = `
    <div>
      <strong>Ripara immagini prodotti da ZIP</strong>
      <p>
        Usa lo stesso ZIP del volantino. Serve quando Render ha perso i crop in /static/images/flyer_offers dopo un redeploy.
        Il prodotto verrà aggiornato con /static/images/products/...
      </p>
    </div>
    <input id="zipImageRepairFile" type="file" accept=".zip,application/zip">
    <label class="repair-check"><input id="zipImageRepairForce" type="checkbox" checked> forza riparazione</label>
    <button id="zipImageRepairBtn" class="primary" type="button">Ripara da ZIP</button>
    <pre id="zipImageRepairOutput" class="zip-repair-output">Seleziona il volantino, poi carica lo ZIP.</pre>
  `;

  panel.insertBefore(box, document.querySelector(".bulkbar"));

  document.getElementById("zipImageRepairBtn").addEventListener("click", repairFromZip);
}

async function repairFromZip() {
  const file = document.getElementById("zipImageRepairFile")?.files?.[0];
  if (!file) return alert("Seleziona lo ZIP del volantino.");

  const flyerId = activeFlyerId();
  if (!flyerId && !confirm("Nessun volantino selezionato. Vuoi riparare globalmente i prodotti Conad da questo ZIP?")) {
    return;
  }

  const force = Boolean(document.getElementById("zipImageRepairForce")?.checked);
  const output = document.getElementById("zipImageRepairOutput");
  const btn = document.getElementById("zipImageRepairBtn");

  const form = new FormData();
  form.append("file", file);
  if (flyerId) form.append("flyer_id", String(flyerId));
  form.append("force", String(force));

  output.textContent = `Upload e riparazione in corso: ${file.name}...`;
  btn.disabled = true;
  btn.textContent = "Riparo...";

  try {
    const res = await fetch(`${CONFIG.API_BASE_URL}/admin/flyer-offer-images/repair-from-zip`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token()}`,
      },
      body: form,
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
    output.textContent = [
      `OK: ${data.total_repaired} prodotti riparati`,
      `ZIP products: ${data.zip_products}`,
      `Linked checked: ${data.linked_checked}`,
      `Linked repaired: ${data.linked_repaired}`,
      `Loose checked: ${data.loose_checked}`,
      `Loose repaired: ${data.loose_repaired}`,
      `Not found linked: ${data.linked_not_found_in_zip}`,
      `Missing image linked: ${data.linked_missing_zip_image}`,
      "",
      "Risposta completa:",
      JSON.stringify(data, null, 2),
    ].join("\n");

    alert(`Riparazione completata: ${data.total_repaired} prodotti aggiornati.`);
  } catch (err) {
    output.textContent = err?.message || "Errore durante riparazione.";
  } finally {
    btn.disabled = false;
    btn.textContent = "Ripara da ZIP";
  }
}

document.addEventListener("DOMContentLoaded", injectZipRepairBox);
setTimeout(injectZipRepairBox, 500);
