#!/usr/bin/env python3
import grp
import json
import os
import pwd
import string
import subprocess
import sys
import time
import uuid

from flask import Flask, request, jsonify

VAULT_FILE = "/secrets/flag"
WORK = "/work"
RUNNER = "/app/runner.py"
AGENT_USER = "ctf"
MAX_JOBS = 8

RESERVED_ENV = {
    "PATH", "HOME", "BROWSER", "BASH_ENV", "ENV", "IFS",
}


def load_vault():
    with open(VAULT_FILE, "r") as f:
        return {"FLAG": f.read().strip()}


VAULT = load_vault()
AGENT_UID = pwd.getpwnam(AGENT_USER).pw_uid
AGENT_GID = grp.getgrnam(AGENT_USER).gr_gid

app = Flask(__name__)
JOBS = {}


def _unsafe_env_name(key):
    return (
        key in RESERVED_ENV
        or key.startswith("PYTHON")
        or key.startswith("LD_")
    )


def materialise_env(env):
    resolved = {}
    for key, val in env.items():
        if not isinstance(key, str):
            continue
        if _unsafe_env_name(key):
            continue
        if isinstance(val, str):
            resolved[key] = string.Template(val).safe_substitute(VAULT)
        else:
            resolved[key] = str(val)
    return resolved


def reap():
    done = [j for j, m in JOBS.items() if m["proc"].poll() is not None]
    for j in done:
        JOBS.pop(j, None)


def clamp_ttl(value):
    try:
        return max(5.0, min(float(value), 90.0))
    except (TypeError, ValueError):
        return 60.0


def spawn(argv, env, cwd):
    return subprocess.Popen(
        argv,
        env=env,
        user=AGENT_UID,
        group=AGENT_GID,
        cwd=cwd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def new_workdir():
    jobid = uuid.uuid4().hex
    workdir = os.path.join(WORK, jobid)
    os.makedirs(workdir, exist_ok=True)
    os.chown(workdir, AGENT_UID, AGENT_GID)
    return jobid, workdir


@app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def schedule(path):
    raw = request.args.get("spec") or request.form.get("spec")
    if not raw and request.data:
        raw = request.data.decode("utf-8", "replace")
    if not raw:
        return jsonify({"service": "buildfarm-orchestrator", "agents": 1, "ok": True}), 200

    try:
        manifest = json.loads(raw)
    except Exception as exc:
        return jsonify({"error": "manifest is not valid json", "detail": str(exc)}), 400
    if not isinstance(manifest, dict):
        return jsonify({"error": "manifest must be an object"}), 400

    reap()
    if len(JOBS) >= MAX_JOBS:
        return jsonify({"error": "all agents busy, retry shortly"}), 429

    task = manifest.get("task", "build")
    ttl = clamp_ttl(manifest.get("ttl", 60))
    jobid, workdir = new_workdir()

    if task == "build":
        env = manifest.get("env") or {}
        if not isinstance(env, dict):
            return jsonify({"error": "env must be an object"}), 400
        child_env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/tmp",
            "CI": "true",
            "JOB_ID": jobid,
        }
        child_env.update(materialise_env(env))
        proc = spawn([sys.executable, "-I", RUNNER, "build", workdir, str(ttl)], child_env, workdir)
        JOBS[jobid] = {"proc": proc, "workdir": workdir, "task": task, "started": time.time()}
        return jsonify({
            "job": jobid,
            "status": "running",
            "log": "/download/%s/build.log" % jobid,
            "ttl": ttl,
        }), 200

    return jsonify({"error": "unknown task %r" % task}), 400


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000, threaded=True)
