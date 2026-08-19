const WORKER_COMPATIBILITY_DATE = "2026-07-13";
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const knownWorkers = new Set();

function json(value, status) {
  return Response.json(value, { status, headers: { "cache-control": "no-store" } });
}

function storageUrl(id) {
  return `http://worker-storage/${id}.js`;
}

async function workerExists(id, env) {
  if (knownWorkers.has(id)) return true;
  const response = await env.WORKER_STORAGE.fetch(storageUrl(id), { method: "HEAD" });
  if (!response.ok) return false;
  knownWorkers.add(id);
  return true;
}

async function serveWorker(request, url, id, env) {
  if (!await workerExists(id, env)) return json({ error: "Worker not found." }, 404);

  const worker = env.WORKER_LOADER.get(id, async () => {
    const response = await env.WORKER_STORAGE.fetch(storageUrl(id));
    if (!response.ok) throw new Error(`Stored worker ${id} disappeared.`);
    return {
      compatibilityDate: WORKER_COMPATIBILITY_DATE,
      mainModule: "post.js",
      modules: {
        "post.js": await response.text(),
      },
    };
  });

  const prefix = `/serve/${id}`;
  url.pathname = url.pathname.slice(prefix.length) || "/";
  return worker.getEntrypoint().fetch(new Request(url, request));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/__healthz") {
      return new Response("ok\n");
    }
    const parts = url.pathname.split("/");
    if (parts[1] === "serve" && UUID_PATTERN.test(parts[2] || "")) {
      return serveWorker(request, url, parts[2], env);
    }
    return json({ error: "Not found." }, 404);
  },
};
