FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /usr/sbin/nologin ctf

COPY lock.py server.py flag.txt ./

USER ctf

EXPOSE 10019

CMD exec socat -T 45 TCP-LISTEN:10019,reuseaddr,fork EXEC:"python3 -u /app/server.py",stderr
