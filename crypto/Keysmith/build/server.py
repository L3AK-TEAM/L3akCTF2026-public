import os
import signal
from lock import lock

N = 5
TIMEOUT = 40
FLAG = open("flag.txt", "r").read()

def timeout_handler(signum, frame):
    print("The lock breaks. Time is up.")
    raise SystemExit

def parse_key(line):
    key_hex = "".join(line.strip().split()).lower()
    if key_hex.startswith("0x"):
        key_hex = key_hex[2:]
    if len(key_hex) != 48:
        raise ValueError("Key length must be 24 bytes!")
    try:
        return bytes.fromhex(key_hex)
    except ValueError as exc:
        raise ValueError("Key must be hex.") from exc

def main():

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(TIMEOUT)

    print("== Keysmith ==")
    print("When a lock can be opened by multiple keys, is it a bad lock or is there just a good keysmith around?")

    for i in range(40):

        print(f"Round {i+1}/40")
        plaintext = bytes.fromhex(os.urandom(16).hex())
        print(f"Plaintext: {plaintext.hex()}")

        try:
            key1 = parse_key(input("Key 1 > "))
            key2 = parse_key(input("Key 2 > "))
        except EOFError:
            return
        except ValueError as exc:
            print(f"Invalid input: {exc}")
            return

        if key1 == key2:
            print("The keys must be distinct.")
            return

        ct1 = lock(plaintext, key1, N)
        ct2 = lock(plaintext, key2, N)

        if ct1 == ct2:
            print("Success!")
            continue
        else:
            print("Failure!")
            print(f"lock(key1) = {ct1.hex()}")
            print(f"lock(key2) = {ct2.hex()}")
            return

    print("The lock yields to craft, not chance.")
    print(FLAG)

if __name__ == "__main__":
    main()
