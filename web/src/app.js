import "./style.css";
import { call } from "./engine";
import { create, connect } from "./folder";
import { remembered, checked } from "./files";
import { backup, daily, inspectZip, prune } from "./backup";
import {
  state,
  q,
  esc,
  field,
  form,
  action,
  link,
  val,
  statement,
  save,
  remove,
  clearActions,
  releasePhotos,
  hydrate,
  activatePickers,
  notice,
  status,
} from "./ui";
import { preparePhoto } from "./media";
import { catalog, detail, garmentEditor, summary } from "./inventory";
import { groups, trips } from "./groups";
import { boards, weather } from "./extras";
import { startUpdates } from "./update";
document.documentElement.dataset.version =
  import.meta.env.VITE_RELEASE || "1.0.0";
const main = document.querySelector("main"),
  nav = document.querySelector("nav");
const sections = {
  catalogo: "Catálogo",
  outfits: "Outfits",
  maletas: "Maletas",
  colecciones: "Colecciones",
  inspiracion: "Inspiración",
  resumen: "Resumen",
  tiempo: "Tiempo",
  ajustes: "Ajustes",
};
let previous,
  pendingBackup,
  renderVersion = 0;
const pick = (mode) =>
  window.showDirectoryPicker({ mode, id: "armario-digital" });
function supported() {
  return (
    window.isSecureContext &&
    window.showDirectoryPicker &&
    navigator.locks &&
    window.Worker &&
    window.createImageBitmap
  );
}
async function activate(s, remember = true) {
  const old = state.session;
  state.session = s;
  await old?.pendingDaily?.catch(() => {});
  old?.release?.();
  if (remember && !s.demo) {
    previous = s.root;
    await remembered(s.root).catch(() =>
      notice("Carpeta abierta. El navegador no ha recordado el acceso."),
    );
  }
  state.dirty = false;
  pendingBackup = null;
  status(s.release ? "Guardado" : "Solo lectura");
  if (s.damaged) notice("Se ha recuperado la última revisión válida.");
  if (!s.release)
    notice(
      "Solo lectura. Para editar, cierra la pestaña que tiene abierto el armario y vuelve a conectar con permiso de escritura.",
    );
  await render();
  if (s.release)
    void daily(s).catch((e) => {
      if (state.session === s)
        notice("No se pudo crear la copia diaria. " + e.message);
    });
}
async function openFolder(root, writable = true) {
  if (
    state.session &&
    (await state.session.root.isSameEntry(root)) &&
    state.session.release
  ) {
    notice("Ya tienes esta carpeta abierta.");
    return;
  }
  await activate(await connect(root, writable));
}
async function chooseNew() {
  const root = await pick("readwrite");
  if (confirm("¿Crear un armario en «" + root.name + "»?"))
    await activate(await create(root, () => call("new")));
}
async function makeDemo() {
  const root = await (
    await navigator.storage.getDirectory()
  ).getDirectoryHandle("armario-demo-" + crypto.randomUUID(), { create: true });
  const s = await create(root, async (dest) => {
    const sql = [
      [
        "INSERT INTO locations(name) VALUES ('Madrid'),('Albacete'),('La Manga')",
      ],
    ];
    for (const [id, name, category, location, color, price, file] of [
      [1, "Camisa blanca", 2, 1, "Blanco", 3500, "camisa"],
      [2, "Chaqueta de viaje", 6, 2, "Azul", null, "chaqueta"],
    ]) {
      const response = await fetch("./demo/" + file + ".png");
      if (!response.ok)
        throw Error("No se pudo abrir la ilustración de la demo.");
      const photo = await preparePhoto(await response.blob());
      sql.push(
        statement("garments", {
          id,
          name,
          category_id: category,
          location_id: location,
          color,
          price_cents: price,
        }),
        statement("garment_images", {
          ...photo.meta,
          garment_id: id,
          is_primary: 1,
          sort_order: 1,
        }),
        ...photo.integrity,
      );
      for (const [name, data] of photo.files)
        await checked(dest, "images/" + name, data);
    }
    return call("new", undefined, { statements: sql });
  });
  s.demo = true;
  await activate(s, false);
}
function uploadBackup() {
  return form(
    '<label>Selecciona el ZIP de tu armario<input name="archive" type="file" required accept=".zip,application/zip"></label>',
    "Verificar copia",
    async (f) => {
      const blob = f.get("archive");
      const { info } = await inspectZip(blob);
      pendingBackup = { blob, info };
      notice("Copia verificada.");
      state.dirty = false;
      await render();
    },
  );
}
function restoreBox() {
  if (!pendingBackup) return uploadBackup();
  const { blob, info } = pendingBackup;
  return (
    '<div class="panel"><strong>Copia verificada</strong><p>' +
    info.garments +
    " prendas · " +
    info.outfits +
    " outfits · " +
    info.files.length +
    " archivos de imagen · esquema " +
    info.version +
    "</p>" +
    action("Restaurar en una carpeta vacía", async () => {
      const root = await pick("readwrite");
      if (!confirm("¿Traer la copia a «" + root.name + "»?")) return;
      await activate(
        await create(root, async (dest) => (await inspectZip(blob, dest)).data),
      );
      notice(
        "Armario restaurado. " +
          info.garments +
          " prendas y " +
          info.outfits +
          " outfits.",
      );
      location.hash = "#/catalogo";
    }) +
    action("Elegir otra copia", async () => {
      pendingBackup = null;
      await render();
    }) +
    "</div>"
  );
}
function connectionControls() {
  const actions = [];
  if (supported()) {
    if (previous)
      actions.push(
        action("Reconectar", async () => {
          const permission = await previous.requestPermission({
            mode: "readwrite",
          });
          if (
            permission !== "granted" &&
            (await previous.queryPermission({ mode: "read" })) !== "granted"
          )
            throw Error("Permiso denegado. Selecciona la carpeta de nuevo.");
          await openFolder(previous, permission === "granted");
        }),
      );
    actions.push(
      action("Crear armario", chooseNew, "primary"),
      action("Abrir mi carpeta", async () =>
        openFolder(await pick("readwrite")),
      ),
      link("Traer una copia", "#/traer"),
    );
  }
  if (navigator.storage?.getDirectory && window.createImageBitmap)
    actions.push(action("Probar la demo", makeDemo));
  return (
    '<div class="actions">' +
    actions.join("") +
    "</div>" +
    (!supported()
      ? "<p>Para guardar en una carpeta local abre esta web en Chrome o Edge de escritorio sobre HTTPS.</p>"
      : "")
  );
}
function appearance() {
  const choice = localStorage.getItem("armario-digital:tema") || "sistema";
  document.documentElement.dataset.theme =
    choice === "sistema"
      ? matchMedia("(prefers-color-scheme:dark)").matches
        ? "oscuro"
        : "claro"
      : choice;
}
function download(file) {
  const url = URL.createObjectURL(file),
    a = document.createElement("a");
  a.href = url;
  a.download = file.name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}
