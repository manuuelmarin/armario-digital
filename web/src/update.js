import { state, notice } from "./ui";
export async function startUpdates() {
  if (!("serviceWorker" in navigator) || !import.meta.env.PROD) return;
  const box = document.querySelector("#update");
  try {
    const reg = await navigator.serviceWorker.register("./sw.js", {
      scope: "./",
      updateViaCache: "none",
    });
    function show() {
      if (!reg.waiting || !navigator.serviceWorker.controller) return;
      box.replaceChildren();
      const btn = document.createElement("button");
      btn.textContent = "Nueva versión disponible · Actualizar";
      box.append(btn);
      btn.onclick = async () => {
        if (state.busy || state.dirty) {
          notice(
            "Guarda el formulario o descártalo al salir antes de actualizar.",
          );
          return;
        }
        reg.waiting?.postMessage({ type: "check-update" });
      };
    }
    let timer;
    function unfreeze() {
      clearTimeout(timer);
      document.body.inert = false;
    }
    navigator.serviceWorker.addEventListener("message", (e) => {
      if (e.data?.type === "can-update") {
        const ok = !state.busy && !state.dirty && !state.session?.pendingDaily;
        if (ok) {
          document.body.inert = true;
          clearTimeout(timer);
          timer = setTimeout(unfreeze, 8000);
        }
        e.ports[0]?.postMessage({ ok });
      }
      if (e.data?.type === "cancel-update") unfreeze();
      if (e.data?.type === "busy")
        notice(
          "Hay otra pestaña con cambios pendientes. Guarda o cierra esa pestaña antes de actualizar.",
        );
    });
    let controlled = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (controlled && !state.dirty && !state.busy) location.reload();
      controlled = true;
    });
    reg.onupdatefound = () => {
      const sw = reg.installing;
      sw.onstatechange = () => {
        if (sw.state === "installed") show();
      };
    };
    show();
  } catch (e) {
    notice("No se pudo preparar el uso sin conexión. " + e.message);
  }
}
