import CONFIG from "./config.js";
import { openProductModal } from "./modal-function.js";

document.addEventListener("DOMContentLoaded", async () => {
  await Promise.all([
    loadProducts(),
    loadFavorites()
  ]);

  renderProducts();

  if (window.innerWidth < 480) {
    updateVisibleRange();
  }
});


    let allProducts = [];
    let supermarkets = [];
    let currentCategory = "all";
    let currentStore = "all";
    let favorites = [];
    let visibleStart = 0;
    let visibleEnd = 0;

    let CARD_HEIGHT = 260; // desktop
    let CARD_HEIGHT_MOBILE = 338; // mobile
    let BUFFER = 10; // quante card extra mostrare
    let filtered = [];

    let currentPage = 1;
const PAGE_SIZE = 20;

async function toggleFavorite(id) {
  if (favorites.includes(id)) {
    // DELETE
await apiFetch(`${CONFIG.API_BASE_URL}/favorite/${id}`, {
  method: "DELETE",
  headers: {
    "Authorization": "Bearer " + localStorage.getItem("token")
  }
});

    favorites = favorites.filter(f => f !== id);
  } else {
    // POST
await apiFetch(`${CONFIG.API_BASE_URL}/favorite`, {
  method: "POST",
  headers: {
    "Authorization": "Bearer " + localStorage.getItem("token"),
    "Content-Type": "application/json"
  },
  body: JSON.stringify({ product_id: id })
});

    favorites.push(id);
  }

  renderProducts();
  updateVisibleRange();
}


    const params = new URLSearchParams(window.location.search);
    if (params.get("sale") === "1") {
      currentCategory = "sale";

      // attiva la pillola "Offerte"
      document.querySelectorAll(".cat-pill").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.cat === "sale");
      });
    }
async function loadFavorites() {
  const res = await apiFetch(`${CONFIG.API_BASE_URL}/favorite`, {
    headers: {
      "Authorization": "Bearer " + localStorage.getItem("token")
    }
  });

  favorites = res.ok ? await res.json() : [];
}


    async function loadProducts() {
      const [prodRes, supRes] = await Promise.all([
        apiFetch(`${CONFIG.API_BASE_URL}/product`),
        apiFetch(`${CONFIG.API_BASE_URL}/supermarket`)
      ]);

      allProducts = prodRes.ok ? await prodRes.json() : [];
      supermarkets = supRes.ok ? await supRes.json() : [];

      populateStoreFilter();


      renderProducts();
    }

    document.getElementById("search-input")
      .addEventListener("input", renderProducts);
    document.getElementById("store-filter")
      .addEventListener("change", setStoreFilter);
    document.querySelectorAll(".cat-pill").forEach(btn => {
      btn.addEventListener("click", () => {
        const cat = btn.dataset.cat;
        setCategory(cat);
      });
    });



    function setCategory(cat) {
      currentCategory = cat;

      document.querySelectorAll(".cat-pill").forEach(btn => {
        btn.classList.toggle("active", btn.dataset.cat === cat);
      });

      renderProducts();
    }

 function renderProducts() {
  const search = document.getElementById("search-input").value.toLowerCase();

  // 1. FILTRO
  filtered = allProducts.filter(p => {
    const matchesSearch = p.name.toLowerCase().includes(search);
    const matchesCategory =
      currentCategory === "all" ||
      (currentCategory === "sale" && p.discounted_price !== null) ||
      (currentCategory === "favorites" && favorites.includes(p.id)) ||
      p.category === currentCategory;

    const matchesStore =
      currentStore === "all" ||
      p.supermarket_id == currentStore;

    return matchesSearch && matchesCategory && matchesStore;
  });

  // 2. ORDINAMENTO
  if (currentStore === "all") {
    filtered.sort((a, b) => a.name.localeCompare(b.name));
  } else {
    filtered.sort((a, b) => (a.aisle_order ?? 9999) - (b.aisle_order ?? 9999));
  }

  // 3. CARD HEIGHT
  const isMobile = window.innerWidth < 480;
  const cardHeight = isMobile ? CARD_HEIGHT_MOBILE : CARD_HEIGHT;

  // 4. VIRTUAL CONTAINER HEIGHT
  const container = document.getElementById("virtual-container");

  // 5. SPAZIO SOPRA PER STICKY
  const sticky = document.querySelector(".sticky-header");
  const stickyHeight = sticky ? sticky.offsetHeight : 0;
  document.getElementById("spacer-top").style.height = stickyHeight + "px";

if (isMobile) {
  container.style.height = filtered.length * cardHeight + "px";
  updateVisibleRange();
} else {
  renderDesktopPaged();
}
}

