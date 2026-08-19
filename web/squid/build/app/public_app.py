#!/usr/bin/env python3
import json
import os
import time
import urllib.parse

import requests
import ujson
from flask import (Flask, Response, jsonify, redirect, render_template,
                   request, send_file, session, url_for)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

WORK = "/work"
ORCHESTRATOR = "http://127.0.0.1:8000"

TRUSTED_MIRRORS = {
    "manifests.buildfarm.internal",
    "cdn.buildfarm.internal",
    "registry.buildfarm.internal",
}

USERS = {}

ORG = {"name": "Acme Corp", "plan": "Enterprise", "agents": 8, "region": "eu-west-1"}

PROJECTS = [
    {"id": "web-frontend", "name": "web-frontend", "language": "TypeScript",
     "branch": "main", "visibility": "private", "repo": "git@buildfarm:acme/web-frontend.git",
     "health": "passing"},
    {"id": "api-gateway", "name": "api-gateway", "language": "Go",
     "branch": "main", "visibility": "private", "repo": "git@buildfarm:acme/api-gateway.git",
     "health": "passing"},
    {"id": "payments", "name": "payments-service", "language": "Java",
     "branch": "release/3.4", "visibility": "private", "repo": "git@buildfarm:acme/payments.git",
     "health": "failing"},
    {"id": "ml-pipeline", "name": "ml-pipeline", "language": "Python",
     "branch": "main", "visibility": "private", "repo": "git@buildfarm:acme/ml-pipeline.git",
     "health": "passing"},
    {"id": "infra", "name": "infra-terraform", "language": "HCL",
     "branch": "main", "visibility": "internal", "repo": "git@buildfarm:acme/infra.git",
     "health": "queued"},
]

RUNS = [
    {"id": "5120", "project": "web-frontend", "status": "success", "branch": "main",
     "commit": "a1b2c3d", "msg": "fix: hydration mismatch on profile cards",
     "author": "maya", "duration": "2m13s", "when": "just now", "trigger": "push"},
    {"id": "5119", "project": "api-gateway", "status": "running", "branch": "main",
     "commit": "9f8e7d6", "msg": "feat: connection pool warmup", "author": "deepak",
     "duration": "1m02s", "when": "1 min ago", "trigger": "push"},
    {"id": "5118", "project": "payments", "status": "failed", "branch": "release/3.4",
     "commit": "44ce19a", "msg": "chore: bump jackson to 2.17", "author": "lena",
     "duration": "4m51s", "when": "6 min ago", "trigger": "merge"},
    {"id": "5117", "project": "ml-pipeline", "status": "success", "branch": "main",
     "commit": "7b22f01", "msg": "perf: vectorise feature extraction", "author": "sam",
     "duration": "11m07s", "when": "22 min ago", "trigger": "schedule"},
    {"id": "5116", "project": "web-frontend", "status": "success", "branch": "main",
     "commit": "1d0a9c4", "msg": "build: split vendor chunk", "author": "maya",
     "duration": "2m02s", "when": "38 min ago", "trigger": "push"},
    {"id": "5115", "project": "infra", "status": "queued", "branch": "main",
     "commit": "e5f6a7b", "msg": "feat: add eu-west-1 read replica", "author": "deepak",
     "duration": "—", "when": "41 min ago", "trigger": "manual"},
]

ARTIFACTS = [
    {"name": "dist.tar.gz", "project": "web-frontend", "run": "5120", "size": "4.2 MB",
     "path": "web-frontend/5120/dist.tar.gz"},
    {"name": "coverage.xml", "project": "ml-pipeline", "run": "5117", "size": "318 KB",
     "path": "ml-pipeline/5117/coverage.xml"},
    {"name": "gateway-linux-amd64", "project": "api-gateway", "run": "5119", "size": "22 MB",
     "path": "api-gateway/5119/gateway-linux-amd64"},
    {"name": "build.log", "project": "payments", "run": "5118", "size": "61 KB",
     "path": "payments/5118/build.log"},
]

ORG_SECRETS = [
    {"name": "DOCKER_REGISTRY_TOKEN", "scope": "all pipelines", "updated": "2d ago"},
    {"name": "NPM_TOKEN", "scope": "web-frontend", "updated": "9d ago"},
    {"name": "AWS_ACCESS_KEY_ID", "scope": "infra", "updated": "1mo ago"},
    {"name": "SENTRY_DSN", "scope": "all pipelines", "updated": "3w ago"},
]


def current_user():
    if "username" not in session:
        return None
    return {"username": session.get("username"), "role": session.get("role", "user")}


def is_staff():
    return session.get("role") == "admin"


def view(template, **ctx):
    ctx.setdefault("user", current_user())
    ctx.setdefault("org", ORG)
    return render_template(template, **ctx)


def status_counts():
    c = {"success": 0, "running": 0, "failed": 0, "queued": 0}
    for r in RUNS:
        c[r["status"]] = c.get(r["status"], 0) + 1
    return c


@app.get("/")
def index():
    if current_user():
        return redirect(url_for("dashboard"))
    return view("landing.html")


@app.get("/login")
def login_page():
    if current_user():
        return redirect(url_for("dashboard"))
    return view("login.html")


