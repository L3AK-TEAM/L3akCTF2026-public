FROM python:3.12-slim AS rootfs

FROM debian:bookworm-slim AS fw
RUN apt-get update && apt-get install -y --no-install-recommends nftables \
 && mkdir -p /fw/lib && cp /usr/sbin/nft /lib64/ld-linux-x86-64.so.2 /fw/ \
 && ldd /usr/sbin/nft | awk '/=>/{print $3}' | xargs -I{} cp -L {} /fw/lib/

FROM pwn.red/jail@sha256:ee52ad5fd6cfed7fd8ea30b09792a6656045dd015f9bef4edbbfa2c6e672c28c
COPY --from=rootfs / /srv
COPY --from=fw /fw /opt/fw
COPY main.py /srv/app/run
COPY hook.sh /jail/hook.sh
COPY rules.nft /opt/fw/rules.nft
RUN touch /srv/etc/hosts && chmod 755 /srv/app/run /jail/hook.sh /opt/fw/nft

ENV JAIL_TIME=30 \
    JAIL_MEM=256M \
    JAIL_PIDS=100 \
    JAIL_POW=0 \
    JAIL_PORT=5000

EXPOSE 5000