function updateVisibleRange() {
  const viewportHeight = window.innerHeight;
  const isMobile = window.innerWidth < 480;
  const cardHeight = isMobile ? CARD_HEIGHT_MOBILE : CARD_HEIGHT;

  // scroll effettivo (non serve topOffset per la prima card)
  const scrollTop = window.scrollY;

  visibleStart = Math.floor(scrollTop / cardHeight);
  visibleEnd = Math.min(
    filtered.length,
    Math.ceil((scrollTop + viewportHeight) / cardHeight) + BUFFER
  );

  renderVirtualProducts();
}

function renderVirtualProducts() {
  const grid = document.getElementById("products-grid");
  [...grid.querySelectorAll(".product-card")].forEach(el => el.remove());

  const isMobile = window.innerWidth < 480;
  const cardHeight = isMobile ? CARD_HEIGHT_MOBILE : CARD_HEIGHT;

  filtered.slice(visibleStart, visibleEnd).forEach((p, i) => {
    const realIndex = visibleStart + i;
    const card = createProductCard(p);

    card.style.position = "absolute";
    card.style.top = realIndex * cardHeight + "px"; // NIENTE offset sulla prima card
    card.style.left = "0";
    card.style.right = "0";

    grid.appendChild(card);
  });
}

function renderDesktopPaged() {
  const grid = document.getElementById("products-grid");
  grid.innerHTML = "";

  const start = (currentPage - 1) * PAGE_SIZE;
  const end = start + PAGE_SIZE;

  const pageItems = filtered.slice(start, end);

  pageItems.forEach(p => {
    const card = createProductCard(p);
    grid.appendChild(card);
  });

  renderPagination();
}

function renderPagination() {
  let pager = document.getElementById("pagination");

  if (!pager) {
    pager = document.createElement("div");
    pager.id = "pagination";
    pager.className = "pagination-bar";
    document.querySelector(".products-page").appendChild(pager);
  }

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const windowSize = 5;

  let start = Math.max(1, currentPage - Math.floor(windowSize / 2));
  let end = start + windowSize - 1;

  if (end > totalPages) {
    end = totalPages;
    start = Math.max(1, end - windowSize + 1);
  }

  pager.innerHTML = "";

  if (currentPage > 1) {
    pager.appendChild(createPageBtn("←", currentPage - 1));
  }

  if (start > 1) {
    pager.appendChild(createPageBtn("1"));
    if (start > 2) pager.appendChild(dots());
  }

  for (let i = start; i <= end; i++) {
    pager.appendChild(createPageBtn(i));
  }

  if (end < totalPages) {
    if (end < totalPages - 1) pager.appendChild(dots());
    pager.appendChild(createPageBtn(totalPages));
  }

  if (currentPage < totalPages) {
    pager.appendChild(createPageBtn("→", currentPage + 1));
  }
}

