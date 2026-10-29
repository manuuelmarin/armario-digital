"use strict";

(() => {
  const bulkForm = document.querySelector("#bulk");
  const selection = Array.from(document.querySelectorAll('input[form="bulk"]'));
  const updateSelection = () => {
    if (!bulkForm) return;
    const count = selection.filter((checkbox) => checkbox.checked).length;
    bulkForm.hidden = count === 0;
    bulkForm.querySelector("[data-selection-count]").textContent = count;
  };
  selection.forEach((checkbox) => checkbox.addEventListener("change", updateSelection));
  document.querySelector("[data-clear-selection]")?.addEventListener("click", () => {
    selection.forEach((checkbox) => {
      checkbox.checked = false;
    });
    updateSelection();
  });
  window.addEventListener("pageshow", updateSelection);
  updateSelection();

  const filters = document.querySelector(".filters");
  const filterButton = document.querySelector("[data-filter-toggle]");
  if (filters && filterButton) {
    const compact = window.matchMedia("(max-width: 620px)");
    const configureFilters = () => {
      filters.dataset.filterCollapsed = String(compact.matches);
      filterButton.setAttribute("aria-expanded", String(!compact.matches));
      filterButton.querySelector("[data-filter-label]").textContent = compact.matches ? "Filtros" : "Filtrar";
    };
    configureFilters();
    compact.addEventListener("change", configureFilters);
    filterButton.addEventListener("click", (event) => {
      if (compact.matches && filters.dataset.filterCollapsed === "true") {
        event.preventDefault();
        filters.dataset.filterCollapsed = "false";
        filterButton.setAttribute("aria-expanded", "true");
        filterButton.querySelector("[data-filter-label]").textContent = "Aplicar";
      }
    });
  }

  document.querySelector('select[name="sort"]')?.addEventListener("change", (event) => {
    event.target.form.requestSubmit();
  });

  const normalize = (value) => value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLocaleLowerCase();
  document.querySelectorAll("[data-picker]").forEach((picker) => {
    const search = picker.querySelector("[data-picker-search]");
    if (!search) return;
    const cards = Array.from(picker.querySelectorAll("[data-picker-card]"));
    search.addEventListener("input", () => {
      const query = normalize(search.value.trim());
      let visible = 0;
      cards.forEach((card) => {
        card.hidden = !normalize(card.dataset.search).includes(query);
        if (!card.hidden) visible += 1;
      });
      picker.querySelector("[data-picker-status]").textContent = `${visible} disponibles`;
      picker.querySelector("[data-picker-empty]").hidden = visible !== 0;
    });
    search.addEventListener("keydown", (event) => {
      if (event.key === "Enter") event.preventDefault();
    });
  });

  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!window.confirm(form.dataset.confirm)) event.preventDefault();
    });
  });
  document.querySelectorAll("[data-go-back]").forEach((button) => {
    button.addEventListener("click", () => {
      if (window.history.length > 1) window.history.back();
      else window.location.assign("/");
    });
  });

  const mainPhoto = document.querySelector("[data-main-photo]");
  document.querySelectorAll("[data-photo-target]").forEach((button) => {
    button.addEventListener("click", () => {
      if (!mainPhoto) return;
      const target = new URL(button.dataset.photoTarget, window.location.origin);
      if (target.origin !== window.location.origin || !target.pathname.startsWith("/imagenes/")) return;
      mainPhoto.src = target.href;
      document.querySelector("[data-photo-expand]").href = target.href;
      document.querySelectorAll("[data-photo-target]").forEach((choice) => {
        choice.classList.toggle("active", choice === button);
        choice.setAttribute("aria-pressed", String(choice === button));
      });
    });
  });

  const photoInput = document.querySelector("[data-photo-input]");
  if (photoInput) {
    let previousUrls = [];
    const releaseUrls = () => {
      previousUrls.forEach((url) => URL.revokeObjectURL(url));
      previousUrls = [];
    };
    photoInput.addEventListener("change", () => {
      releaseUrls();
      const container = document.querySelector("[data-photo-previews]");
      container.replaceChildren();
      photoInput.setCustomValidity(photoInput.files.length > 6 ? "Selecciona como máximo seis fotografías." : "");
      Array.from(photoInput.files).slice(0, 6).forEach((file) => {
        if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) return;
        const img = document.createElement("img");
        img.alt = "Vista previa de " + file.name;
        img.src = URL.createObjectURL(file);
        previousUrls.push(img.src);
        container.append(img);
      });
    });
    window.addEventListener("pagehide", releaseUrls);
  }
})();
