FROM alpine:3.20 AS builder

RUN apk add --no-cache \
    bash \
    binutils \
    build-base \
    python3 \
    socat 

WORKDIR /src
COPY . /src

RUN mkdir -p /src/modules \
    && gcc -O2 -Wall -Wextra -static -o /src/chal /src/chal.c \
    && bash /src/compile.sh /src/cat.S cat "Print file. Usage: cat <file>" \
    && bash /src/compile.sh /src/echo.S echo "Print args to stdout. Usage: echo <text>" \
    && bash /src/compile.sh /src/exit.S exit "Exit the shell." \
    && bash /src/compile.sh /src/help.S help "Show help text." \
    && bash /src/compile.sh /src/ray.S ray "Simulate a cosmic ray, once per execution. Usage: ray <address to write in decimal> <byte value in decimal>" \
    && printf 'L3AK{3v3r_h3ard_0f_4_s36f4u1t_0r4c13?!}\n' > /src/flag.txt

FROM alpine:3.20

RUN apk add --no-cache socat bash

WORKDIR /opt/bosh
COPY --from=builder /src/chal /opt/bosh/chal
COPY --from=builder /src/modules /opt/bosh/modules
COPY --from=builder /src/flag.txt /opt/bosh/flag.txt
COPY --from=builder /src/run.sh /opt/bosh/run.sh

RUN mkdir -p /opt/bosh/modules \
    && chmod 755 /opt/bosh/chal /opt/bosh/run.sh \
    && find /opt/bosh -type f \( -name '*.S' -o -name '*.c' -o -name 'compile.sh' -o -name 'makeModule.py' -o -name 'Dockerfile' \) -delete \
    && find /opt/bosh -type d -empty -delete

EXPOSE 5000

ENTRYPOINT ["/bin/sh", "-c", "socat TCP-LISTEN:5000,reuseaddr,fork EXEC:'/opt/bosh/run.sh'" ]
