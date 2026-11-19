import { call } from "./engine";
import { commit } from "./folder";
import { read } from "./files";
export const state = {
  session: null,
  busy: false,
  dirty: false,
  refresh: null,
  returnTo: "#/catalogo",
};
export const q = (sql, ...params) =>
  call("query", state.session.head.data, { sql, params });
export const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export const money = (v) =>
  v == null
    ? "Sin precio"
    : new Intl.NumberFormat("es-ES", {
        style: "currency",
        currency: "EUR",
      }).format(v / 100);
export function notice(msg) {
  document.querySelector("#notice").textContent = msg;
}
export function status(msg) {
  document.querySelector("#connection").textContent = [
    state.session?.demo ? "Demo" : state.session?.root.name,
    msg,
  ]
    .filter(Boolean)
    .join(" · ");
}
export function field(label, name, value = "", attrs = "") {
  return (
    "<label>" +
    esc(label) +
    '<input name="' +
    name +
    '" value="' +
    esc(value) +
    '" ' +
    attrs +
    "></label>"
  );
}
export function options(items, current, blank) {
  return (
    (blank === undefined
      ? ""
      : '<option value="">' + esc(blank) + "</option>") +
    items
      .map(
        (i) =>
          '<option value="' +
          esc(i.id) +
          '" ' +
          (String(current) === String(i.id) ? "selected" : "") +
          ">" +
          esc(i.name) +
          "</option>",
      )
      .join("")
  );
}
export function select(label, name, items, current, blank) {
  return (
    "<label>" +
    esc(label) +
    '<select name="' +
    name +
    '" ' +
    (blank === undefined ? "required" : "") +
    ">" +
    options(items, current, blank) +
    "</select></label>"
  );
}
export const link = (label, path) =>
  '<a class="button" href="' + esc(path) + '">' + esc(label) + "</a>";
