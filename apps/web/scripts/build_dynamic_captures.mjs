import { createRequire } from "node:module";
import { mkdir } from "node:fs/promises";
import path from "node:path";

const require = createRequire(import.meta.url);
const sharp = require("sharp");
const [slug, sourceDirectory, outputDirectory] = process.argv.slice(2);

if (!slug || !sourceDirectory || !outputDirectory) {
  throw new Error(
    "Usage: build_dynamic_captures.mjs <slug> <source-directory> <output-directory>",
  );
}

await mkdir(path.join(outputDirectory, "downloads"), { recursive: true });
for (const style of ["orthophoto", "topographic"]) {
  const source = path.join(sourceDirectory, `${slug}-${style}-2474.png`);
  const mobileSource = path.join(sourceDirectory, `${slug}-${style}-mobile.png`);
  for (const [width, height] of [
    [960, 664],
    [1600, 1107],
    [2474, 1712],
  ]) {
    await sharp(source)
      .resize(width, height, { fit: "fill", kernel: sharp.kernel.lanczos3 })
      .webp({ quality: 88, effort: 6, smartSubsample: true })
      .toFile(path.join(outputDirectory, `3d-dynamic-${style}-${width}.webp`));
  }
  await sharp(source)
    .jpeg({ quality: 95, chromaSubsampling: "4:4:4", mozjpeg: true })
    .toFile(
      path.join(outputDirectory, "downloads", `3d-dynamic-${style}-full.jpg`),
    );
  await sharp(mobileSource)
    .resize(960, 662, { fit: "fill", kernel: sharp.kernel.lanczos3 })
    .webp({ quality: 88, effort: 6, smartSubsample: true })
    .toFile(
      path.join(outputDirectory, `3d-dynamic-${style}-mobile-960.webp`),
    );
}
