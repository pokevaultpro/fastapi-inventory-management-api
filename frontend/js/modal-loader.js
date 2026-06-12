import { closeModal } from "./modal-function.js";

(function injectModal() {
  const modalHTML = `
<div id="product-modal" class="modal hidden">
  <div class="modal-backdrop" id="modal-backdrop"></div>
  <div class="modal-content">
    <div id="modal-discount-badge" class="modal-discount-badge hidden"></div>
    <button class="modal-x" id="modal-x" type="button" aria-label="Chiudi">×</button>
    <img id="modal-image" class="modal-img" alt="Prodotto">

    <div class="modal-body">
      <div class="modal-tags-row">
        <span id="modal-category" class="modal-tag"></span>
        <span id="modal-lidl-plus" class="modal-tag amber hidden">Lidl Plus</span>
      </div>
      <h2 id="modal-name" class="modal-title"></h2>
      <div class="modal-price" id="modal-price"></div>

      <div id="modal-flyer-box" class="modal-flyer-box hidden">
        <div>
          <span class="modal-flyer-label">Volantino</span>
          <strong id="modal-flyer-page">Pagina —</strong>
        </div>
        <div>
          <span class="modal-flyer-label">Validità</span>
          <strong id="modal-flyer-validity">—</strong>
        </div>
      </div>

      <div class="modal-sections">
        <div class="modal-section">
          <div class="modal-section-title">Negozio</div>
          <div class="modal-section-value" id="modal-store"></div>
        </div>
        <div class="modal-section">
          <div class="modal-section-title">Posizione</div>
          <div class="modal-section-value" id="modal-location"></div>
        </div>
      </div>

      <div class="modal-nutrition">
        <h3 class="nutrition-title">Valori nutrizionali</h3>
        <div class="nutrition-grid" id="modal-nutrition-grid"></div>
      </div>

      <button class="modal-close" id="modal-close-btn">Chiudi</button>
    </div>
  </div>
</div>`;

  document.body.insertAdjacentHTML("beforeend", modalHTML);
  document.getElementById("modal-backdrop").addEventListener("click", closeModal);
  document.getElementById("modal-close-btn").addEventListener("click", closeModal);
  document.getElementById("modal-x").addEventListener("click", closeModal);
})();
