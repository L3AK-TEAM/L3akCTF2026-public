# Build and deployment

This directory contains every file required to compile and deploy the
challenge.

## Native Ubuntu x86-64 build

From this directory:

```bash
sudo apt-get update
sudo apt-get install -y build-essential python3 file

make clean
make release
```

The player files are written to:

```text
../dist/whatwho
../dist/vault.wwc
```

## Docker deployment

```bash
export WHATWHO_FLAG='L3AK{wh4t_4sks_wh0_4nsw3rs}'
export WHATWHO_PORT=28451
docker compose up -d --build
```

Connect to the deployed challenge:

```bash
nc 127.0.0.1 28451
```

The service runs as an unprivileged account, obtains a fresh 64-bit seed for
each connection, and reads the flag only from `WHATWHO_FLAG`.

## Cross-build the handout

On a non-Linux organizer machine with Docker Buildx:

```bash
make dist
```

This produces the same Linux amd64 player files in `../dist`.
