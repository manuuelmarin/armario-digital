const worker = new Worker(new URL("./worker.ts", import.meta.url), {
  type: "module",
});
const pending = new Map();
worker.onmessage = ({ data: { id, result, error } }) => {
  const job = pending.get(id);
  pending.delete(id);
  if (error) job.reject(Error(error));
  else job.resolve(result);
};
worker.onerror = (event) => {
  for (const job of pending.values()) job.reject(Error(event.message));
  pending.clear();
};
export function call(kind, bytes, options = {}) {
  return new Promise((resolve, reject) => {
    const id = crypto.randomUUID();
    pending.set(id, { resolve, reject });
    worker.postMessage({ id, kind, bytes, ...options });
  });
}
export async function sha(bytes) {
  return [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))]
    .map((x) => x.toString(16).padStart(2, "0"))
    .join("");
}
