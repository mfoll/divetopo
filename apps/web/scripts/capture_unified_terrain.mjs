import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

const require = createRequire(import.meta.url);
const WebSocket = require("ws");
const chromeExecutable =
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const [slug, style, outputPath, widthText = "2474", heightText = "1712"] =
  process.argv.slice(2);
const outputWidth = Number(widthText);
const outputHeight = Number(heightText);

if (
  !slug ||
  !["orthophoto", "topographic"].includes(style) ||
  !outputPath ||
  !Number.isFinite(outputWidth) ||
  !Number.isFinite(outputHeight)
) {
  throw new Error(
    "Usage: capture_unified_terrain.mjs <slug> <orthophoto|topographic> <output.png> [width] [height]",
  );
}

const scale = 2;
const viewportWidth = Math.ceil(outputWidth / scale);
const viewportHeight = Math.ceil(outputHeight / scale);
const profileDirectory = await mkdtemp(path.join(tmpdir(), "divetopo-chrome-"));
const chrome = spawn(
  chromeExecutable,
  [
    "--headless=new",
    "--remote-debugging-port=0",
    `--user-data-dir=${profileDirectory}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--hide-scrollbars",
    "--enable-webgl",
    "--enable-unsafe-swiftshader",
    "--use-angle=swiftshader",
    `--force-device-scale-factor=${scale}`,
    `--window-size=${viewportWidth},${viewportHeight}`,
    "about:blank",
  ],
  { stdio: ["ignore", "ignore", "pipe"] },
);

let diagnostics = "";
chrome.stderr.on("data", (chunk) => {
  diagnostics += String(chunk);
});

async function waitForPort() {
  const activePortFile = path.join(profileDirectory, "DevToolsActivePort");
  for (let attempt = 0; attempt < 120; attempt += 1) {
    try {
      const [port] = (await readFile(activePortFile, "utf8")).trim().split("\n");
      if (port) return Number(port);
    } catch {
      // Chrome is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`Chrome did not expose DevTools.\n${diagnostics}`);
}

function connect(url) {
  const socket = new WebSocket(url);
  const ready = new Promise((resolve, reject) => {
    socket.once("open", resolve);
    socket.once("error", reject);
  });
  const pending = new Map();
  let id = 0;
  socket.on("message", (message) => {
    const payload = JSON.parse(String(message));
    const request = pending.get(payload.id);
    if (!request) return;
    pending.delete(payload.id);
    payload.error
      ? request.reject(new Error(payload.error.message))
      : request.resolve(payload.result);
  });
  return {
    async send(method, params = {}) {
      await ready;
      const requestId = ++id;
      return new Promise((resolve, reject) => {
        pending.set(requestId, { resolve, reject });
        socket.send(JSON.stringify({ id: requestId, method, params }));
      });
    },
    close() {
      socket.close();
    },
  };
}

async function evaluate(cdp, expression, awaitPromise = false) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(
      result.exceptionDetails.exception?.description ??
        result.exceptionDetails.text,
    );
  }
  return result.result.value;
}

async function waitFor(cdp, expression, timeoutMs = 45_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await evaluate(cdp, expression)) return;
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  throw new Error(`Timed out waiting for ${expression}`);
}

let cdp;
try {
  const port = await waitForPort();
  const pageResponse = await fetch(
    `http://127.0.0.1:${port}/json/new?about:blank`,
    { method: "PUT" },
  );
  const page = await pageResponse.json();
  cdp = connect(page.webSocketDebuggerUrl);
  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: viewportWidth,
    height: viewportHeight,
    deviceScaleFactor: scale,
    mobile: false,
    screenWidth: viewportWidth,
    screenHeight: viewportHeight,
  });
  await cdp.send("Page.navigate", {
    url: `http://127.0.0.1:3130/reunion/fr/sites/${slug}`,
  });
  await waitFor(
    cdp,
    "document.readyState === 'complete' && Boolean(document.querySelector('.unified-3d-layer.is-rendered canvas'))",
  );
  if (style === "topographic") {
    await evaluate(
      cdp,
      `(() => {
        const button = [...document.querySelectorAll(".surface-control button")]
          .find((candidate) => candidate.textContent.trim() === "Topographie");
        if (!button) throw new Error("Topographic control unavailable");
        button.click();
        return true;
      })()`,
    );
    await new Promise((resolve) => setTimeout(resolve, 700));
  }
  await evaluate(
    cdp,
    `(async () => {
      const viewer = document.querySelector('[data-testid="topo-reunion-viewer"]');
      if (!viewer) throw new Error("Terrain viewer unavailable");
      const styles = document.createElement("style");
      styles.textContent = \`
        html, body { background:#06202a!important; height:${viewportHeight}px!important;
          margin:0!important; overflow:hidden!important; padding:0!important;
          width:${viewportWidth}px!important; }
        .viewer-frame { border-radius:0!important; box-shadow:none!important;
          height:${viewportHeight}px!important; width:${viewportWidth}px!important; }
        .map-open, .terrain-actions { display:none!important; }
      \`;
      document.head.appendChild(styles);
      document.body.replaceChildren(viewer);
      await new Promise((resolve) => requestAnimationFrame(() =>
        requestAnimationFrame(() => setTimeout(resolve, 900))));
      return true;
    })()`,
    true,
  );
  const capture = await cdp.send("Page.captureScreenshot", {
    format: "png",
    fromSurface: true,
    captureBeyondViewport: false,
    clip: {
      x: 0,
      y: 0,
      width: viewportWidth,
      height: viewportHeight,
      scale: 1,
    },
  });
  await writeFile(outputPath, Buffer.from(capture.data, "base64"));
} finally {
  cdp?.close();
  chrome.kill("SIGTERM");
  await rm(profileDirectory, { recursive: true, force: true }).catch(() => {
    // Chrome can briefly keep its profile directory busy after a valid capture.
  });
}
