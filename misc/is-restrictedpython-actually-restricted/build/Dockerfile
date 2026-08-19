# syntax=docker/dockerfile:1.7
FROM python:3.14.5-slim@sha256:c845af9399020c7e562969a13689e929074a10fd057acd1b1fad06a2fb068e97 AS runtime

RUN python3 -m pip install --no-cache-dir "RestrictedPython==8.4"

FROM pwn.red/jail@sha256:ee52ad5fd6cfed7fd8ea30b09792a6656045dd015f9bef4edbbfa2c6e672c28c

COPY --from=runtime / /srv
COPY --chmod=0555 chall.py /srv/app/run
COPY --chmod=0444 flag.txt /srv/flag.txt

ENV JAIL_TIME=20 \
    JAIL_MEM=64M \
    JAIL_PIDS=8 \
    JAIL_CPU=500 \
    JAIL_CONNS_PER_IP=8 \
    JAIL_PORT=1622 \
    JAIL_TMP_SIZE=2M \
    JAIL_ENV_PYTHONUNBUFFERED=1 \
    JAIL_ENV_PYTHONDONTWRITEBYTECODE=1 \
    JAIL_ENV_CHALLENGE_WORKDIR=/tmp

EXPOSE 1622
