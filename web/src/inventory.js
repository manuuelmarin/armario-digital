import { read, optional } from "./files";
import {
  q,
  esc,
  field,
  select,
  form,
  action,
  link,
  img,
  val,
  ids,
  nextId,
  statement,
  save,
  remove,
  money,
  seasons,
  checks,
  state,
} from "./ui";
import { preparePhoto } from "./media";
export const coverOrder = "is_primary DESC,coalesce(sort_order,id),id";
export const garmentSQL =
  "SELECT g.*,c.name category,l.name location,(SELECT thumbnail FROM garment_images WHERE garment_id=g.id ORDER BY " +
  coverOrder +
  " LIMIT 1) thumbnail FROM garments g JOIN categories c ON g.category_id=c.id JOIN locations l ON g.location_id=l.id";
const choices = async (table) =>
  q("SELECT id,name FROM " + table + " ORDER BY name");
const seasonRows = seasons.map((id) => ({ id, name: id }));
export function move(gids, destination, reason) {
  return gids.flatMap((gid) => [
    [
      "INSERT INTO garment_movements(garment_id,from_id,to_id,reason) SELECT id,location_id,?,? FROM garments WHERE id=? AND location_id<>? AND archived=0",
      [destination, reason, gid, destination],
    ],
    [
      "UPDATE garments SET location_id=? WHERE id=? AND archived=0",
      [destination, gid],
    ],
  ]);
}
export async function catalog(p) {
  const [locations, categories, tags, collections] = await Promise.all(
    ["locations", "categories", "tags", "collections"].map(choices),
  );
  const where = ["g.archived=?"],
    args = [Number(p.get("archived") === "1")];
  for (const [key, col] of [
    ["location", "g.location_id"],
    ["category", "g.category_id"],
    ["favorite", "g.favorite"],
  ])
    if (p.get(key)) {
      where.push(col + "=?");
      args.push(Number(p.get(key)));
    }
  for (const [key, t, c] of [
    ["season", "garment_seasons", "season"],
    ["tag", "garment_tags", "tag_id"],
    ["collection", "collection_items", "collection_id"],
  ])
    if (p.get(key)) {
      where.push(
        "g.id IN (SELECT garment_id FROM " + t + " WHERE " + c + "=?)",
      );
      args.push(p.get(key));
    }
  if (p.get("q")) {
    where.push(
      "instr(fold(g.name||' '||g.brand||' '||g.color||' '||g.notes),fold(?))>0",
    );
    args.push(p.get("q"));
  }
  const filter = " WHERE " + where.join(" AND "),
    page = Math.max(1, Math.trunc(Number(p.get("page"))) || 1);
  const sorts = new Map([
    ["newest", "g.id DESC"],
    ["oldest", "g.id"],
    ["name", "fold(g.name),g.id"],
    ["name_desc", "fold(g.name) DESC,g.id DESC"],
  ]);
  const order = sorts.get(p.get("sort")) || sorts.get("newest");
  const items = await q(
    garmentSQL + filter + " ORDER BY " + order + " LIMIT 25 OFFSET ?",
    ...args,
    (page - 1) * 24,
  );
  state.returnTo = location.hash || "#/catalogo";
  const switchPage = (n) => {
    const x = new URLSearchParams(p);
    x.set("page", n);
    return "#/catalogo?" + x;
  };
  const filters =
    field("Buscar", "q", p.get("q")) +
    select(
      "Orden",
      "sort",
      [
        { id: "newest", name: "Más recientes" },
        { id: "oldest", name: "Más antiguas" },
        { id: "name", name: "Nombre A–Z" },
        { id: "name_desc", name: "Nombre Z–A" },
      ],
      p.get("sort") || "newest",
    ) +
    select("Ubicación", "location", locations, p.get("location"), "Todas") +
    select("Categoría", "category", categories, p.get("category"), "Todas") +
    select("Temporada", "season", seasonRows, p.get("season"), "Todas") +
    select("Etiqueta", "tag", tags, p.get("tag"), "Todas") +
    select(
      "Colección",
      "collection",
      collections,
      p.get("collection"),
      "Todas",
    ) +
    select(
      "Favoritas",
      "favorite",
      [{ id: 1, name: "Solo favoritas" }],
      p.get("favorite"),
      "Todas",
    ) +
    select(
      "Estado",
      "archived",
      [
        { id: 0, name: "Activas" },
        { id: 1, name: "Archivadas" },
      ],
      p.get("archived") ?? 0,
    );
  const cards = items
    .slice(0, 24)
    .map(
      (g) =>
        '<article class="card"><a href="#/prendas/' +
        g.id +
        '"><div class="cover">' +
        img(g.thumbnail, g.name) +
        "</div><h3>" +
        esc(g.name) +
        "</h3></a>" +
        esc(g.location) +
        " · " +
        esc(g.category) +
        '<label><input name="garment" type="checkbox" value="' +
        g.id +
        '">Seleccionar ' +
        esc(g.name) +
        "</label></article>",
    )
    .join("");
  const bulk =
    select("Nuevo destino", "dest", locations, null, "Sin traslado") +
    select("Nueva categoría", "category", categories, null, "Conservar") +
    select("Añadir temporada", "season", seasonRows, null, "Conservar") +
    select("Añadir etiqueta", "tag", tags, null, "Conservar");
  return (
    '<h1>Catálogo</h1><div class="actions">' +
    link("Añadir prenda", "#/prendas/nueva") +
    link("Importar grupos de fotos", "#/lotes") +
    '</div><details class="catalog-filters" ' +
    (matchMedia("(min-width: 701px)").matches ? "open" : "") +
    "><summary>Buscar y filtrar</summary>" +
    form(
      '<div class="fields">' + filters + "</div>",
      "Aplicar filtros",
      (f) => {
        state.dirty = false;
        location.hash =
          "#/catalogo?" + new URLSearchParams([...f].filter(([, v]) => v));
      },
    ) +
    "</details>" +
    (items.length
      ? form(
          '<div class="cards">' +
            cards +
            '</div><details><summary>Editar selección</summary><div class="fields">' +
            bulk +
            "</div></details>",
          "Confirmar cambios en la selección",
          async (f) => {
            const chosen = ids(f, "garment"),
              sql = [];
            if (p.get("archived") === "1")
              throw Error("Reactiva las prendas antes de editarlas en lote.");
            if (!chosen.length) throw Error("Selecciona alguna prenda.");
            if (val(f, "dest"))
              sql.push(...move(chosen, +val(f, "dest"), "Traslado manual"));
            for (const id of chosen) {
              if (val(f, "category"))
                sql.push([
                  "UPDATE garments SET category_id=? WHERE id=?",
                  [+val(f, "category"), id],
                ]);
              if (val(f, "season"))
                sql.push([
                  "INSERT OR IGNORE INTO garment_seasons VALUES (?,?)",
                  [id, val(f, "season")],
                ]);
              if (val(f, "tag"))
                sql.push([
                  "INSERT OR IGNORE INTO garment_tags VALUES (?,?)",
                  [id, +val(f, "tag")],
                ]);
            }
            if (
              sql.length &&
              confirm(
                "¿Aplicar los cambios a las " +
                  chosen.length +
                  " prendas seleccionadas?",
              )
            )
              await save(sql);
          },
        )
      : "<p>No hay prendas que coincidan.</p>") +
    '<div class="actions">' +
    (page > 1 ? link("Anterior", switchPage(page - 1)) : "") +
    (items.length > 24 ? link("Siguiente", switchPage(page + 1)) : "") +
    "</div>"
  );
}
function photoInput() {
  return (
    '<label>Fotos (hasta seis)<input type="file" name="photos" multiple accept="image/jpeg,image/png,image/webp"></label>' +
    field(
      "Número de la nueva foto de portada",
      "cover",
      "",
      'type="number" min="1" max="6"',
    )
  );
}
async function photos(files, gid, cover, offset) {
  if (files.length + offset > 6)
    throw Error("Admite hasta seis fotos por prenda.");
  if (cover && (cover < 1 || cover > files.length))
    throw Error("El número de portada no corresponde a una foto.");
  const sql = [],
    media = [];
  if (cover)
    sql.push([
      "UPDATE garment_images SET is_primary=0 WHERE garment_id=?",
      [gid],
    ]);
  for (const [i, file] of files.entries()) {
    const photo = await preparePhoto(file);
    sql.push(
      statement("garment_images", {
        garment_id: gid,
        ...photo.meta,
        is_primary: Number(cover ? i + 1 === cover : !offset && i === 0),
        sort_order: offset + i + 1,
      }),
      ...photo.integrity,
    );
    media.push(...photo.files);
  }
  return { sql, media };
}
const uploads = (f) => f.getAll("photos").filter((file) => file.size);
export async function garmentEditor(id, batch = false) {
  const g = id ? (await q("SELECT * FROM garments WHERE id=?", id))[0] : {};
  if (!g) throw Error("Prenda inexistente.");
  if (g.archived)
    return (
      "<h1>Prenda archivada</h1><p>Reactiva la prenda en su ficha para editarla.</p>" +
      link("Volver a la ficha", "#/prendas/" + id)
    );
  const [loc, cat, oldSeasons, oldImages, suggestions] = await Promise.all([
    choices("locations"),
    choices("categories"),
    q("SELECT season FROM garment_seasons WHERE garment_id=?", id || 0),
    q("SELECT id FROM garment_images WHERE garment_id=?", id || 0),
    q("SELECT DISTINCT brand,size,color FROM garments"),
  ]);
  if (!loc.length)
    return (
      "<h1>Añadir prenda</h1><p>Crea la ubicación donde guardarás tu primera prenda.</p>" +
      link("Crear ubicación", "#/ajustes")
    );
  const group =
    '<div class="fields">' +
    field("Nombre", "name", g.name, 'required maxlength="120"') +
    select("Ubicación", "location_id", loc, g.location_id) +
    select("Categoría", "category_id", cat, g.category_id) +
    "</div>" +
    photoInput();
  if (batch)
    return (
      "<h1>Importar grupos de fotos</h1>" +
      form(
        "<div data-groups><fieldset><legend>Prenda 1</legend>" +
          group +
          "</fieldset></div>" +
          action("Añadir otro grupo", (el) => {
            const box = el.closest("form").querySelector("[data-groups]");
            const copy = box.firstElementChild.cloneNode(true);
            copy.querySelectorAll("input").forEach((i) => (i.value = ""));
            copy.querySelector("legend").textContent =
              "Prenda " + (box.children.length + 1);
            box.append(copy);
          }),
        "Guardar lote",
        async (f, el) => {
          let gid = await nextId("garments");
          const sql = [],
            media = [];
          const uploads = [...el.querySelectorAll('[name="photos"]')].flatMap(
            (input) => [...input.files],
          );
          if (
            uploads.length > 20 ||
            uploads.reduce((n, f) => n + f.size, 0) > 64 * 1024 ** 2
          )
            throw Error("El lote admite hasta 20 fotos y 64 MiB.");
          for (const box of el.querySelectorAll("fieldset")) {
            const get = (name) => box.querySelector('[name="' + name + '"]');
            const files = [...get("photos").files];
            if (!files.length)
              throw Error("Selecciona al menos una foto por grupo.");
            sql.push(
              statement("garments", {
                id: gid,
                name: get("name").value.trim(),
                location_id: +get("location_id").value,
                category_id: +get("category_id").value,
              }),
            );
            const p = await photos(files, gid, +get("cover").value, 0);
            sql.push(...p.sql);
            media.push(...p.media);
            gid++;
          }
          await save(sql, media, "#/catalogo");
        },
      )
    );
  const suggest = (key, label) =>
    field(
      label,
      key,
      g[key],
      'list="suggest-' +
        key +
        '" maxlength="' +
        { brand: 80, size: 30, color: 60 }[key] +
        '"',
    ) +
    '<datalist id="suggest-' +
    key +
    '">' +
    [...new Set(suggestions.map((x) => x[key]).filter(Boolean))]
      .map((v) => '<option value="' + esc(v) + '">')
      .join("") +
    "</datalist>";
  return (
    "<h1>" +
    (id ? "Editar prenda" : "Añadir prenda") +
    "</h1>" +
    form(
      group +
        '<div class="fields">' +
        suggest("brand", "Marca") +
        suggest("size", "Talla") +
        suggest("color", "Color") +
        field(
          "Precio (€)",
          "price",
          g.price_cents == null ? "" : g.price_cents / 100,
          'type="number" min="0" max="1000000" step=".01"',
        ) +
        field("Fecha de compra", "date", g.purchased_on, 'type="date"') +
        "</div>" +
        field("Notas", "notes", g.notes, 'maxlength="3000"') +
        '<label><input type="checkbox" name="favorite" ' +
        (g.favorite ? "checked" : "") +
        ">Favorita</label>" +
        "<fieldset><legend>Temporadas</legend>" +
        checks(
          seasonRows,
          oldSeasons.map((x) => x.season),
          "season",
        ) +
        "</fieldset>",
      "Guardar prenda",
      async (f) => {
        const gid = id || (await nextId("garments")),
          values = {
            name: val(f, "name"),
            category_id: +val(f, "category_id"),
            favorite: Number(f.has("favorite")),
            brand: val(f, "brand"),
            color: val(f, "color"),
            size: val(f, "size"),
            notes: val(f, "notes"),
            price_cents:
              val(f, "price") === ""
                ? null
                : Math.round(Number(val(f, "price")) * 100),
            purchased_on: val(f, "date") || null,
          };
        const dest = +val(f, "location_id"),
          sql = [];
        if (!id) Object.assign(values, { id: gid, location_id: dest });
        else if (dest !== g.location_id) {
          if (!confirm("¿Confirmar traslado de esta prenda?")) return;
          sql.push(...move([id], dest, "Traslado desde la ficha"));
        }
        sql.push(
          statement("garments", values, id),
          ["DELETE FROM garment_seasons WHERE garment_id=?", [gid]],
          ...f
            .getAll("season")
            .map((s) => ["INSERT INTO garment_seasons VALUES (?,?)", [gid, s]]),
        );
        const p = await photos(
          uploads(f),
          gid,
          +val(f, "cover"),
          oldImages.length,
        );
        await save([...sql, ...p.sql], p.media, "#/prendas/" + gid);
      },
    )
  );
}
export async function detail(id) {
  const [g] = await q(garmentSQL + " WHERE g.id=?", id);
  if (!g) throw Error("Prenda inexistente.");
  const photos = await q(
    "SELECT * FROM garment_images WHERE garment_id=? ORDER BY " + coverOrder,
    id,
  );
  const missing = new Set();
  await Promise.all(
    photos.map(async (p) => {
      for (const name of [p.filename, p.thumbnail, p.preview].filter(Boolean))
        if (!(await optional(state.session.root, "images/" + name)))
          missing.add(p.id);
    }),
  );
  const seasons = await q(
    "SELECT season FROM garment_seasons WHERE garment_id=? ORDER BY season",
    id,
  );
  const looks = await q(
    "SELECT o.id,o.name FROM outfit_items i JOIN outfits o ON o.id=i.outfit_id WHERE garment_id=? ORDER BY o.name",
    id,
  );
  const history = await q(
    "SELECT a.name origin,b.name destination,m.created_at FROM garment_movements m JOIN locations a ON a.id=m.from_id JOIN locations b ON b.id=m.to_id WHERE garment_id=? ORDER BY m.id DESC",
    id,
  );
  const setCover = (pid) => [
    ["UPDATE garment_images SET is_primary=0 WHERE garment_id=?", [id]],
    ["UPDATE garment_images SET is_primary=1 WHERE id=?", [pid]],
  ];
  return (
    link("Volver al catálogo", state.returnTo) +
    "<h1>" +
    esc(g.name) +
    "</h1><p>" +
    [
      g.location,
      g.category,
      g.brand,
      g.size,
      g.color,
      money(g.price_cents),
      g.purchased_on,
      g.notes,
      ...seasons.map((r) => r.season),
    ]
      .filter(Boolean)
      .map(esc)
      .join(" · ") +
    '</p><div class="actions">' +
    link("Editar prenda", "#/prendas/" + id + "/editar") +
    action(g.favorite ? "Quitar de favoritas" : "Marcar favorita", () =>
      save([
        ["UPDATE garments SET favorite=? WHERE id=?", [1 - g.favorite, id]],
      ]),
    ) +
    action(g.archived ? "Reactivar" : "Archivar", () =>
      save([
        ["UPDATE garments SET archived=? WHERE id=?", [1 - g.archived, id]],
      ]),
    ) +
    remove("Eliminar prenda", "garments", id, "#/catalogo") +
    '</div><div class="cards">' +
    photos
      .map(
        (p, i) =>
          '<article class="card"><div class="cover">' +
          (missing.has(p.id)
            ? "Foto no disponible"
            : img(p.preview || p.thumbnail, g.name)) +
          "</div><p>" +
          (i === 0 ? "Portada" : "Foto " + (i + 1)) +
          "</p>" +
          action("Ver original", async () => {
            const url = URL.createObjectURL(
              await read(state.session.root, "images/" + p.filename),
            );
            const dialog = document.createElement("dialog");
            dialog.innerHTML =
              '<img alt="Foto original"><button>Cerrar</button>';
            dialog.querySelector("img").src = url;
            dialog.querySelector("button").onclick = () => dialog.close();
            dialog.onclose = () => {
              URL.revokeObjectURL(url);
              dialog.remove();
            };
            document.body.append(dialog);
            dialog.showModal();
          }) +
          (i ? action("Usar como portada", () => save(setCover(p.id))) : "") +
          (i > 1
            ? action("Subir", () =>
                save(
                  photos.map((r, j) => [
                    "UPDATE garment_images SET sort_order=? WHERE id=?",
                    [j === i ? i - 1 : j === i - 1 ? i : j, r.id],
                  ]),
                ),
              )
            : "") +
          (i > 0 && i < photos.length - 1
            ? action("Bajar", () =>
                save(
                  photos.map((r, j) => [
                    "UPDATE garment_images SET sort_order=? WHERE id=?",
                    [j === i ? i + 1 : j === i + 1 ? i : j, r.id],
                  ]),
                ),
              )
            : "") +
          action("Eliminar foto", async () => {
            if (confirm("¿Eliminar esta foto?"))
              await save([
                ["DELETE FROM garment_images WHERE id=?", [p.id]],
                ...(i === 0 && photos[1] ? setCover(photos[1].id) : []),
              ]);
          }) +
          form(
            '<label>Sustituir foto<input name="photo" type="file" required accept="image/*"></label>',
            "Reparar o sustituir",
            async (f) => {
              const photo = await preparePhoto(f.get("photo"));
              await save(
                [
                  statement("garment_images", photo.meta, p.id),
                  ...photo.integrity,
                ],
                photo.files,
                undefined,
                true,
              );
            },
          ) +
          "</article>",
      )
      .join("") +
    "</div>" +
    (looks.length
      ? "<h2>Outfits con esta prenda</h2>" +
        looks.map((o) => link(o.name, "#/outfits/" + o.id)).join(" ")
      : "") +
    "<h2>Historial de traslados</h2>" +
    (history
      .map(
        (r) =>
          "<p>" +
          esc(r.created_at) +
          " · " +
          esc(r.origin) +
          " → " +
          esc(r.destination) +
          "</p>",
      )
      .join("") || "<p>Sin traslados.</p>")
  );
}
export async function summary() {
  const rows = await q(
    "SELECT l.id location_id,l.name location,c.id category_id,c.name category,count(*) n,count(price_cents) priced,sum(price_cents) total FROM garments g JOIN locations l ON l.id=g.location_id JOIN categories c ON c.id=g.category_id WHERE g.archived=0 GROUP BY l.id,c.id ORDER BY l.name,c.name",
  );
  return (
    "<h1>Resumen</h1><p>" +
    rows.reduce((n, r) => n + r.n, 0) +
    " prendas activas</p><table><thead><tr><th>Ubicación y categoría</th><th>Con precio</th><th>Valor</th></tr></thead><tbody>" +
    rows
      .map(
        (r) =>
          "<tr><td>" +
          link(
            r.location + " · " + r.category,
            "#/catalogo?location=" +
              r.location_id +
              "&category=" +
              r.category_id,
          ) +
          "</td><td>" +
          r.priced +
          " de " +
          r.n +
          "</td><td>" +
          money(r.total) +
          "</td></tr>",
      )
      .join("") +
    "</tbody></table>"
  );
}
