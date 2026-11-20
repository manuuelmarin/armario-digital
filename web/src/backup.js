import {
  ZipReader,
  ZipWriter,
  BlobReader,
  Uint8ArrayReader,
  configure,
} from "@zip.js/zip.js/index-native.js";
import { call, sha } from "./engine";
import { access, bytes, read, write, checked, optional } from "./files";
import { decoded } from "./media";
configure({ useWebWorkers: false, useCompressionStream: true });
const imagePath = /^images\/[a-f0-9]{32}(?:-preview|-thumb)?\.webp$/;
const max = 4 * 1024 ** 3,
  manifestMax = 4 * 1024 ** 2;
async function extract(entry, limit = entry.uncompressedSize) {
  const chunks = [];
  let size = 0;
  await entry.getData(
    new WritableStream({
      write(chunk) {
        size += chunk.length;
        if (size > limit || size > entry.uncompressedSize)
          throw Error("Contenido descomprimido demasiado grande.");
        chunks.push(chunk);
      },
    }),
    { checkSignature: true },
  );
  if (size !== entry.uncompressedSize)
    throw Error("Tamaño de entrada incorrecto.");
  return new Blob(chunks);
}
export async function inspectZip(blob, destination) {
  const reader = new ZipReader(new BlobReader(blob));
  try {
    const entries = new Map();
    let total = 0;
    for await (const e of reader.getEntriesGenerator()) {
      const name = e.filename;
      total += e.uncompressedSize;
      if (
        entries.has(name) ||
        entries.size >= 20002 ||
        e.directory ||
        e.encrypted ||
        e.symlink ||
        ((e.externalFileAttributes >>> 16) & 0o170000) === 0o120000 ||
        total > max
      )
        throw Error("Entradas duplicadas, no permitidas o demasiado grandes.");
      if (
        !["wardrobe.sqlite", "manifest.json"].includes(name) &&
        !imagePath.test(name)
      )
        throw Error("Ruta de copia no válida.");
      entries.set(name, e);
    }
    const entry = entries.get("manifest.json");
    if (!entry || entry.uncompressedSize > manifestMax)
      throw Error("Manifiesto ausente o demasiado grande.");
    const manifest = JSON.parse(
        await (await extract(entry, manifestMax)).text(),
      ),
      fileMap = manifest?.files;
    if (
      manifest?.format !== 1 ||
      !Number.isInteger(manifest.schema_version) ||
      typeof manifest.created_at !== "string" ||
      !fileMap ||
      typeof fileMap !== "object" ||
      Array.isArray(fileMap) ||
      Object.keys(fileMap).length !== entries.size - 1 ||
      !entries.has("wardrobe.sqlite")
    )
      throw Error("Manifiesto incompatible.");
    async function verified(name) {
      const data = await bytes(await extract(entries.get(name)));
      if ((await sha(data)) !== fileMap[name])
        throw Error("Huella incorrecta de " + name);
      return data;
    }
    const data = await verified("wardrobe.sqlite"),
      info = await call("inspect", data);
    if (
      info.version !== manifest.schema_version ||
      info.files.length !== entries.size - 2
    )
      throw Error("Esquema o conjunto de imágenes incorrecto.");
    const hashes = {};
    for (const name of info.files) {
      const path = "images/" + name;
      if (!entries.has(path)) throw Error("Falta " + path);
      const photo = await verified(path);
      (await decoded(photo, "webp")).close();
      if (info.version >= 5 && info.hashes[name] !== fileMap[path])
        throw Error("La foto difiere de su huella original.");
      hashes[name] = fileMap[path];
      if (destination) await checked(destination, path, photo);
    }
    if (destination && info.version < 9)
      await saveOriginal(
        destination,
        "before-schema-" + info.version + "-" + crypto.randomUUID() + ".zip",
        blob,
      );
    return {
      info,
      data:
        destination && info.version < 9
          ? await call("upgrade", data, { hashes })
          : data,
    };
  } finally {
    await reader.close();
  }
}
async function saveOriginal(root, name, blob) {
  const file = await write(root, "backups/" + name, blob);
  await inspectZip(file);
  return file;
}
export async function backup(
  session,
  prefix = "manual",
  day = new Date().toISOString().slice(0, 10),
) {
  const { data, revision } = session.head,
    info = await call("inspect", data);
  if (info.files.length > 20000)
    throw Error(
      "El ZIP histórico admite hasta 20.000 archivos de imagen. Conserva una copia de la carpeta completa.",
    );
  const name =
    prefix === "daily"
      ? "daily-" + day + ".zip"
      : "manual-" + day + "-" + crypto.randomUUID() + ".zip";
  const handle = await access(session.root, "backups/" + name, true),
    stream = await handle.createWritable();
  let parts = [],
    size = 0,
    total = 0;
  async function flush() {
    if (!size) return;
    await stream.write(new Blob(parts));
    parts = [];
    size = 0;
  }
  // Agrupar las escrituras pequeñas sin construir el ZIP completo en memoria.
  const output = new WritableStream({
    async write(chunk) {
      parts.push(chunk.slice());
      size += chunk.byteLength;
      if (size >= 1024 * 1024) await flush();
    },
    close: flush,
  });
  try {
    const zip = new ZipWriter(output, { level: 0 }),
      files = {};
    async function add(path, buffer) {
      total += buffer.byteLength;
      if (total > max) throw Error("La copia excede 4 GiB descomprimidos.");
      await zip.add(path, new Uint8ArrayReader(buffer));
    }
    files["wardrobe.sqlite"] = await sha(data);
    await add("wardrobe.sqlite", data);
    for (const file of info.files) {
      const path = "images/" + file,
        photo = await bytes(await read(session.root, path));
      const hash = await sha(photo);
      if (hash !== info.hashes[file])
        throw Error("La foto difiere de su huella original: " + file);
      files[path] = hash;
      await add(path, photo);
    }
    const manifest = new TextEncoder().encode(
      JSON.stringify({
        format: 1,
        schema_version: info.version,
        created_at: new Date().toISOString(),
        revision,
        files,
      }),
    );
    if (manifest.length > manifestMax)
      throw Error("El manifiesto excede 4 MiB.");
    await add("manifest.json", manifest);
    await zip.close();
    await stream.close();
    const file = await handle.getFile();
    await inspectZip(file);
    return file;
  } catch (error) {
    await stream.abort().catch(() => {});
    throw (
      error ||
      Error(
        "No se pudo completar la copia " +
          name +
          ". Comprueba el espacio disponible y reintenta.",
      )
    );
  }
}
export async function daily(s) {
  const day = new Date().toISOString().slice(0, 10);
  if (!s.release || s.daily === day) return;
  if (s.pendingDaily) return s.pendingDaily;
  s.pendingDaily = ensureDaily(s, day);
  try {
    await s.pendingDaily;
  } finally {
    s.pendingDaily = null;
  }
}
async function ensureDaily(s, day) {
  const existing = await optional(s.root, "backups/daily-" + day + ".zip");
  if (existing?.size) {
    try {
      await inspectZip(existing);
    } catch (error) {
      throw Error(
        "No se pudo verificar " +
          existing.name +
          ". Conserva ese ZIP fuera de backups y reintenta para generar la copia del día. " +
          error.message,
      );
    }
  } else await backup(s, "daily", day);
  s.daily = day;
}
export async function prune(s, keep) {
  if (!s.release || !Number.isInteger(keep) || keep < 1 || keep > 365)
    throw Error("Elige entre 1 y 365 copias.");
  const dir = await s.root.getDirectoryHandle("backups"),
    names = [];
  for await (const [name, entry] of dir.entries())
    if (entry.kind === "file" && /^daily-\d{4}-\d{2}-\d{2}\.zip$/.test(name))
      names.push(name);
  names.sort().reverse();
  if (names.length <= keep) return 0;
  for (const name of names.slice(0, keep))
    await inspectZip(await (await dir.getFileHandle(name)).getFile());
  for (const name of names.slice(keep)) await dir.removeEntry(name);
  return names.length - keep;
}
