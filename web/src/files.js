import { sha } from "./engine";
export async function access(root, path, create = false) {
  const parts = path.split("/");
  let directory = root;
  for (const part of parts.slice(0, -1))
    directory = await directory.getDirectoryHandle(part, { create });
  return directory.getFileHandle(parts.at(-1), { create });
}
export async function read(root, path) {
  return (await access(root, path)).getFile();
}
export async function optional(root, path) {
  try {
    return await read(root, path);
  } catch (e) {
    if (e.name === "NotFoundError") return null;
    throw e;
  }
}
export async function bytes(file) {
  return new Uint8Array(await file.arrayBuffer());
}
export async function write(root, path, data) {
  const handle = await access(root, path, true);
  const stream = await handle.createWritable();
  try {
    await stream.write(data);
    await stream.close();
  } catch (e) {
    await stream.abort().catch(() => {});
    throw e;
  }
  return handle.getFile();
}
export async function checked(root, path, data) {
  const result = await write(root, path, data);
  if ((await sha(await result.arrayBuffer())) !== (await sha(data)))
    throw Error("No se pudo verificar " + path);
  return result;
}
export async function remembered(value) {
  const db = await new Promise((resolve, reject) => {
    const req = indexedDB.open("armario-digital:conexion", 1);
    req.onupgradeneeded = () => req.result.createObjectStore("preferencias");
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  try {
    return await new Promise((resolve, reject) => {
      const tx = db.transaction(
        "preferencias",
        value === undefined ? "readonly" : "readwrite",
      );
      const store = tx.objectStore("preferencias");
      const req =
        value === undefined
          ? store.get("carpeta")
          : value === null
            ? store.delete("carpeta")
            : store.put(value, "carpeta");
      tx.oncomplete = () => resolve(req.result);
      tx.onabort = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