function createPageBtn(label, page = label) {
  const btn = document.createElement("button");
  btn.textContent = label;
  btn.className = "page-btn";
  if (page === currentPage) btn.classList.add("active");

  btn.onclick = () => {
    currentPage = page;
    renderDesktopPaged();
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return btn;
}

function dots() {
  const span = document.createElement("span");
  span.textContent = "...";
  span.className = "dots";
  return span;
}




    async function addToCart(productId) {
      const res = await apiFetch(`${CONFIG.API_BASE_URL}/cart`, {
        method: "POST",
        headers: {
          "Authorization": "Bearer " + localStorage.getItem("token"),
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ product_id: productId, quantity: 1 })
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.detail || "Errore durante l'aggiunta", false);
        return;
      }

      showToast("Aggiunto alla lista spesa");
    }


    function showToast(message, success = true) {
      const toast = document.getElementById("toast");
      toast.textContent = message;
      toast.style.background = success ? "#2ecc71" : "#e53935";
      toast.classList.add("show");

      setTimeout(() => {
        toast.classList.remove("show");
      }, 2000);
    }

    function populateStoreFilter() {
      const select = document.getElementById("store-filter");
      select.innerHTML = `<option value="all">Tutti i negozi</option>`;

      supermarkets.forEach(s => {
        const opt = document.createElement("option");
        opt.value = s.id;
        opt.textContent = s.name;
        select.appendChild(opt);
      });
    }
    function setStoreFilter() {
      currentStore = document.getElementById("store-filter").value;
      renderProducts();
    }

    function createProductCard(p) {
      const hasDiscount = p.discounted_price !== null;
      const supermarket = supermarkets.find(s => s.id === p.supermarket_id);
      const supermarketName = supermarket ? supermarket.name : "";

      const card = document.createElement("div");
      card.className = "product-card";

    card.innerHTML = `
        <div class="img-wrapper">

          ${hasDiscount ? `
            <div class="discount-badge">
              -${Math.round((1 - p.discounted_price / p.original_price) * 100)}%
            </div>` : ""
          }

          <img loading="lazy"
               src="${p.image}"
               class="product-img"
               onerror="this.src='/static/images/placeholder.jpg'">

          <div class="fav-icon ${favorites.includes(p.id) ? "active" : ""}" data-id="${p.id}">
            <svg viewBox="0 0 24 24" class="heart-svg">
              <path d="M12 21s-6-4.35-9-8.7C-1.5 7.5 1.5 3 6 3c2.25 0 4.5 1.5 6 3.75C13.5 4.5 15.75 3 18 3c4.5 0 7.5 4.5 3 9.3C18 16.65 12 21 12 21z"/>
            </svg>
          </div>

        </div>

        <div class="product-info">

          <div class="product-name">${p.name}</div>

          <div class="product-meta-row">
            <span class="product-brand">${supermarketName}</span>
            <span class="product-category">${p.category}</span>
          </div>

          <div class="nutri-row">
            ${p.calories ? `<span class="nutri-badge">CAL ${p.calories}</span>` : ""}
            ${p.protein ? `<span class="nutri-badge">PROT ${p.protein}g</span>` : ""}
          </div>

          <div class="price-row">
            ${
              hasDiscount
                ? `
                  <span class="old-price">€ ${p.original_price.toFixed(2).replace(".", ",")}</span>
                  <span class="new-price">€ ${p.discounted_price.toFixed(2).replace(".", ",")}</span>
                `
                : `
                  <span class="regular-price">€ ${p.original_price.toFixed(2).replace(".", ",")}</span>
                `
            }
            <span class="unit-tag">/ ${p.unit || "pz"}</span>
          </div>

          <button class="add-btn" data-id="${p.id}">
            + Aggiungi
          </button>

        </div>
      `;

      // ❤️ CLICK SUL CUORE
      const favBtn = card.querySelector(".fav-icon");
      favBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleFavorite(p.id);
      });

      // 🛒 CLICK SU AGGIUNGI
      card.querySelector(".add-btn").addEventListener("click", (event) => {
        event.stopPropagation();
        addToCart(p.id);
      });

      // 📄 MODAL
      card.addEventListener("click", () => {
        openProductModal(p, supermarket);
      });

      return card;
    }

    function syncStickyOffset() {
      const sticky = document.querySelector(".sticky-header");
      const page = document.querySelector(".products-page");

      if (!sticky || !page) return;

      const navbarHeight = document.querySelector(".top-header")?.offsetHeight || 60;
      page.style.paddingTop = sticky.offsetHeight + navbarHeight + "px";
    }

    window.addEventListener("load", syncStickyOffset);
    window.addEventListener("resize", syncStickyOffset);



let ticking = false;

window.addEventListener("scroll", () => {
  if (window.innerWidth >= 480) return; // DESKTOP: disabilita virtual scroll

  if (!ticking) {
    requestAnimationFrame(() => {
      updateVisibleRange();
      ticking = false;
    });
    ticking = true;
  }
});
    window.addEventListener("resize", renderProducts);