const fs = require("fs");
const http = require("http");
const path = require("path");
const { rgbaToPng } = require("./src/png.cjs");
const Fractal = require("./src/fractal.cjs");

const ROOT = __dirname;
const PUBLIC_ROOT = path.join(ROOT, "public");
const DEFAULT_PORT = Number(process.env.PORT || 8767);
const MAX_INPUT_BYTES = Number(process.env.MAX_INPUT_BYTES || 200);
const FLAG = process.env.FLAG || fs.readFileSync(path.join(ROOT, "flag.txt"), "utf8").trim();

const CONFIG = Fractal.mergeConfig({
  blockSize: 16,
  coefficientsPerBlock: 8,
  polynomialDegree: 8,
  imageSize: Number(process.env.IMAGE_SIZE || 240)
});

const STATIC_FILES = new Map([
  ["/", "index.html"],
  ["/index.html", "index.html"],
  ["/styles.css", "styles.css"],
  ["/app.js", "app.js"]
]);

const MIME_TYPES = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8"
};

function utf8Bytes(message) {
  return Buffer.from(message, "utf8");
}

function pkcs7Pad(buffer, blockSize) {
  const remainder = buffer.length % blockSize;
  const paddingLength = remainder === 0 ? blockSize : blockSize - remainder;
  const padding = Buffer.alloc(paddingLength, paddingLength);
  return Buffer.concat([buffer, padding]);
}

function splitBlocks(buffer, blockSize) {
  const blocks = [];
  for (let offset = 0; offset < buffer.length; offset += blockSize) {
    blocks.push(buffer.subarray(offset, offset + blockSize));
  }
  return blocks;
}

function makeServerPlaintext(message) {
  const userBytes = utf8Bytes(message);

  if (userBytes.length > MAX_INPUT_BYTES) {
    const error = new Error(`Input is too long; max ${MAX_INPUT_BYTES} UTF-8 bytes`);
    error.statusCode = 413;
    throw error;
  }

  const flagBytes = utf8Bytes(FLAG);
  return pkcs7Pad(Buffer.concat([userBytes, flagBytes]), CONFIG.blockSize);
}

function renderBlock(block) {
  const coefficients = Fractal.blockToCoefficients(block, CONFIG);
  const rgba = Fractal.renderImageData(coefficients, CONFIG);
  return rgbaToPng(CONFIG.imageSize, CONFIG.imageSize, rgba);
}

function serviceConfig() {
  return {
    blockSize: CONFIG.blockSize,
    coefficientsPerBlock: CONFIG.coefficientsPerBlock,
    polynomialDegree: CONFIG.polynomialDegree,
    imageSize: CONFIG.imageSize,
    viewport: CONFIG.viewport,
    maxIterations: CONFIG.maxIterations,
    tolerance: CONFIG.tolerance,
    maxInputBytes: MAX_INPUT_BYTES
  };
}

function sendJson(response, statusCode, body) {
  const payload = Buffer.from(JSON.stringify(body));
  response.writeHead(statusCode, {
    "cache-control": "no-store",
    "content-length": payload.length,
    "content-type": "application/json; charset=utf-8"
  });
  response.end(payload);
}

function sendError(response, statusCode, message) {
  sendJson(response, statusCode, { error: message });
}

function collectBody(request, limit) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let size = 0;

    request.on("data", (chunk) => {
      size += chunk.length;
      if (size > limit) {
        reject(new Error("Request body is too large"));
        request.destroy();
        return;
      }
      chunks.push(chunk);
    });

    request.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
    request.on("error", reject);
  });
}

async function handleRender(request, response) {
  let payload;

  try {
    payload = JSON.parse(await collectBody(request, 8192));
  } catch (error) {
    sendError(response, 400, "Invalid JSON request");
    return;
  }

  const message = typeof payload.message === "string" ? payload.message : "";
  const focusBlock = Number.isInteger(payload.blockIndex) ? payload.blockIndex : null;

  try {
    const padded = makeServerPlaintext(message);
    const blocks = splitBlocks(padded, CONFIG.blockSize);

    if (focusBlock !== null && (focusBlock < 0 || focusBlock >= blocks.length)) {
      sendError(response, 400, "Requested block index is outside the rendered message");
      return;
    }

    const selected = focusBlock === null
      ? blocks.map((block, index) => ({ block, index }))
      : [{ block: blocks[focusBlock], index: focusBlock }];

    const renderedBlocks = selected.map(function renderSelected(item) {
      const png = renderBlock(item.block);
      return {
        index: item.index,
        width: CONFIG.imageSize,
        height: CONFIG.imageSize,
        image: `data:image/png;base64,${png.toString("base64")}`
      };
    });

    sendJson(response, 200, {
      inputBytes: utf8Bytes(message).length,
      blockCount: blocks.length,
      blockSize: CONFIG.blockSize,
      blocks: renderedBlocks
    });
  } catch (error) {
    sendError(response, error.statusCode || 500, error.message || "Render failed");
  }
}

function handleStatic(request, response) {
  const url = new URL(request.url, "http://localhost");
  const relativePath = STATIC_FILES.get(url.pathname);

  if (!relativePath) {
    sendError(response, 404, "Not found");
    return;
  }

  const filePath = path.join(PUBLIC_ROOT, relativePath);
  fs.readFile(filePath, (error, body) => {
    if (error) {
      sendError(response, 404, "Not found");
      return;
    }

    response.writeHead(200, {
      "cache-control": "no-store",
      "content-length": body.length,
      "content-type": MIME_TYPES[path.extname(filePath)] || "application/octet-stream"
    });
    response.end(body);
  });
}

function createServer() {
  return http.createServer(async (request, response) => {
    const url = new URL(request.url, "http://localhost");

    if (request.method === "GET" && url.pathname === "/api/challenge") {
      sendJson(response, 200, {
        title: "Isaac's Kaleidoscope",
        publicConfig: serviceConfig()
      });
      return;
    }

    if (request.method === "POST" && url.pathname === "/api/render") {
      await handleRender(request, response);
      return;
    }

    if (request.method === "GET" || request.method === "HEAD") {
      handleStatic(request, response);
      return;
    }

    sendError(response, 405, "Method not allowed");
  });
}

if (require.main === module) {
  const server = createServer();
  server.listen(DEFAULT_PORT, "127.0.0.1", () => {
    console.log(`Fractal block server listening on http://127.0.0.1:${DEFAULT_PORT}/`);
  });
}

module.exports = {
  CONFIG,
  createServer,
  makeServerPlaintext,
  pkcs7Pad,
  renderBlock,
  splitBlocks
};
