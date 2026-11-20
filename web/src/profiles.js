import { schema, prompt } from "./profile-contract";
import { q, esc, link, form, action, field, save, val, state } from "./ui";
import { read } from "./files";
import { sha } from "./engine";
import { chat, VISION_MODEL } from "./ollama";

function validate(value, rule) {
  if (rule.type === "object") {
    if (
      !value ||
      Array.isArray(value) ||
      typeof value !== "object" ||
      Object.keys(value).length !== Object.keys(rule.properties).length ||
      Object.keys(rule.properties).some((key) => !Object.hasOwn(value, key))
    )
      throw Error("La descripción no tiene los campos esperados.");
    return Object.fromEntries(
      Object.entries(rule.properties).map(([key, child]) => [
        key,
        validate(value[key], child),
      ]),
    );
  }
  if (rule.type === "string") {
    if (
      typeof value !== "string" ||
      Array.from(value).length > (rule.maxLength || 2000) ||
      /[\x00-\x08\x0b\x0c\x0e-\x1f]/.test(value)
    )
      throw Error("Un texto de la descripción no es válido.");
    value = value.trim();
    if (rule.enum && !rule.enum.includes(value))
      throw Error("Una opción no es válida.");
    return value;
  }
  if (rule.type === "integer") {
    if (
      !Number.isInteger(value) ||
      value < rule.minimum ||
      value > rule.maximum
    )
      throw Error("La formalidad debe estar entre 0 y 5.");
    return value;
  }
  if (rule.type === "array") {
    if (!Array.isArray(value) || value.length > rule.maxItems)
      throw Error("Lista de estilos inválida.");
    return value.map((item) => validate(item, rule.items));
  }
  throw Error("Esquema no admitido.");
}
export function validProfile(value) {
  const profile = validate(value, schema);
  const type = profile.identification.type,
    length = profile.shape.leg_length;
  if (
    (type === "pantalon_corto" && length !== "corto") ||
    (!["pantalon", "pantalon_corto"].includes(type) && length !== "no_visible")
  )
    throw Error("Revisa el largo de pantalón.");
  return profile;
}
async function snapshot(id) {
  const [row] = await q(
    "SELECT g.archived,i.filename,h.sha256,coalesce(p.revision,0) revision FROM garments g LEFT JOIN garment_images i ON i.id=(SELECT id FROM garment_images WHERE garment_id=g.id ORDER BY is_primary DESC,id LIMIT 1) LEFT JOIN image_integrity h ON h.name=i.filename LEFT JOIN garment_profiles p ON p.garment_id=g.id WHERE g.id=?",
    id,
  );
  if (!row || row.archived || !row.filename || !row.sha256)
    throw Error("Añade una foto principal verificada a la prenda activa.");
  return row;
}
const labels = {
  description: "Descripción",
  identification: "Tipo de prenda",
  "identification.type": "Tipo",
  "identification.subtype": "Subtipo",
  palette: "Colores",
  "palette.main": "Color principal",
  "palette.secondary": "Colores secundarios",
  "palette.contrast": "Contraste",
  pattern: "Estampado",
  "pattern.kind": "Tipo de estampado",
  "pattern.distribution": "Distribución",
  shape: "Forma",
  "shape.silhouette": "Silueta",
  "shape.sleeves": "Mangas",
  "shape.leg_length": "Largo del pantalón",
  surface: "Superficie",
  "surface.texture": "Textura",
  "surface.finish": "Acabado",
  details: "Detalles",
  aesthetics: "Estética",
  "aesthetics.styles": "Estilos",
  "aesthetics.formality": "Formalidad (0 a 5)",
};
function fields(rule, value, prefix = "") {
  return Object.entries(rule.properties)
    .map(([key, child]) => {
      const name = prefix ? prefix + "." + key : key,
        current = value[key];
      if (child.type === "object")
        return (
          "<fieldset><legend>" +
          esc(labels[name] || key) +
          "</legend>" +
          fields(child, current, name) +
          "</fieldset>"
        );
      if (child.enum)
        return (
          "<label>" +
          esc(labels[name] || name) +
          '<select name="' +
          esc(name) +
          '">' +
          child.enum
            .map(
              (v) =>
                '<option value="' +
                esc(v) +
                '"' +
                (current === v ? " selected" : "") +
                ">" +
                esc(v) +
                "</option>",
            )
            .join("") +
          "</select></label>"
        );
      if (child.type === "array")
        return field(
          labels[name] || name,
          name,
          current.join(", "),
          'maxlength="204"',
        );
      return field(
        labels[name] || name,
        name,
        current,
        child.type === "integer"
          ? 'type="number" min="0" max="5" required'
          : 'maxlength="' + child.maxLength + '"',
      );
    })
    .join("");
}
function fromForm(data, rule, prefix = "") {
  return Object.fromEntries(
    Object.entries(rule.properties).map(([key, child]) => {
      const name = prefix ? prefix + "." + key : key;
      if (child.type === "object") return [key, fromForm(data, child, name)];
      const raw = val(data, name);
      return [
        key,
        child.type === "integer"
          ? Number(raw)
          : child.type === "array"
            ? raw
                .split(",")
                .map((x) => x.trim())
                .filter(Boolean)
            : raw,
      ];
    }),
  );
}
let proposal;
export async function profilePage(id) {
  const [garment] = await q("SELECT name FROM garments WHERE id=?", id);
  if (!garment) throw Error("Prenda inexistente.");
  const [saved] = await q(
    "SELECT * FROM garment_profiles WHERE garment_id=?",
    id,
  );
  const selected =
    proposal?.id === id && proposal.session === state.session ? proposal : null;
  const profile =
    selected?.value || (saved && validProfile(JSON.parse(saved.profile_json)));
  let html =
    link("Volver a la prenda", "#/prendas/" + id) +
    "<h1>Descripción de " +
    esc(garment.name) +
    "</h1>";
  html += action("Analizar foto principal", async () => {
    if (
      state.dirty &&
      !confirm(
        "¿Descartar los cambios de esta descripción y analizar de nuevo?",
      )
    )
      return;
    const session = state.session,
      source = await snapshot(id);
    const image = await read(session.root, "images/" + source.filename);
    const data = await image.arrayBuffer();
    if ((await sha(data)) !== source.sha256)
      throw Error("La foto no coincide con su huella registrada.");
    const bitmap = await createImageBitmap(image);
    const scale = Math.min(1, 1024 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d");
    context.fillStyle = "#fafafa";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    bitmap.close();
    const encoded = canvas.toDataURL("image/jpeg", 0.88).split(",")[1];
    const result = await chat(
      VISION_MODEL,
      prompt,
      "Describe la prenda de esta fotografía según los siete grupos.",
      schema,
      encoded,
    );
    if (
      state.session !== session ||
      JSON.stringify(await snapshot(id)) !== JSON.stringify(source) ||
      (await sha(
        await (
          await read(session.root, "images/" + source.filename)
        ).arrayBuffer(),
      )) !== source.sha256
    )
      throw Error(
        "La prenda o su fotografía cambiaron durante el análisis. Vuelve a intentarlo.",
      );
    state.dirty = false;
    proposal = {
      id,
      session,
      source,
      value: validProfile(result.value),
      digest: result.digest,
    };
    await state.refresh();
  });
  if (!profile)
    return (
      html + "<p>Analiza la foto principal para preparar una descripción.</p>"
    );
  let source = selected?.source;
  if (!source && saved) {
    const current = await snapshot(id);
    if (
      current.filename === saved.source_name &&
      current.sha256 === saved.source_hash &&
      current.revision === saved.revision
    )
      source = current;
    else
      html +=
        "<p>La foto principal ha cambiado. Analízala de nuevo para actualizar la descripción.</p>";
  }
  html +=
    "<p>Revisa cada campo antes de guardar. Los estilos se separan con comas.</p>" +
    form(fields(schema, profile), "Guardar descripción", async (data) => {
      if (!source)
        throw Error(
          "Vuelve a analizar la foto para revisar y guardar esta descripción.",
        );
      const current = await snapshot(id);
      if (
        JSON.stringify(current) !== JSON.stringify(source) ||
        (await sha(
          await (
            await read(state.session.root, "images/" + source.filename)
          ).arrayBuffer(),
        )) !== source.sha256
      )
        throw Error(
          "La prenda o su fotografía han cambiado. Vuelve a analizarla.",
        );
      const cleaned = validProfile(fromForm(data, schema));
      const provenance = JSON.stringify({
        origin: selected ? "vision_reviewed" : "manual",
        schema: 1,
        ...(selected
          ? {
              model: VISION_MODEL,
              digest: selected.digest,
              prompt: "wardrobe-1",
            }
          : {}),
        approval_id: crypto.randomUUID().replaceAll("-", ""),
      });
      await save(
        [
          [
            "INSERT INTO garment_profiles(garment_id,revision,profile_json,source_name,source_hash,provenance_json) VALUES(?,?,?,?,?,?) ON CONFLICT(garment_id) DO UPDATE SET revision=excluded.revision,profile_json=excluded.profile_json,source_name=excluded.source_name,source_hash=excluded.source_hash,provenance_json=excluded.provenance_json,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')",
            [
              id,
              source.revision + 1,
              JSON.stringify(cleaned),
              source.filename,
              source.sha256,
              provenance,
            ],
          ],
        ],
        [],
        "#/prendas/" + id,
      );
      proposal = null;
    });
  return html;
}
