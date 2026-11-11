import { readFile, readdir, rm } from "node:fs/promises";
import path from "node:path";

const mapsRoot = path.resolve("dist/client/maps");

async function findDownloadDirectories(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const directories = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const child = path.join(directory, entry.name);
    if (entry.name === "downloads") {
      directories.push(child);
    } else {
      directories.push(...(await findDownloadDirectories(child)));
    }
  }
  return directories;
}

const downloadDirectories = await findDownloadDirectories(mapsRoot);
const legacyPacaAssets = JSON.parse(
  await readFile(new URL("../content/legacy-paca-assets.json", import.meta.url), "utf8"),
);
await Promise.all(
  downloadDirectories.map((directory) => rm(directory, { recursive: true })),
);
await Promise.all(
  legacyPacaAssets.paths.map((asset) => rm(path.resolve("dist/client", `.${asset}`))),
);
console.log(
  `Removed ${downloadDirectories.length} release-backed download directories and ${legacyPacaAssets.paths.length} archived PACA maps from the hosting build.`,
);
