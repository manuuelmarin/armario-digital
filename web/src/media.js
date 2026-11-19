import { imageSize } from "image-size";
import { sha } from "./engine";
export function imageFormat(data) {
  const tag = (p, n) => String.fromCharCode(...data.subarray(p, p + n));
  if (tag(0, 4) === "RIFF" && tag(8, 4) === "WEBP") return "webp";
  if (data[0] === 255 && data[1] === 216 && data[2] === 255) return "jpeg";
  if (data[0] === 137 && tag(1, 3) === "PNG") return "png";
  throw Error("Formato no admitido. Utiliza JPEG, PNG o WebP.");
}
export async function decoded(buffer, expected) {
  const format = imageFormat(buffer);
  if (expected && format !== expected)
    throw Error("Se esperaba una imagen WebP.");
  const { width, height } = imageSize(buffer);
  if (!width || !height || width * height > 24000000)
    throw Error("La imagen supera el límite de 24 millones de píxeles.");
  return createImageBitmap(new Blob([buffer]), {
    imageOrientation: "from-image",
  });
}
export async function preparePhoto(file) {
  if (file.size > 10 * 1024 ** 2) throw Error("La foto supera los 10 MiB.");
  const input = new Uint8Array(await file.arrayBuffer()),
    image = await decoded(input);
  const token = crypto.randomUUID().replaceAll("-", ""),
    files = [],
    integrity = [];
  const meta = { digest: await sha(input) };
  try {
    for (const [column, suffix, limit] of [
      ["filename", "", 4096],
      ["preview", "-preview", 1024],
      ["thumbnail", "-thumb", 512],
    ]) {
      const scale = Math.min(1, limit / Math.max(image.width, image.height)),
        w = Math.max(1, Math.round(image.width * scale)),
        h = Math.max(1, Math.round(image.height * scale));
      const canvas = new OffscreenCanvas(w, h);
      canvas.getContext("2d").drawImage(image, 0, 0, w, h);
      const data = new Uint8Array(
        await (
          await canvas.convertToBlob({ type: "image/webp", quality: 0.86 })
        ).arrayBuffer(),
      );
      if (imageFormat(data) !== "webp")
        throw Error("Este navegador no puede crear archivos WebP.");
      const name = token + suffix + ".webp";
      meta[column] = name;
      if (column === "filename") {
        meta.width = w;
        meta.height = h;
      } else meta[column + "_width"] = w;
      files.push([name, data]);
      integrity.push([
        "INSERT INTO image_integrity(name,sha256) VALUES (?,?)",
        [name, await sha(data)],
      ]);
    }
    return { meta, files, integrity };
  } finally {
    image.close();
  }
}
