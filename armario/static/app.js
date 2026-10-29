"use strict";

document.querySelectorAll('input[form="bulk"]').forEach((checkbox) => {
  checkbox.addEventListener("change", () => {
    const count = document.querySelectorAll(
      'input[form="bulk"]:checked',
    ).length;
    document.querySelector("[data-selection-count]").textContent = count;
  });
});

document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

document.querySelectorAll("[data-go-back]").forEach((button) => {
  button.addEventListener("click", () => window.history.back());
});

const photoInput = document.querySelector("[data-photo-input]");
if (photoInput) {
  let previousUrls = [];
  photoInput.addEventListener("change", () => {
    previousUrls.forEach((url) => URL.revokeObjectURL(url));
    previousUrls = [];
    const container = document.querySelector("[data-photo-previews]");
    container.replaceChildren();
    Array.from(photoInput.files)
      .slice(0, 6)
      .forEach((file) => {
        if (!["image/jpeg", "image/png", "image/webp"].includes(file.type))
          return;
        const img = document.createElement("img");
        img.alt = "Vista previa de " + file.name;
        img.src = URL.createObjectURL(file);
        previousUrls.push(img.src);
        container.append(img);
      });
  });
}