async function settings() {
  const s = state.session,
    [locations, categories] = await Promise.all(
      ["locations", "categories"].map((t) =>
        q("SELECT * FROM " + t + " ORDER BY name"),
      ),
    );
  const copies = [];
  try {
    const dir = await s.root.getDirectoryHandle("backups");
    for await (const entry of dir.values())
      if (entry.kind === "file" && entry.name.endsWith(".zip"))
        copies.push(entry);
  } catch (e) {
    if (e.name !== "NotFoundError") throw e;
  }
  copies.sort((a, b) => b.name.localeCompare(a.name));
  const savedCopies =
    "<details><summary>Copias de esta carpeta (" +
    copies.length +
    ")</summary>" +
    copies
      .map(
        (handle) =>
          '<div class="row"><span>' +
          esc(handle.name) +
          "</span>" +
          action("Verificar", async () => {
            const { info } = await inspectZip(await handle.getFile());
            notice(
              "Copia válida. " +
                info.garments +
                " prendas y " +
                info.outfits +
                " outfits.",
            );
          }) +
          action("Descargar", async () => download(await handle.getFile())) +
          "</div>",
      )
      .join("") +
    "</details>";
  const manage = (table, label, rows) =>
    "<h2>" +
    label +
    "</h2>" +
    rows
      .map(
        (r) =>
          "<details><summary>" +
          esc(r.name) +
          "</summary>" +
          form(
            field("Nombre", "name", r.name, 'required maxlength="80"'),
            "Renombrar",
            (f) => save([statement(table, { name: val(f, "name") }, r.id)]),
          ) +
          remove("Eliminar " + r.name, table, r.id, "#/ajustes") +
          "</details>",
      )
      .join("") +
    form(
      field(
        "Nombre de " + (table === "locations" ? "ubicación" : "categoría"),
        "name",
        "",
        'required maxlength="80"',
      ),
      "Crear " + (table === "locations" ? "ubicación" : "categoría"),
      (f) => save([statement(table, { name: val(f, "name") })]),
    );
  return (
    "<h1>Ajustes</h1><h2>Carpeta conectada</h2><p>" +
    esc(s.root.name) +
    " · Revisión " +
    s.head.revision +
    " · " +
    (s.release ? "Lectura y escritura" : "Solo lectura") +
    "</p>" +
    connectionControls() +
    action("Desconectar", async () => {
      await remembered(null);
      previous = null;
      await s.pendingDaily?.catch(() => {});
      s.release?.();
      state.session = null;
      state.dirty = false;
      status("Sin conectar");
      location.hash = "#/catalogo";
      await render();
    }) +
    '<h2>Apariencia</h2><div class="actions">' +
    ["sistema", "claro", "oscuro"]
      .map((t) =>
        action(t[0].toUpperCase() + t.slice(1), () => {
          localStorage.setItem("armario-digital:tema", t);
          appearance();
        }),
      )
      .join("") +
    "</div>" +
    manage("locations", "Ubicaciones", locations) +
    manage("categories", "Categorías", categories) +
    "<h2>Copias</h2>" +
    action("Crear y descargar copia", async () => {
      if (!s.release)
        throw Error("Se necesita acceso de escritura para crear la copia.");
      const f = await backup(s);
      download(f);
      notice("Copia verificada y guardada en backups.");
    }) +
    savedCopies +
    link("Verificar o restaurar una copia", "#/traer") +
    form(
      field(
        "Copias diarias que conservar",
        "keep",
        7,
        'type="number" min="1" max="365" required',
      ),
      "Limpiar copias diarias antiguas",
      async (f) => {
        if (
          confirm(
            "¿Limpiar únicamente las copias diarias anteriores a las conservadas?",
          )
        )
          notice("Copias eliminadas: " + (await prune(s, +val(f, "keep"))));
      },
    )
  );
}
async function render() {
  const version = ++renderVersion;
  clearActions();
  const [path, query = ""] = (location.hash.slice(1) || "/catalogo").split("?");
  const [route, id, mode] = path.split("/").filter(Boolean),
    params = new URLSearchParams(query);
  let html;
  nav.innerHTML = state.session
    ? Object.entries(sections)
        .map(
          ([key, title]) =>
            "<a " +
            (key === route ? 'aria-current="page"' : "") +
            ' href="#/' +
            key +
            '">' +
            title +
            "</a>",
        )
        .join("")
    : "";
  try {
    if (route === "traer")
      html =
        "<h1>Traer una copia</h1><p>En tu aplicación anterior abre Ajustes y elige «Crear y descargar copia». Aquí podrás comprobar su contenido y elegir una carpeta vacía.</p>" +
        restoreBox() +
        link("Volver", "#/catalogo");
    else if (!state.session)
      html =
        '<div class="entry"><div class="welcome"><h1>Mi armario digital</h1><p>Guarda tus prendas y fotografías en una carpeta de tu ordenador. Puedes volver a abrirla desde este mismo enlace.</p>' +
        connectionControls() +
        '</div><div class="sample-rail" aria-hidden="true"><img src="./demo/camisa.png" alt=""><img src="./demo/chaqueta.png" alt=""></div></div>';
    else if (route === "ajustes") html = await settings();
    else if (route === "prendas")
      html =
        id === "nueva"
          ? await garmentEditor()
          : mode === "editar"
            ? await garmentEditor(+id)
            : await detail(+id);
    else if (route === "lotes") html = await garmentEditor(null, true);
    else if (["outfits", "colecciones", "etiquetas"].includes(route))
      html = await groups(
        route,
        id && (/^\d+$/.test(id) ? Number(id) : id),
        params,
      );
    else if (route === "maletas")
      html = await trips(id && (/^\d+$/.test(id) ? Number(id) : id));
    else if (route === "inspiracion") html = await boards(Number(id) || null);
    else if (route === "tiempo") html = await weather();
    else if (route === "resumen") html = await summary();
    else html = await catalog(params);
  } catch (e) {
    html =
      "<h1>No se pudo abrir esta pantalla</h1><p>" +
      esc(e.message) +
      "</p>" +
      link("Volver", "#/catalogo");
  }
  if (version !== renderVersion) return;
  releasePhotos();
  main.innerHTML = html;
  main.focus({ preventScroll: true });
  document.title =
    (main.querySelector("h1")?.textContent || "Catálogo") +
    " · Armario Digital";
  activatePickers();
  await hydrate();
}
state.refresh = render;
window.addEventListener("hashchange", (event) => {
  if (
    state.dirty &&
    !state.busy &&
    !confirm("¿Descartar los cambios pendientes y salir de este formulario?")
  ) {
    history.replaceState(null, "", event.oldURL);
    return;
  }
  state.dirty = false;
  nav.classList.remove("open");
  document.querySelector("#mobile").setAttribute("aria-expanded", "false");
  void render();
});
window.addEventListener("beforeunload", (e) => {
  if (state.busy || state.dirty) {
    e.preventDefault();
    e.returnValue = "";
  }
});
document.querySelector("#mobile").onclick = (e) =>
  e.target.setAttribute("aria-expanded", nav.classList.toggle("open"));
document.querySelector(".skip").onclick = (e) => {
  e.preventDefault();
  main.focus();
};
appearance();
matchMedia("(prefers-color-scheme:dark)").addEventListener(
  "change",
  appearance,
);
async function boot() {
  try {
    if (location.hash === "#/demo") {
      history.replaceState(null, "", "#/catalogo");
      await makeDemo();
      return;
    }
    previous = await remembered();
    if (
      previous &&
      (await previous.queryPermission({ mode: "readwrite" })) === "granted"
    ) {
      await openFolder(previous);
      return;
    }
  } catch (e) {
    notice("Vuelve a elegir tu carpeta. " + e.message);
  }
  status("Sin conectar");
  await render();
}
void boot();
startUpdates();
