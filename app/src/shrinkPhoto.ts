// Shrinks a photo on the phone before it's uploaded. A phone photo is often 3–5 MB; this makes
// it a few hundred KB, which matters on prepaid data and keeps it under the server's 3 MB limit.
// Redrawing it also drops the file's metadata (GPS included), though the server strips that too.

/** The longest side after shrinking, in pixels: plenty for a provider to see the problem. */
const MAX_SIDE_PX = 1280;
const JPEG_QUALITY = 0.7;
const JPEG_TYPE = "image/jpeg";

/** Turns the drawn canvas into a JPEG file. Fails if the browser can't encode it. */
function readCanvasAsJpeg(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (jpeg) => (jpeg ? resolve(jpeg) : reject(new Error("The photo couldn't be shrunk"))),
      JPEG_TYPE,
      JPEG_QUALITY,
    );
  });
}

/**
 * Returns the photo as a JPEG, at most MAX_SIDE_PX on its longest side, upright even if the
 * camera saved it sideways. A photo already small enough keeps its size but is still re-encoded.
 */
export async function shrinkPhoto(photo: Blob): Promise<Blob> {
  const bitmap = await createImageBitmap(photo, { imageOrientation: "from-image" });
  const scale = Math.min(1, MAX_SIDE_PX / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  return readCanvasAsJpeg(canvas);
}
