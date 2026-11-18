(() => {
  const selected = new Set();
  const panel = document.querySelector("[data-trip-picker]");
  let latest = 0;
  const count = () => { panel.querySelector("[data-count]").textContent = "(" + selected.size + ")"; };
  async function navigate(url) {
    const sequence = ++latest;
    try {
      const response = await fetch(url);
      if (!response.ok) throw Error();
      const doc = new DOMParser().parseFromString(await response.text(), "text/html");
      if (sequence !== latest) return;
      const next = doc.querySelector("[data-trip-picker]");
      if (!next) throw Error();
      panel.replaceChildren(...next.children);
      panel.querySelectorAll("input[type=checkbox]").forEach(input => { input.checked = selected.has(input.value); });
      count();
    } catch {
      if (sequence === latest) alert("No se pudo cargar la búsqueda. Tu selección se conserva.");
    }
  }
  panel.addEventListener("change", ({target}) => {
    if (target.type !== "checkbox") return;
    if (target.checked) selected.add(target.value);
    else selected.delete(target.value);
    count();
  });
  panel.addEventListener("click", event => {
    const link = event.target.closest("nav a");
    if (link) { event.preventDefault(); navigate(link.href); }
  });
  panel.addEventListener("submit", event => {
    if (event.target.matches("[data-search]")) {
      event.preventDefault();
      navigate(location.pathname + "?" + new URLSearchParams(new FormData(event.target)));
    }
  });
  function fill(event) {
    event.formData.delete("garment_ids");
    for (const id of selected) event.formData.append("garment_ids", id);
  }
  panel.addEventListener("formdata", event => { if (event.target.matches("[data-add]")) fill(event); }, true);
})();
