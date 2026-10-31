"use strict";

(() => {
  const importInput = document.querySelector('#photos[name="photos"][multiple]');
  const importPreview = document.querySelector("[data-import-preview]");
  if (importInput && importPreview) {
    importInput.addEventListener("change", () => {
      importPreview.querySelectorAll("img[data-object-url]").forEach((img) => URL.revokeObjectURL(img.src));
      importPreview.replaceChildren();
      Array.from(importInput.files).forEach((file, index) => {
        const label = document.createElement("label");
        label.textContent = `Prenda ${index + 1} · ${file.name}`;
        if (file.type.startsWith("image/")) {
          const image = document.createElement("img");
          image.src = URL.createObjectURL(file);
          image.dataset.objectUrl = "";
          image.alt = `Vista previa ${index + 1}`;
          image.width = 100;
          image.height = 100;
          label.append(image);
        }
        const input = document.createElement("input");
        input.name = "photo_names";
        input.required = true;
        input.maxLength = 120;
        input.value = file.name.replace(/\.[^.]*$/, "").trim().slice(0, 120) || "Prenda sin nombre";
        label.append(input);
        importPreview.append(label);
      });
    });
  }

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
    const selectedCount = picker.querySelector("[data-picker-selected]");
    const updateCount = () => {
      selectedCount.textContent = `${cards.filter((card) => card.querySelector('input:checked')).length} seleccionadas`;
    };
    picker.addEventListener("change", updateCount);
    updateCount();
    const pager = picker.querySelector("[data-picker-pagination]");
    const previous = picker.querySelector("[data-picker-prev]");
    const next = picker.querySelector("[data-picker-next]");
    const pageLabel = picker.querySelector("[data-picker-page]");
    let page = 0;
    const pageSize = 24;
    const render = () => {
      const query = normalize(search.value.trim());
      const matches = cards.filter((card) => normalize(card.dataset.search).includes(query));
      const pages = Math.max(1, Math.ceil(matches.length / pageSize));
      page = Math.min(page, pages - 1);
      const shown = new Set(matches.slice(page * pageSize, (page + 1) * pageSize));
      cards.forEach((card) => { card.hidden = !shown.has(card); });
      picker.querySelector("[data-picker-status]").textContent = `${matches.length} disponibles`;
      picker.querySelector("[data-picker-empty]").hidden = matches.length !== 0;
      pageLabel.textContent = `Página ${page + 1} de ${pages}`;
      previous.disabled = page === 0;
      next.disabled = page === pages - 1;
      pager.hidden = pages <= 1;
    };
    search.addEventListener("input", () => { page = 0; render(); });
    previous.addEventListener("click", () => { page -= 1; render(); });
    next.addEventListener("click", () => { page += 1; render(); });
    render();
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
