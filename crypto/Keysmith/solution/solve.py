import os
import re
import subprocess
import time
from pathlib import Path
from pwn import remote
from lock import lock

def build_helper():
    source = "attack192_fast.c"
    binary = "attack192_fast"
    commands = [
        ["gcc", "-std=c99", "-O3", "-march=native", "-funroll-loops", str(source), "-o", str(binary)],
        ["gcc", "-std=c99", "-O3", str(source), "-o", str(binary)]
    ]
    for command in commands:
        try:
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return binary
        except:
            print('idk something went wrong')
            exit()
    print('something else went wrong xd')
    return

def read_result(output):
    values = {}
    for line in output.splitlines():
        if "=" in line:
            name, value = line.strip().split("=", 1)
            values[name] = value
    if not all(name in values for name in ("key1", "key2", "digest")):
        raise RuntimeError(f"unexpected helper output:\n{output}")
    checked = int(values["candidates"]) if "candidates" in values else None
    return (bytes.fromhex(values["key1"]), bytes.fromhex(values["key2"]), bytes.fromhex(values["digest"]), checked)

def find_collision(plaintext, binary):
    workers = max(1, min(8, os.cpu_count() or 1))
    step = 0x9E3779B97F4A7C15
    first_seed = int.from_bytes(os.urandom(8), "big") or 1
    processes = []
    print(f"Solving {plaintext.hex()} with {workers} workers")

    def start(seed):
        process = subprocess.Popen([str(binary), plaintext.hex(), "200000000", str(seed)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append((process, seed))

    def stop_workers():
        for process, _ in processes:
            if process.poll() is None:
                process.kill()
        for process, _ in processes:
            process.communicate()

    try:
        for i in range(workers):
            seed = (first_seed + i * step) & ((1 << 64) - 1)
            start(seed or i + 1)
        while True:
            for process, seed in processes.copy():
                if process.poll() is None:
                    continue
                stdout, _ = process.communicate()
                processes.remove((process, seed))
                if process.returncode == 0:
                    key1, key2, digest, checked = read_result(stdout)
                    if checked is not None:
                        print(f"Winning worker checked {checked} candidates")
                    return key1, key2, digest
                next_seed = (seed + workers * step) & ((1 << 64) - 1)
                start(next_seed or seed + 1)
            time.sleep(0.01)
    finally:
        stop_workers()

def generate_collision(plaintext, binary):
    key1, key2, digest = find_collision(plaintext, binary)
    if key1 == key2:
        raise RuntimeError("generated identical keys")
    if lock(plaintext, key1, 5) != digest or lock(plaintext, key2, 5) != digest:
        raise RuntimeError("generated keys do not collide")
    return key1, key2, digest

def read_banner(text):
    plaintext = re.search(r"Plaintext:\s*([0-9a-fA-F]{32})", text)
    round_number = re.search(r"Round\s+(\d+)\s*/\s*(\d+)", text)
    if not plaintext or not round_number:
        raise RuntimeError(f"could not parse server output:\n{text}")
    return (bytes.fromhex(plaintext.group(1)),int(round_number.group(1)),int(round_number.group(2)))

def receive_round(connection):
    try:
        data = connection.recvuntil(b"Key 1 > ")
    except EOFError as error:
        leftover = connection.clean()
        if leftover:
            print(leftover.decode(errors="replace"), end="")
        raise RuntimeError("server closed before the next key prompt") from error

    if not data:
        raise RuntimeError("timed out waiting for the next key prompt")

    text = data.decode(errors="replace")
    print(text, end="")
    return read_banner(text)

def main():
    binary = build_helper()
    connection = remote("127.0.0.1", 10019)

    try:
        while True:
            plaintext, round_number, total_rounds = receive_round(connection)
            key1, key2, digest = generate_collision(plaintext, binary)

            print(f"key 1:  {key1.hex()}")
            print(f"key 2:  {key2.hex()}")
            print(f"digest: {digest.hex()}")

            connection.sendline(key1.hex().encode())
            print(connection.recvuntil(b"Key 2 > ").decode(errors="replace"), end="")
            connection.sendline(key2.hex().encode())

            if round_number >= total_rounds:
                print(connection.recvall().decode(errors="replace"), end="")
                break
    finally:
        connection.close()

if __name__ == "__main__":
    main()
