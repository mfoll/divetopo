import { readdir, rm } from "node:fs/promises";
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
await Promise.all(
  downloadDirectories.map((directory) => rm(directory, { recursive: true })),
);
console.log(
  `Removed ${downloadDirectories.length} release-backed download directories from the hosting build.`,
);
