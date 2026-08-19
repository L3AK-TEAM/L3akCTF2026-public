#!/usr/bin/env python3
import os
import sys
import time


def do_build(workdir, ttl):
    log = os.path.join(workdir, "build.log")
    with open(log, "w") as f:
        f.write("[buildfarm] agent online\n")
        f.write("[buildfarm] restoring toolchain cache ... ok\n")
        f.write("[buildfarm] resolving dependencies ... ok\n")
        f.write("[buildfarm] compiling sources ... ok\n")
        f.write("[buildfarm] running tests ... 42 passed\n")
        f.write("[buildfarm] build succeeded\n")
    deadline = time.time() + ttl
    while time.time() < deadline:
        time.sleep(0.2)


def main():
    if len(sys.argv) < 3:
        return
    mode = sys.argv[1]
    workdir = sys.argv[2]
    if mode == "build":
        do_build(workdir, float(sys.argv[3]))


if __name__ == "__main__":
    main()
