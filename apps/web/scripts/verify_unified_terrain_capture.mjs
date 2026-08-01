import { createRequire } from "node:module";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const sharp = require("sharp");

const [slug, routePath, expectedDirectory, baseUrl = "http://127.0.0.1:3130"] =
  process.argv.slice(2);
const minimumCorrelation = Number(
  process.env.DIVETOPO_TERRAIN_MIN_CORRELATION ?? "0.985",
);

if (!slug || !routePath || !expectedDirectory) {
  throw new Error(
    "Usage: verify_unified_terrain_capture.mjs <slug> <route-path> <published-map-directory> [base-url]",
  );
}
if (!Number.isFinite(minimumCorrelation)) {
  throw new Error("DIVETOPO_TERRAIN_MIN_CORRELATION must be numeric");
}

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const captureScript = path.join(scriptDirectory, "capture_unified_terrain.mjs");
const expectedRoot = path.resolve(expectedDirectory);
const temporaryRoot = await mkdtemp(path.join(tmpdir(), "divetopo-terrain-"));
const styles = ["orthophoto", "topographic"];

function runCapture(style, outputPath, width, height) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [
        captureScript,
        slug,
        style,
        outputPath,
        String(width),
        String(height),
        baseUrl,
        "",
        routePath,
      ],
      { stdio: "inherit" },
    );
    child.once("error", reject);
    child.once("exit", (code, signal) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(
        new Error(
          `Capture failed for ${slug}/${style} (code=${code}, signal=${signal ?? "none"})`,
        ),
      );
    });
  });
}

async function imageBytes(imagePath, width, height) {
  const metadata = await sharp(imagePath).metadata();
  if (metadata.width !== width || metadata.height !== height) {
    throw new Error(
      `${imagePath} must be ${width}x${height}, found ${metadata.width}x${metadata.height}`,
    );
  }
  const { data } = await sharp(imagePath)
    .resize({ width: 160, height: 111, fit: "fill" })
    .removeAlpha()
    .raw()
    .toBuffer({ resolveWithObject: true });
  return data;
}

async function compareImages(actualPath, expectedPath, width, height) {
  const [actual, expected] = await Promise.all([
    imageBytes(actualPath, width, height),
    imageBytes(expectedPath, width, height),
  ]);
  if (actual.length !== expected.length) {
    throw new Error(`Image buffers have different lengths for ${expectedPath}`);
  }

  let actualMean = 0;
  let expectedMean = 0;
  for (let index = 0; index < actual.length; index += 1) {
    actualMean += actual[index];
    expectedMean += expected[index];
  }
  actualMean /= actual.length;
  expectedMean /= expected.length;

  let covariance = 0;
  let actualVariance = 0;
  let expectedVariance = 0;
  let absoluteError = 0;
  for (let index = 0; index < actual.length; index += 1) {
    const actualDelta = actual[index] - actualMean;
    const expectedDelta = expected[index] - expectedMean;
    covariance += actualDelta * expectedDelta;
    actualVariance += actualDelta * actualDelta;
    expectedVariance += expectedDelta * expectedDelta;
    absoluteError += Math.abs(actual[index] - expected[index]);
  }

  const correlation =
    covariance / Math.sqrt(actualVariance * expectedVariance || 1);
  return {
    correlation,
    meanAbsoluteError: absoluteError / actual.length / 255,
  };
}

try {
  const failures = [];
  for (const style of styles) {
    for (const capture of [
      {
        name: "desktop",
        width: 2474,
        height: 1712,
        expected: [
          path.join(expectedRoot, `3d-dynamic-${style}-2474.webp`),
          path.join(expectedRoot, "downloads", `3d-dynamic-${style}-full.jpg`),
        ],
      },
      {
        name: "mobile",
        width: 960,
        height: 662,
        expected: [
          path.join(expectedRoot, `3d-dynamic-${style}-mobile-960.webp`),
        ],
      },
    ]) {
      const actualPath = path.join(
        temporaryRoot,
        `${style}-${capture.name}.png`,
      );
      await runCapture(style, actualPath, capture.width, capture.height);

      for (const expectedPath of capture.expected) {
        await readFile(expectedPath);
        const result = await compareImages(
          actualPath,
          expectedPath,
          capture.width,
          capture.height,
        );
        const label = path.basename(expectedPath);
        const passed = result.correlation >= minimumCorrelation;
        console.log(
          `${passed ? "PASS" : "FAIL"} ${slug}/${style}/${capture.name} ${label}: ` +
            `correlation=${result.correlation.toFixed(4)} ` +
            `mae=${result.meanAbsoluteError.toFixed(4)}`,
        );
        if (!passed) {
          failures.push(`${slug}/${style}/${capture.name} ${label}`);
        }
      }
    }
  }

  if (failures.length) {
    throw new Error(
      `Initial-view equivalence failed below correlation ${minimumCorrelation}: ${failures.join(", ")}`,
    );
  }
} finally {
  await rm(temporaryRoot, { recursive: true, force: true });
}
