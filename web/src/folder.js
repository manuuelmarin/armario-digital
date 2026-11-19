import { call, sha } from "./engine";
import { read, write, bytes, checked, optional } from "./files";
const marker = "armario.json",
  enc = new TextEncoder();
const UUID = /^[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}$/;
const stringify = (value) => enc.encode(JSON.stringify(value));
async function writer(uuid) {
  let release;
  const hold = new Promise((done) => {
    release = done;
  });
  return new Promise((resolve, reject) =>
    navigator.locks
      .request(
        "armario-digital:writer:" + uuid,
        { ifAvailable: true },
        (lock) => {
          resolve(lock ? release : null);
          if (lock) return hold;
        },
      )
      .catch(reject),
  );
}
async function generations(root, uuid) {
  const valid = [];
  let damaged = false;
  for (const slot of ["a", "b"]) {
    const prefix = "catalogo/" + slot;
    const receipt = await optional(root, prefix + ".commit.json");
    if (!receipt) {
      if (await optional(root, prefix + ".sqlite")) damaged = true;
      continue;
    }
    let r;
    try {
      r = JSON.parse(await receipt.text());
    } catch {
      damaged = true;
      continue;
    }
    if (r.schema > 9 || r.format > 1)
      throw Error("Formato posterior. Actualiza la aplicación.");
    if (r.uuid !== uuid) throw Error("Conflicto de identidad del armario.");
    const file = await optional(root, prefix + ".sqlite");
    if (
      !file ||
      file.size !== r.length ||
      !Number.isSafeInteger(r.revision) ||
      r.revision < 1 ||
      !UUID.test(r.operation) ||
      r.format !== 1
    ) {
      damaged = true;
      continue;
    }
    const data = await bytes(file);
    if ((await sha(data)) !== r.hash) {
      damaged = true;
      continue;
    }
    try {
      const info = await call("inspect", data);
      if (info.version !== r.schema) throw Error();
    } catch {
      damaged = true;
      continue;
    }
    valid.push({ ...r, slot, data });
  }
  valid.sort((a, b) => b.revision - a.revision);
  if (!valid.length)
    throw Error(
      "No hay una revisión válida. Conserva la carpeta y restaura una copia en otra.",
    );
  if (
    valid.length === 2 &&
    (valid[0].parent !== valid[1].hash ||
      valid[0].revision !== valid[1].revision + 1)
  )
    throw Error(
      "Las revisiones están en conflicto. Conserva la carpeta antes de recuperar.",
    );
  return { valid, damaged };
}
async function publish(root, uuid, base, operation, data) {
  const slot = base?.slot === "a" ? "b" : "a",
    prefix = "catalogo/" + slot;
  const file = await checked(root, prefix + ".sqlite", data);
  const { version } = await call("inspect", await bytes(file));
  const r = {
    format: 1,
    uuid,
    schema: version,
    revision: (base?.revision ?? 0) + 1,
    parent: base?.hash ?? null,
    operation,
    length: data.length,
    hash: await sha(data),
  };
  await checked(root, prefix + ".commit.json", stringify(r));
  return { ...r, data, slot };
}
export async function create(root, build) {
  return navigator.locks.request("armario-digital:init:v1", async () => {
    for await (const _ of root.keys())
      throw Error(
        "La carpeta contiene archivos. Abre el armario existente o elige otra carpeta vacía.",
      );
    const uuid = crypto.randomUUID(),
      release = await writer(uuid);
    if (!release) throw Error("No se pudo bloquear el destino.");
    try {
      const data = await build(root);
      const head = await publish(root, uuid, null, crypto.randomUUID(), data);
      await checked(
        root,
        marker,
        stringify({ format: "armario-digital", version: 1, uuid }),
      );
      return { root, uuid, release, head };
    } catch (e) {
      release();
      throw e;
    }
  });
}
export async function connect(root, editable = true) {
  const file = await optional(root, marker);
  if (!file)
    throw Error(
      (await optional(root, "wardrobe.sqlite"))
        ? "Esta carpeta es de la aplicación Python. Crea un ZIP en Ajustes y usa «Traer una copia»."
        : "Esta carpeta no contiene un armario reconocido.",
    );
  const m = JSON.parse(await file.text());
  if (m.format !== "armario-digital" || m.version !== 1 || !UUID.test(m.uuid))
    throw Error("Formato de carpeta incompatible.");
  const release = editable ? await writer(m.uuid) : null;
  try {
    const { valid, damaged } = await generations(root, m.uuid);
    return { root, uuid: m.uuid, head: valid[0], release, damaged };
  } catch (e) {
    release?.();
    throw e;
  }
}
export async function commit(s, intent, statements, media = []) {
  if (!s.release || intent.uuid !== s.uuid)
    throw Error("El armario está en modo de solo lectura.");
  const m = JSON.parse(await (await read(s.root, marker)).text());
  if (m.uuid !== s.uuid || m.version !== 1 || m.format !== "armario-digital")
    throw Error("La identidad o versión de la carpeta ha cambiado.");
  const { valid } = await generations(s.root, s.uuid),
    base = valid[0];
  if (valid.some((v) => v.operation === intent.operation)) {
    s.head = base;
    return;
  }
  if (intent.revision !== base.revision || s.head.hash !== base.hash)
    throw Error(
      "La revisión ha cambiado. Abre de nuevo la carpeta y revisa la operación.",
    );
  const data = await call("write", base.data, { statements });
  for (const [name, buffer] of media) {
    if (await optional(s.root, "images/" + name))
      throw Error("La foto ya existe.");
    await checked(s.root, "images/" + name, buffer);
  }
  s.head = await publish(s.root, s.uuid, base, intent.operation, data);
}
