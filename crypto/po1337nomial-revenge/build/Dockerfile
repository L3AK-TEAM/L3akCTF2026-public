FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /usr/sbin/nologin ctf

COPY server.py .

USER ctf

EXPOSE 10028

ENV FLAG="L3AK{19937_bottles_of_beer_on_the_wall}"

CMD exec socat -T 600 TCP-LISTEN:10028,reuseaddr,fork EXEC:"python3 -u /app/server.py"