@app.get("/register")
def register_page():
    if current_user():
        return redirect(url_for("dashboard"))
    return view("register.html")


@app.get("/dashboard")
def dashboard():
    if not current_user():
        return redirect(url_for("login_page"))
    return view("dashboard.html", active="dashboard", projects=PROJECTS,
                runs=RUNS, counts=status_counts())


@app.get("/projects")
def projects_page():
    if not current_user():
        return redirect(url_for("login_page"))
    return view("projects.html", active="projects", projects=PROJECTS)


@app.get("/projects/<pid>")
def project_detail(pid):
    if not current_user():
        return redirect(url_for("login_page"))
    project = next((p for p in PROJECTS if p["id"] == pid), None)
    if not project:
        return view("notfound.html", what="project"), 404
    runs = [r for r in RUNS if r["project"] == pid]
    return view("project_detail.html", active="projects", project=project, runs=runs)


@app.get("/runs/<rid>")
def run_detail(rid):
    if not current_user():
        return redirect(url_for("login_page"))
    run = next((r for r in RUNS if r["id"] == rid), None)
    if not run:
        return view("notfound.html", what="run"), 404
    return view("run_detail.html", active="dashboard", run=run)


@app.get("/artifacts")
def artifacts_page():
    if not current_user():
        return redirect(url_for("login_page"))
    return view("artifacts.html", active="artifacts", artifacts=ARTIFACTS, staff=is_staff())


@app.get("/settings")
def settings_page():
    if not current_user():
        return redirect(url_for("login_page"))
    return view("settings.html", active="settings", secrets=ORG_SECRETS)


@app.get("/import")
def import_page():
    if not current_user():
        return redirect(url_for("login_page"))
    return view("import.html", active="import", mirrors=sorted(TRUSTED_MIRRORS),
                staff=is_staff())


@app.post("/api/register")
def api_register():
    raw = request.get_data()
    try:
        payload = json.loads(raw)
    except Exception:
        return jsonify({"error": "request body must be json"}), 400
    if not isinstance(payload, dict) or not payload.get("username"):
        return jsonify({"error": "username is required"}), 400

    if payload.get("role", "user") == "admin":
        return jsonify({"error": "self-service accounts cannot request the admin role"}), 403

    record = ujson.loads(raw)
    username = str(record.get("username"))[:64]
    role = record.get("role", "user")
    USERS[username] = {"role": role, "password": record.get("password")}
    session["username"] = username
    session["role"] = role
    return jsonify({"ok": True, "username": username, "role": role})


@app.post("/api/login")
def api_login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", ""))[:64]
    password = payload.get("password")
    record = USERS.get(username)
    if not record or record.get("password") != password:
        return jsonify({"error": "invalid credentials"}), 401
    session["username"] = username
    session["role"] = record.get("role", "user")
    return jsonify({"ok": True, "username": username, "role": session["role"]})


@app.post("/api/logout")
def api_logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/me")
def api_me():
    return jsonify({"username": session.get("username"), "role": session.get("role")})


@app.get("/api/projects")
def api_projects():
    if not current_user():
        return jsonify({"error": "authentication required"}), 401
    return Response(ujson.dumps({"projects": PROJECTS}), content_type="application/json")


@app.post("/api/projects")
def api_create_project():
    if not current_user():
        return jsonify({"error": "authentication required"}), 401
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()[:48]
    if not name:
        return jsonify({"error": "name is required"}), 400
    pid = "".join(ch if ch.isalnum() else "-" for ch in name.lower())[:48]
    project = {"id": pid, "name": name, "language": body.get("language", "Other"),
               "branch": "main", "visibility": "private",
               "repo": "git@buildfarm:acme/%s.git" % pid, "health": "queued"}
    PROJECTS.append(project)
    return jsonify({"ok": True, "project": project})


@app.get("/api/runs")
def api_runs():
    if not current_user():
        return jsonify({"error": "authentication required"}), 401
    return jsonify({"runs": RUNS})


@app.post("/api/manifest")
def api_manifest():
    if not is_staff():
        return jsonify({"error": "importing manifests is limited to organisation staff"}), 403
    body = request.get_json(silent=True) or {}
    url = body.get("url", "")
    if not isinstance(url, str) or not url:
        return jsonify({"error": "a manifest url is required"}), 400

    mirror = urllib.parse.urlparse(url).hostname
    if mirror not in TRUSTED_MIRRORS:
        return jsonify({"error": "mirror is not on the trusted list",
                        "mirror": mirror}), 403
    try:
        resp = requests.get(url, timeout=5, allow_redirects=False)
    except Exception as exc:
        return jsonify({"error": "could not reach mirror", "detail": str(exc)}), 502
    return Response(resp.content, status=resp.status_code,
                    content_type=resp.headers.get("Content-Type", "application/json"))


@app.get("/download/<path:target>")
def download(target):
    if not is_staff():
        return jsonify({"error": "artifact access is limited to organisation staff"}), 403
    path = os.path.join(WORK, target)
    try:
        return send_file(path)
    except OSError:
        return jsonify({"error": "artifact not found"}), 404


@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "ts": int(time.time())})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
