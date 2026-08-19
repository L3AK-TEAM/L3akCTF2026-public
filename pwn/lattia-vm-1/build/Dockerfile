FROM debian:bookworm AS build

RUN apt update && \
    apt install -y gcc patchelf

WORKDIR /build
COPY . .

RUN gcc wrapper.c -o wrapper
RUN patchelf \
    --set-interpreter /app/ld-linux-x86-64.so.2 \
    --set-rpath /app \
    wrapper
RUN patchelf \
    --set-interpreter /app/ld-linux-x86-64.so.2 \
    --set-rpath /app \
    lattia-vm

FROM pwn.red/jail

COPY --from=debian:bookworm-slim / /srv
COPY --from=build /build/wrapper /srv/app/run
COPY --from=build /build/lattia-vm /srv/app/lattia-vm
COPY libc.so.6 /srv/app/libc.so.6
COPY ld-linux-x86-64.so.2 /srv/app/ld-linux-x86-64.so.2
COPY flag.txt /srv/app/flag.txt

RUN chmod 0555 /srv/app/run /srv/app/lattia-vm /srv/app/ld-linux-x86-64.so.2
ENV JAIL_TIME=60
ENV JAIL_MEM=64M
