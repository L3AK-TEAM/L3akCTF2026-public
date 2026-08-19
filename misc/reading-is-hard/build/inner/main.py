#!/usr/local/bin/python3
import sys
src = bytes.fromhex(sys.stdin.readline().strip())
problem = sys.stdin.readline().strip()
ns = {}
try:
    exec(compile(src, "solve.py", "exec"), ns)
    ans = ns["solve"](problem)
except Exception:
    ans = "ERR"
print("RESULT:" + str(ans))
