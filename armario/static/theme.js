(() => {
  const system = matchMedia("(prefers-color-scheme: dark)");
  let choice = "system";
  try { choice = localStorage.getItem("wardrobe.theme") || choice; } catch {}
  function apply() {
    document.documentElement.dataset.theme = choice === "system" ? (system.matches ? "dark" : "light") : choice;
  }
  apply();
  system.addEventListener("change", apply);
  document.addEventListener("DOMContentLoaded", () => {
    const select = document.querySelector("#appearance");
    if (!select) return;
    select.value = choice;
    select.addEventListener("change", () => {
      choice = select.value;
      try { localStorage.setItem("wardrobe.theme", choice); } catch {}
      apply();
    });
  });
})();
