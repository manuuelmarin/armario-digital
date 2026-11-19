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
  picker,
  state,
} from "./ui";
import { garmentSQL, move } from "./inventory";
const definitions = {
  outfits: {
    table: "outfits",
    title: "Outfits",
    single: "outfit",
    join: "outfit_items",
    key: "outfit_id",
  },
  colecciones: {
    table: "collections",
    title: "Colecciones",
    single: "colección",
    join: "collection_items",
    key: "collection_id",
  },
  etiquetas: {
    table: "tags",
    title: "Etiquetas",
    single: "etiqueta",
    join: "garment_tags",
    key: "tag_id",
  },
};
export async function groups(route, id, p) {
  const d = definitions[route],
    outfit = route === "outfits",
    tag = route === "etiquetas";
  const locations = outfit
    ? await q("SELECT id,name FROM locations ORDER BY name")
    : [];
  if (!id) {
    let sql = "SELECT * FROM " + d.table + " WHERE 1=1",
      args = [];
    if (outfit) {
      sql += " AND instr(fold(name||' '||notes||' '||occasion),fold(?))>0";
      args.push(p.get("q") || "");
      if (p.get("favorite")) sql += " AND favorite=1";
      if (p.get("location") && p.get("complete")) {
        sql +=
          " AND EXISTS(SELECT 1 FROM outfit_items WHERE outfit_id=outfits.id) AND NOT EXISTS(SELECT 1 FROM outfit_items i JOIN garments g ON g.id=i.garment_id WHERE i.outfit_id=outfits.id AND (g.location_id<>? OR g.archived=1))";
        args.push(+p.get("location"));
      }
    }
    const items = await q(sql + " ORDER BY name", ...args);
    const byOutfit = new Map();
    if (outfit) {
      const members = await q(
        garmentSQL.replace("SELECT g.*", "SELECT i.outfit_id,g.*") +
          " JOIN outfit_items i ON i.garment_id=g.id ORDER BY i.outfit_id,g.name",
      );
      for (const g of members) {
        if (!byOutfit.has(g.outfit_id)) byOutfit.set(g.outfit_id, []);
        byOutfit.get(g.outfit_id).push(g);
      }
    }
    function availability(id) {
      if (!outfit) return "";
      const pieces = byOutfit.get(id) || [],
        missing = pieces.filter(
          (g) => g.archived || g.location_id !== +p.get("location"),
        );
      return (
        (pieces[0]
          ? '<div class="cover">' +
            img(pieces[0].thumbnail, pieces[0].name) +
            "</div>"
          : "") +
        (p.get("location") && pieces.length
          ? "<p>" +
            (missing.length
              ? "Faltan: " + missing.map((g) => esc(g.name)).join(", ")
              : "Completo en esta ubicación") +
            "</p>"
          : "")
      );
    }
    const filters = outfit
      ? form(
          '<div class="fields">' +
            field("Buscar", "q", p.get("q")) +
            select(
              "Disponible en",
              "location",
              locations,
              p.get("location"),
              "Cualquier ubicación",
            ) +
            select(
              "Disponibilidad",
              "complete",
              [{ id: 1, name: "Solo completos" }],
              p.get("complete"),
              "Mostrar todos",
            ) +
            select(
              "Favoritos",
              "favorite",
              [{ id: 1, name: "Solo favoritos" }],
              p.get("favorite"),
              "Todos",
            ) +
            "</div>",
          "Filtrar",
          (f) => {
            state.dirty = false;
            location.hash =
              "#/outfits?" + new URLSearchParams([...f].filter(([, v]) => v));
          },
        )
      : "";
    return (
      "<h1>" +
      d.title +
      "</h1>" +
      link("Crear " + d.single, "#/" + route + "/nuevo") +
      (tag
        ? ""
        : route === "colecciones"
          ? link("Etiquetas", "#/etiquetas")
          : "") +
      filters +
      '<div class="cards">' +
      items
        .map(
          (r) =>
            '<article class="card"><h3>' +
            link(r.name, "#/" + route + "/" + r.id) +
            "</h3>" +
            availability(r.id) +
            esc(r.notes ?? "") +
            "</article>",
        )
        .join("") +
      "</div>"
    );
  }
  const isNew = id === "nuevo",
    row = isNew
      ? {}
      : (await q("SELECT * FROM " + d.table + " WHERE id=?", id))[0];
  if (!row) throw Error("No existe la agrupación.");
  const chosen = isNew
    ? []
    : await q(
        garmentSQL +
          " JOIN " +
          d.join +
          " i ON i.garment_id=g.id WHERE i." +
          d.key +
          "=? ORDER BY g.name",
        id,
      );
  const available = await q(
    "SELECT id,name FROM garments WHERE archived=0 ORDER BY name",
  );
  const current = chosen.map((g) => g.id);
  const fields =
    field(
      "Nombre",
      "name",
      row.name,
      'required maxlength="' + (tag ? 60 : outfit ? 120 : 100) + '"',
    ) +
    (tag ? "" : field("Notas", "notes", row.notes, 'maxlength="3000"')) +
    (outfit
      ? field("Ocasión", "occasion", row.occasion, 'maxlength="80"') +
        '<label><input type="checkbox" name="favorite" ' +
        (row.favorite ? "checked" : "") +
        ">Favorito</label>"
      : "");
  return (
    link("Volver", "#/" + route) +
    "<h1>" +
    esc(isNew ? "Crear " + d.single : row.name) +
    "</h1>" +
    (outfit && chosen.length
      ? "<p>Disponibilidad · " +
        esc(
          [
            ...new Set(
              chosen.map((g) => (g.archived ? "Archivada" : g.location)),
            ),
          ].join(", "),
        ) +
        "</p>"
      : "") +
    '<div class="list">' +
    chosen
      .map(
        (g) =>
          '<div class="row">' +
          img(g.thumbnail, g.name) +
          link(g.name, "#/prendas/" + g.id) +
          " " +
          esc(g.location) +
          "</div>",
      )
      .join("") +
    "</div>" +
    form(
      '<div class="fields">' + fields + "</div>" + picker(available, current),
      "Guardar " + d.single,
      async (f) => {
        const key = isNew ? await nextId(d.table) : id,
          values = { name: val(f, "name") };
        if (isNew) values.id = key;
        if (!tag) values.notes = val(f, "notes");
        if (outfit)
          Object.assign(values, {
            occasion: val(f, "occasion"),
            favorite: Number(f.has("favorite")),
          });
        if (
          outfit &&
          !ids(f, "garment").length &&
          !chosen.some((g) => g.archived)
        )
          throw Error("Selecciona al menos una prenda.");
        const sql = [
          statement(d.table, values, isNew ? null : id),
          ["DELETE FROM " + d.join + " WHERE " + d.key + "=?", [key]],
        ];
        if (outfit && !isNew)
          sql.push(["DELETE FROM outfit_origins WHERE outfit_id=?", [key]]);
        for (const gid of new Set([
          ...ids(f, "garment"),
          ...chosen.filter((g) => g.archived).map((g) => g.id),
        ]))
          sql.push([
            "INSERT INTO " +
              d.join +
              " (" +
              d.key +
              ",garment_id) VALUES (?,?)",
            [key, gid],
          ]);
        await save(sql, [], "#/" + route + "/" + key);
      },
    ) +
    (isNew
      ? ""
      : '<div class="actions">' +
        (outfit
          ? action("Duplicar outfit", async () => {
              const key = await nextId("outfits");
              await save(
                [
                  statement("outfits", {
                    id: key,
                    name: row.name.slice(0, 111) + " (copia)",
                    occasion: row.occasion,
                    notes: row.notes,
                  }),
                  [
                    "INSERT INTO outfit_items SELECT ?,garment_id FROM outfit_items WHERE outfit_id=?",
                    [key, id],
                  ],
                ],
                [],
                "#/outfits/" + key,
              );
            })
          : "") +
        remove("Eliminar " + d.single, d.table, id, "#/" + route) +
        "</div>")
  );
}
export async function trips(id) {
  if (!id) {
    const rows = await q("SELECT * FROM trips ORDER BY id DESC");
    return (
      "<h1>Maletas</h1>" +
      link("Crear maleta", "#/maletas/nueva") +
      '<div class="cards">' +
      rows
        .map(
          (r) =>
            '<article class="card"><h3>' +
            link(r.name, "#/maletas/" + r.id) +
            "</h3>" +
            esc(r.starts_on) +
            "</article>",
        )
        .join("") +
      "</div>"
    );
  }
  const fresh = id === "nueva",
    t = fresh ? {} : (await q("SELECT * FROM trips WHERE id=?", id))[0];
  if (!t) throw Error("No existe la maleta.");
  const loc = await q("SELECT id,name FROM locations ORDER BY id");
  if (loc.length < 2)
    return (
      "<h1>Maletas</h1><p>Añade dos ubicaciones para elegir el origen y el destino del viaje.</p>" +
      link("Gestionar ubicaciones", "#/ajustes")
    );
  const editor = form(
    '<div class="fields">' +
      field("Nombre del viaje", "name", t.name, 'required maxlength="120"') +
      select("Origen", "origin", loc, t.origin_id) +
      select("Destino", "destination", loc, t.destination_id ?? loc[1].id) +
      field("Salida", "start", t.starts_on, 'type="date"') +
      field("Vuelta", "end", t.ends_on, 'type="date"') +
      field("Notas", "notes", t.notes) +
      "</div>",
    "Guardar viaje",
    async (f) => {
      const key = fresh ? await nextId("trips") : id;
      const values = {
        name: val(f, "name"),
        origin_id: +val(f, "origin"),
        destination_id: +val(f, "destination"),
        starts_on: val(f, "start") || null,
        ends_on: val(f, "end") || null,
        notes: val(f, "notes"),
      };
      if (values.origin_id === values.destination_id)
        throw Error("Elige un origen y un destino distintos.");
      if (fresh) values.id = key;
      await save(
        [statement("trips", values, fresh ? null : id)],
        [],
        "#/maletas/" + key,
      );
    },
  );
  if (fresh) return "<h1>Crear maleta</h1>" + editor;
  const [items, garments, outfits] = await Promise.all([
    q(
      "SELECT i.*,g.name,g.location_id,g.archived,(SELECT thumbnail FROM garment_images WHERE garment_id=g.id ORDER BY is_primary DESC,coalesce(sort_order,id),id LIMIT 1) thumbnail FROM trip_items i LEFT JOIN garments g ON g.id=i.garment_id WHERE trip_id=? ORDER BY i.id",
      id,
    ),
    q("SELECT id,name FROM garments WHERE archived=0 ORDER BY name"),
    q("SELECT id,name FROM outfits ORDER BY name"),
  ]);
  const list = items
    .map(
      (i) =>
        '<div class="row">' +
        (i.garment_id ? img(i.thumbnail, i.name) : "") +
        "<strong>" +
        esc(i.name || i.label) +
        "</strong> · " +
        (i.packed ? "Preparado" : "Pendiente") +
        " " +
        action(i.packed ? "Marcar pendiente" : "Marcar preparado", () =>
          save([
            [
              "UPDATE trip_items SET packed=? WHERE id=? AND trip_id=?",
              [1 - i.packed, i.id, id],
            ],
          ]),
        ) +
        action("Quitar de la maleta", () =>
          save([
            ["DELETE FROM trip_items WHERE id=? AND trip_id=?", [i.id, id]],
          ]),
        ) +
        "</div>",
    )
    .join("");
  const add = form(
    picker(garments) +
      select("Incluir un outfit", "outfit", outfits, null, "Ninguno") +
      field("Objeto libre", "label", "", 'maxlength="120"'),
    "Añadir a la maleta",
    async (f) => {
      const chosen = new Set(ids(f, "garment"));
      if (val(f, "outfit"))
        for (const row of await q(
          "SELECT g.id,g.archived FROM outfit_items i JOIN garments g ON g.id=i.garment_id WHERE outfit_id=?",
          +val(f, "outfit"),
        )) {
          if (row.archived)
            throw Error("El outfit contiene una prenda archivada.");
          chosen.add(row.id);
        }
      const sql = [...chosen].map((g) => [
        "INSERT OR IGNORE INTO trip_items(trip_id,garment_id) VALUES (?,?)",
        [id, g],
      ]);
      if (val(f, "label"))
        sql.push([
          "INSERT OR IGNORE INTO trip_items(trip_id,label) VALUES (?,?)",
          [id, val(f, "label")],
        ]);
      if (sql.length) await save(sql);
    },
  );
  const clone = async (back) => {
    const key = await nextId("trips");
    await save(
      [
        statement("trips", {
          id: key,
          name: t.name.slice(0, 110) + (back ? " (vuelta)" : " (copia)"),
          origin_id: back ? t.destination_id : t.origin_id,
          destination_id: back ? t.origin_id : t.destination_id,
          notes: t.notes,
        }),
        [
          "INSERT INTO trip_items(trip_id,garment_id,label) SELECT ?,garment_id,label FROM trip_items WHERE trip_id=?",
          [key, id],
        ],
      ],
      [],
      "#/maletas/" + key,
    );
  };
  const eligible = items
    .filter(
      (i) =>
        i.garment_id &&
        i.packed &&
        !i.archived &&
        i.location_id === t.origin_id,
    )
    .map((i) => ({ id: i.garment_id, name: i.name }));
  return (
    '<section class="trip-sheet">' +
    link("Todas las maletas", "#/maletas") +
    "<h1>" +
    esc(t.name) +
    "</h1><p>" +
    esc(loc.find((l) => l.id === t.origin_id).name) +
    " → " +
    esc(loc.find((l) => l.id === t.destination_id).name) +
    "</p><p>" +
    [t.starts_on, t.ends_on, t.notes].filter(Boolean).map(esc).join(" · ") +
    "</p>" +
    '<div class="list">' +
    list +
    '</div></section><div class="no-print">' +
    '<div class="actions">' +
    action("Imprimir", () => print()) +
    action("Duplicar maleta", () => clone(false)) +
    action("Crear viaje de vuelta", () => clone(true)) +
    remove("Eliminar maleta", "trips", id, "#/maletas") +
    "</div><details><summary>Editar viaje</summary>" +
    editor +
    "</details><h2>Añadir elementos</h2>" +
    add +
    "<h2>Trasladar a destino</h2>" +
    (eligible.length
      ? form(
          picker(
            eligible,
            eligible.map((g) => g.id),
          ),
          "Confirmar traslado",
          async (f) => {
            const selected = ids(f, "garment");
            if (
              selected.length &&
              confirm("¿Han llegado estas prendas al destino?")
            )
              await save(move(selected, t.destination_id, "Viaje: " + t.name));
          },
        )
      : "<p>Se podrán trasladar las prendas preparadas que estén en el origen.</p>") +
    "</div>"
  );
}
