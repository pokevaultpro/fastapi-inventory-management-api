function renderQuickActions() {
  const currentPage = document.body.dataset.page;

  const actions = [
    {
      id: "home",
      label: "Home",
      color: "green",
      icon: "M3 9.75L12 3l9 6.75V21a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1V9.75z"
    },
    {
      id: "list",
      label: "Lista",
      color: "green",
      icon: "M5 6h14M5 12h14M5 18h14"
    },
    {
      id: "products",
      label: "Prodotti",
      color: "blue",
      icon: "M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
    },
    {
      id: "history",
      label: "Storico",
      color: "teal",
      icon: "M12 8v4l3 3M21 12a9 9 0 11-3.2-6.9M21 3v6h-6"
    },
    {
      id: "recipes",
      label: "Ricette",
      color: "orange",
      icon: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
    },
    {
      id: "supermarkets",
      label: "Negozi",
      color: "purple",
      icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"
    },
    {
      id: "profile",
      label: "Profilo",
      color: "gray",
      icon: "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
    }
  ];

  const visibleActions = actions.filter(a => a.id !== currentPage);
  const container = document.getElementById("bottom-bar");
  if (!container) return;

  container.innerHTML = visibleActions.map(a => `
    <button class="action-btn-bottom" data-id="${a.id}" onclick="navigate('${a.id}')">
      <div class="action-icon color-${a.color}">
        <svg class="icon-svg" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${a.icon}" />
        </svg>
      </div>
      <span class="action-label-bottom">${a.label}</span>
    </button>
  `).join("");
}

renderQuickActions();
