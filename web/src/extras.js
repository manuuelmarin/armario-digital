import {
  q,
  esc,
  field,
  form,
  action,
  link,
  img,
  val,
  nextId,
  statement,
  save,
  remove,
} from "./ui";
import { preparePhoto } from "./media";
function http(value) {
  if (!value) return "";
  const url = new URL(value);
  if (!["https:", "http:"].includes(url.protocol))
    throw Error("El enlace debe ser HTTP o HTTPS.");
  return url.href;
}
export async function boards(id) {
  if (!id) {
    const list = await q("SELECT * FROM boards ORDER BY name");
    return (
      '<h1>Inspiración</h1><div class="cards">' +
      list
        .map(
          (b) =>
            '<article class="card"><h3>' +
            link(b.name, "#/inspiracion/" + b.id) +
            "</h3>" +
            esc(b.notes) +
            "</article>",
        )
        .join("") +
      "</div>" +
      form(
        field("Nombre del tablero", "name", "", 'required maxlength="100"') +
          field("Notas", "notes"),
        "Crear tablero",
        async (f) => {
          const key = await nextId("boards");
          await save(
            [
              statement("boards", {
                id: key,
                name: val(f, "name"),
                notes: val(f, "notes"),
              }),
            ],
            [],
            "#/inspiracion/" + key,
          );
        },
      )
    );
  }
  const [b] = await q("SELECT * FROM boards WHERE id=?", id);
  if (!b) throw Error("No existe el tablero.");
  const items = await q(
    "SELECT * FROM board_items WHERE board_id=? ORDER BY id",
    id,
  );
  const itemForm = (r = {}) =>
    form(
      '<div class="fields">' +
        field("Descripción", "caption", r.caption) +
        field("Enlace", "link", r.link, 'type="url"') +
        field(
          "Posición horizontal",
          "x",
          r.x ?? 0,
          'type="number" required min="0" max="2000"',
        ) +
        field(
          "Posición vertical",
          "y",
          r.y ?? 0,
          'type="number" required min="0" max="2000"',
        ) +
        field(
          "Ancho",
          "width",
          r.width ?? 200,
          'type="number" required min="100" max="600"',
        ) +
        '</div><label>Imagen opcional<input type="file" name="image" accept="image/jpeg,image/png,image/webp"></label>',
      r.id ? "Guardar elemento" : "Añadir elemento",
      async (f) => {
        const data = {
            board_id: id,
            caption: val(f, "caption"),
            link: http(val(f, "link")),
            x: +val(f, "x"),
            y: +val(f, "y"),
            width: +val(f, "width"),
          },
          sql = [],
          files = [];
        if (f.get("image").size) {
          const photo = await preparePhoto(f.get("image"));
          for (const k of ["filename", "thumbnail", "preview"])
            data[k] = photo.meta[k];
          sql.push(...photo.integrity);
          files.push(...photo.files);
        }
        if (!r.filename && !data.filename && !data.link && !data.caption)
          throw Error("Añade una foto, enlace o descripción.");
        await save([...sql, statement("board_items", data, r.id)], files);
      },
    );
  return (
    link("Todos los tableros", "#/inspiracion") +
    "<h1>" +
    esc(b.name) +
    "</h1><p>" +
    esc(b.notes) +
    '</p><div class="collage"><div class="canvas" style="width:' +
    Math.max(300, ...items.map((r) => r.x + r.width)) +
    "px;height:" +
    Math.max(360, ...items.map((r) => r.y + r.width + 80)) +
    'px">' +
    items
      .map(
        (r) =>
          '<div class="pin" style="left:' +
          Number(r.x) +
          "px;top:" +
          Number(r.y) +
          "px;width:" +
          Number(r.width) +
          'px">' +
          (r.filename ? img(r.preview || r.thumbnail, r.caption) : "") +
          "<p>" +
          esc(r.caption) +
          "</p>" +
          (r.link && /^https?:\/\//i.test(r.link)
            ? '<a target="_blank" rel="noopener noreferrer" href="' +
              esc(r.link) +
              '">Abrir enlace</a>'
            : "") +
          "</div>",
      )
      .join("") +
    "</div></div><h2>Elementos del tablero</h2>" +
    items
      .map(
        (r) =>
          "<details><summary>" +
          esc(r.caption || "Elemento " + r.id) +
          "</summary>" +
          itemForm(r) +
          remove(
            "Eliminar elemento",
            "board_items",
            r.id,
            "#/inspiracion/" + id,
          ) +
          "</details>",
      )
      .join("") +
    itemForm() +
    "<details><summary>Editar tablero</summary>" +
    form(
      field("Nombre", "name", b.name, 'required maxlength="100"') +
        field("Notas", "notes", b.notes),
      "Guardar tablero",
      (f) =>
        save([
          statement(
            "boards",
            { name: val(f, "name"), notes: val(f, "notes") },
            id,
          ),
        ]),
    ) +
    remove("Eliminar tablero", "boards", id, "#/inspiracion") +
    "</details>"
  );
}
export async function weather() {
  const [r] = await q("SELECT * FROM weather_cache");
  const forecast = r ? JSON.parse(r.payload) : [];
  return (
    "<h1>Tiempo</h1>" +
    (r
      ? "<h2>" +
        esc(r.label) +
        "</h2><p>Actualizado el " +
        esc(r.fetched_at) +
        "</p>" +
        forecast
          .map(
            (d) =>
              "<p>" +
              esc(d.date) +
              " · " +
              esc(d.min) +
              " a " +
              esc(d.max) +
              " °C · " +
              esc(d.rain) +
              " % de lluvia</p>",
          )
          .join("")
      : "<p>Aún no hay previsión guardada.</p>") +
    form(
      '<p>Al actualizar se envían las coordenadas a Open-Meteo.</p><div class="fields">' +
        field("Lugar", "label", r?.label, 'required maxlength="80"') +
        field(
          "Latitud",
          "latitude",
          r?.latitude,
          'type="number" min="-90" max="90" step="any" required',
        ) +
        field(
          "Longitud",
          "longitude",
          r?.longitude,
          'type="number" min="-180" max="180" step="any" required',
        ) +
        "</div>",
      "Actualizar previsión",
      async (f) => {
        const lat = +val(f, "latitude"),
          lon = +val(f, "longitude");
        if (
          !Number.isFinite(lat) ||
          !Number.isFinite(lon) ||
          Math.abs(lat) > 90 ||
          Math.abs(lon) > 180
        )
          throw Error("Coordenadas no válidas.");
        const query = new URLSearchParams({
          latitude: lat,
          longitude: lon,
          daily:
            "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
          forecast_days: 5,
          timezone: "auto",
        });
        let rows;
        try {
          const res = await fetch(
            "https://api.open-meteo.com/v1/forecast?" + query,
            {
              redirect: "error",
              credentials: "omit",
              referrerPolicy: "no-referrer",
              signal: AbortSignal.timeout(8000),
            },
          );
          if (!res.ok) throw Error();
          const raw = await res.text();
          if (raw.length > 200000) throw Error();
          const { daily: d } = JSON.parse(raw);
          rows = d.time.map((date, i) => ({
            date,
            max: d.temperature_2m_max[i],
            min: d.temperature_2m_min[i],
            rain: d.precipitation_probability_max[i],
          }));
          if (
            !rows.length ||
            rows.length > 5 ||
            rows.some(
              (v) =>
                !/^\d{4}-\d{2}-\d{2}$/.test(v.date) ||
                ![v.min, v.max, v.rain].every(Number.isFinite) ||
                v.rain < 0 ||
                v.rain > 100,
            )
          )
            throw Error();
        } catch {
          throw Error(
            "No se pudo actualizar. Se conserva la última previsión.",
          );
        }
        await save([
          [
            "INSERT OR REPLACE INTO weather_cache VALUES (1,?,?,?,?,?)",
            [
              val(f, "label"),
              lat,
              lon,
              new Date().toISOString(),
              JSON.stringify(rows),
            ],
          ],
        ]);
      },
    ) +
    (r
      ? action("Borrar previsión", () => {
          if (confirm("¿Borrar la previsión guardada?"))
            return save([["DELETE FROM weather_cache"]]);
        })
      : "")
  );
}
