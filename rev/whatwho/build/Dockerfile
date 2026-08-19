FROM ubuntu:24.04 AS builder
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev python3 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY src/ src/
COPY tools/ tools/
RUN mkdir out \
 && python3 tools/build_cartridge.py -o out/vault.wwc \
 && gcc -std=c17 -O2 -s -Wall -Wextra -Werror -Wpedantic \
    -fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE \
    -fvisibility=hidden -Isrc src/main.c src/cartridge.c src/vm.c \
    -pie -Wl,-z,relro,-z,now,--build-id=none -o out/whatwho

FROM scratch AS artifacts
COPY --from=builder /src/out/whatwho /whatwho
COPY --from=builder /src/out/vault.wwc /vault.wwc

FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends \
    socat coreutils && rm -rf /var/lib/apt/lists/*
COPY --from=builder --chmod=0555 /src/out/whatwho /opt/whatwho/whatwho
COPY --from=builder --chmod=0444 /src/out/vault.wwc /opt/whatwho/vault.wwc
USER 10001:10001
EXPOSE 28451
CMD ["socat", "TCP-LISTEN:28451,reuseaddr,fork,max-children=64", "EXEC:timeout 120s /opt/whatwho/whatwho /opt/whatwho/vault.wwc,stderr,setsid"]
