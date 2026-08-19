FROM ubuntu@sha256:f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64 AS app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libpng16-16 && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /challenge
WORKDIR /challenge
COPY piet .
COPY flag.txt .

FROM pwn.red/jail@sha256:ee52ad5fd6cfed7fd8ea30b09792a6656045dd015f9bef4edbbfa2c6e672c28c

COPY --from=app / /srv
RUN mkdir -p /srv/app
COPY --chmod=555 ./run /srv/app/run

ENV JAIL_TIME=120 \
    JAIL_MEM=64M \
    JAIL_PIDS=32 \
    JAIL_CONNS=64 \
    JAIL_TMP_SIZE=4M
