FROM gcc:14 AS readflag
WORKDIR /build
COPY readflag.c .

RUN gcc -static -O2 -o readflag readflag.c

FROM ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90 

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY supervisor .

COPY --from=readflag /build/readflag /readflag
RUN chown root:root /readflag \
    && chmod +s /readflag 

COPY flag.txt /flag.txt
RUN chown root:root /flag.txt \
    && chmod 0400 /flag.txt

USER ubuntu

EXPOSE 8000
CMD ["socat", "TCP-LISTEN:8000,reuseaddr,fork", "EXEC:./supervisor"]