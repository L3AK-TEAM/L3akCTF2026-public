# --- build stage: compile the runner (needs the host + MIPS toolchains) ----
FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc-mips-linux-gnu \
        python3 \
        make \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY . .

RUN make clean && make executor run

# --- app stage: assemble the challenge rootfs ------------------------------
FROM debian:bookworm-slim@sha256:7b140f374b289a7c2befc338f42ebe6441b7ea838a042bbd5acbfca6ec875818 AS app

RUN mkdir -p /app
COPY --from=builder --chmod=555 /src/out/executor /app/executor
COPY --from=builder --chmod=555 /src/out/run /app/run

# --- jail stage: redpwn nsjail provides the listener + sandbox -------------
FROM pwn.red/jail@sha256:ee52ad5fd6cfed7fd8ea30b09792a6656045dd015f9bef4edbbfa2c6e672c28c

COPY --from=app / /srv
COPY --chmod=444 build/.env /srv/app/.env
COPY --chmod=444 build/flag.txt /srv/app/flag.txt

ENV JAIL_PIDS=20 \
    JAIL_MEM=4M \
    JAIL_TIME=120 \
    JAIL_TMP_SIZE=8K \
    JAIL_CONNS=100 \
    JAIL_CONNS_PER_IP=4 \
    JAIL_CPU=100