using Workerd = import "/workerd/workerd.capnp";

const config :Workerd.Config = (
  services = [
    (name = "dispatcher", worker = .dispatcher),
    (name = "worker-storage", disk = (
      path = "/data/workers",
      writable = false,
    )),
  ],
  sockets = [
    (name = "http", address = "127.0.0.1:8081", http = (), service = "dispatcher"),
  ],
);

const dispatcher :Workerd.Worker = (
  modules = [(name = "runtime.js", esModule = embed "runtime.js")],
  compatibilityDate = "2026-07-13",
  compatibilityFlags = ["experimental"],
  bindings = [
    (name = "WORKER_LOADER", workerLoader = (id = "uploaded-workers")),
    (name = "WORKER_STORAGE", service = "worker-storage"),
  ],
);
