import os
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from flask import Flask, jsonify, request

app = Flask(__name__)

FLAG_PATH = os.environ.get("FLAG_PATH", "/flag.txt")
MAX_MANIFEST_BYTES = 16 * 1024

POLICIES = {
    "standard": {"translate"},
    "system": {"translate", "import"},
}


def canonicalize_slug(raw_slug):
    return unicodedata.normalize("NFKC", raw_slug).casefold()


def select_policy(raw_slug):
    if canonicalize_slug(raw_slug) == "system":
        return "system"
    return "standard"


def translate(source):
    return "Translation job completed"


def import_bundle(source):
    parsed = urlsplit(source)
    if parsed.scheme != "file":
        raise PermissionError("Invalid scheme")
    if parsed.netloc != "":
        raise PermissionError("Invalid file host")
    if parsed.path != "/flag.txt":
        raise PermissionError("Unknown internal bundle")
    if parsed.query or parsed.fragment:
        raise PermissionError("Invalid internal bundle")
    return Path(FLAG_PATH).read_text(encoding="utf-8").strip()


@app.get("/health")
def health():
    return jsonify(service="worker", status="ok")


@app.post("/run")
def run():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(ok=False, error="Invalid request"), 400

    raw_slug = payload.get("slug")
    raw_manifest = payload.get("manifest")
    if not isinstance(raw_slug, str) or not isinstance(raw_manifest, str):
        return jsonify(ok=False, error="Invalid request"), 400
    if len(raw_manifest.encode("utf-8")) > MAX_MANIFEST_BYTES:
        return jsonify(ok=False, error="Manifest too large"), 413

    allowed_actions = POLICIES[select_policy(raw_slug)]

    try:
        manifest = yaml.safe_load(raw_manifest)
    except yaml.YAMLError:
        return jsonify(ok=False, error="Manifest could not be parsed"), 400

    if not isinstance(manifest, dict) or not isinstance(manifest.get("job"), dict):
        return jsonify(ok=False, error="Manifest must contain a job"), 400

    job = manifest["job"]
    action = job.get("action")
    source = job.get("source")
    if not isinstance(action, str) or not isinstance(source, str):
        return jsonify(ok=False, error="Invalid job"), 400

    if action not in allowed_actions:
        return jsonify(ok=False, error="Action not allowed"), 403

    try:
        if action == "translate":
            artifact = translate(source)
        elif action == "import":
            artifact = import_bundle(source)
        else:
            return jsonify(ok=False, error="Unsupported action"), 400
    except PermissionError as exc:
        return jsonify(ok=False, error=str(exc)), 403
    except OSError:
        return jsonify(ok=False, error="Bundle unavailable"), 500

    return jsonify(ok=True, artifact=artifact)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
