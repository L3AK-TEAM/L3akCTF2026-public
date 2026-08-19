FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /usr/sbin/nologin ctf

RUN pip install --no-cache-dir pycryptodome==3.23.0

COPY chall.py flag.txt .

USER ctf

EXPOSE 10027

CMD exec socat -T 600 TCP-LISTEN:10027,reuseaddr,fork EXEC:"python3 -u /app/chall.py"