export function img(name, label = "Foto de la prenda") {
  return name
    ? '<img loading="lazy" data-photo="' +
        esc(name) +
        '" alt="' +
        esc(label) +
        '">'
    : '<span class="muted">Sin foto</span>';
}
const callbacks = new Map();
export function action(label, fn, cls = "") {
  return (
    '<button type="button" class="' +
    cls +
    '" data-action="' +
    bind(fn) +
    '">' +
    esc(label) +
    "</button>"
  );
}
function bind(fn) {
  const key = crypto.randomUUID();
  callbacks.set(key, fn);
  return key;
}
export function form(body, label, fn, cls = "") {
  return (
    '<form class="' +
    cls +
    '" data-submit="' +
    bind((el) => fn(new FormData(el), el)) +
    '">' +
    body +
    '<div class="actions"><button class="primary">' +
    esc(label) +
    "</button></div></form>"
  );
}
export function clearActions() {
  callbacks.clear();
}
export function val(f, k) {
  return String(f.get(k) ?? "").trim();
}
export const ids = (f, k) => [...new Set(f.getAll(k).map(Number))];
export function statement(table, values, id) {
  const columns = Object.keys(values),
    params = Object.values(values);
  return id
    ? [
        "UPDATE " +
          table +
          " SET " +
          columns.map((k) => k + "=?").join(",") +
          " WHERE id=?",
        [...params, id],
      ]
    : [
        "INSERT INTO " +
          table +
          " (" +
          columns.join(",") +
          ") VALUES (" +
          columns.map(() => "?").join(",") +
          ")",
        params,
      ];
}
export async function nextId(table) {
  return (await q("SELECT coalesce(max(id),0)+1 id FROM " + table))[0].id;
}
let activeControl;
export async function save(statements, files = [], destination) {
  const s = state.session;
  if (!s?.release)
    throw Error(
      "Solo lectura. Cierra la otra pestaña y vuelve a abrir la carpeta con permiso de escritura.",
    );
  const el = activeControl;
  const intent = el?._intent ?? {
    uuid: s.uuid,
    revision: s.head.revision,
    operation: crypto.randomUUID(),
  };
  if (el) el._intent = intent;
  status("Guardando");
  await commit(s, intent, statements, files);
  if (el) delete el._intent;
  state.dirty = false;
  status("Guardado");
  notice("Cambios guardados.");
  if (destination && location.hash !== destination) location.hash = destination;
  else await state.refresh();
}
export function remove(label, table, id, dest) {
  return action(label, async () => {
    if (confirm("¿" + label + "? Esta acción es definitiva."))
      await save([["DELETE FROM " + table + " WHERE id=?", [id]]], [], dest);
  });
}
export async function dispatch(el, key) {
  if (state.busy || !callbacks.has(key)) return;
  state.busy = true;
  activeControl = el;
  try {
    await callbacks.get(key)(el);
  } catch (e) {
    if (e.name !== "AbortError") {
      notice(
        e.message?.includes("FOREIGN KEY")
          ? "Hay elementos vinculados. Quita la relación antes de eliminar."
          : e.message,
      );
      if (state.session) status("No se pudo completar la operación");
      document.querySelector("#notice").setAttribute("tabindex", "-1");
      document.querySelector("#notice").focus();
    }
  } finally {
    activeControl = null;
    state.busy = false;
  }
}
document.addEventListener("submit", (e) => {
  if (e.target.dataset.submit) {
    e.preventDefault();
    void dispatch(e.target, e.target.dataset.submit);
  }
});
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-action]");
  if (el) void dispatch(el, el.dataset.action);
});
document.addEventListener("input", (e) => {
  if (e.target.closest("form")) {
    state.dirty = true;
    delete e.target.closest("form")._intent;
  }
});
let urls = [];
export function releasePhotos() {
  urls.forEach(URL.revokeObjectURL);
  urls = [];
}
export async function hydrate() {
  const root = state.session?.root;
  await Promise.all(
    [...document.querySelectorAll("img[data-photo]")].map(async (el) => {
      try {
        const f = await read(root, "images/" + el.dataset.photo);
        if (!el.isConnected) return;
        const url = URL.createObjectURL(f);
        urls.push(url);
        el.src = url;
        el.onerror = () => el.replaceWith("Foto no disponible");
      } catch {
        if (el.isConnected) el.replaceWith("Foto no disponible");
      }
    }),
  );
}
export const seasons = ["Primavera", "Verano", "Otoño", "Invierno"];
export const checks = (rows, chosen, name) =>
  rows
    .map(
      (i) =>
        '<label><input type="checkbox" name="' +
        name +
        '" value="' +
        esc(i.id) +
        '" ' +
        (chosen.includes(i.id) ? "checked" : "") +
        ">" +
        esc(i.name) +
        "</label>",
    )
    .join("");
export function picker(rows, chosen = []) {
  return (
    '<fieldset data-picker><legend>Seleccionar prendas</legend><label>Buscar prenda<input type="search" data-filter></label><div data-choices>' +
    checks(rows, chosen, "garment") +
    '</div><div class="actions"><button type="button" data-step="-1">Anterior</button><span data-page></span><button type="button" data-step="1">Siguiente</button></div></fieldset>'
  );
}
export function activatePickers() {
  for (const box of document.querySelectorAll("[data-picker]")) {
    let page = 0;
    const input = box.querySelector("[data-filter]");
    function draw() {
      const all = [...box.querySelectorAll("[data-choices] label")];
      const matches = all.filter((el) =>
        el.textContent
          .toLocaleLowerCase()
          .includes(input.value.toLocaleLowerCase()),
      );
      all.forEach((el) => (el.hidden = true));
      matches
        .slice(page * 24, page * 24 + 24)
        .forEach((el) => (el.hidden = false));
      box.querySelector("[data-page]").textContent =
        page + 1 + " / " + Math.max(1, Math.ceil(matches.length / 24));
      for (const btn of box.querySelectorAll("[data-step]"))
        btn.disabled =
          btn.dataset.step === "-1"
            ? page === 0
            : (page + 1) * 24 >= matches.length;
    }
    input.oninput = () => {
      page = 0;
      draw();
    };
    box.querySelectorAll("[data-step]").forEach(
      (btn) =>
        (btn.onclick = () => {
          page += Number(btn.dataset.step);
          draw();
        }),
    );
    draw();
  }
}
