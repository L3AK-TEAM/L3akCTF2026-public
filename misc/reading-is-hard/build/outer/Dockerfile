FROM gcc:14 AS readflag
WORKDIR /build
COPY readflag.c .

RUN gcc -static -O2 -o readflag readflag.c

FROM postgres:18.4
RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

COPY --from=readflag /build/readflag /usr/local/bin/readflag
RUN chown root:root /usr/local/bin/readflag && chmod 4111 /usr/local/bin/readflag

COPY outer /app/outer
COPY alice.txt /app/alice.txt
COPY hhgttg.txt /app/hhgttg.txt
COPY flag.txt /app/flag.txt
COPY flag2.txt /flag2.txt
RUN chown root:root /flag2.txt && chmod 400 /flag2.txt
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh /app/outer

WORKDIR /app
EXPOSE 1337
ENTRYPOINT []
CMD ["/usr/local/bin/start.sh"]
