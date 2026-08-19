FROM python:3.13-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin ctf

COPY answers.json flag.txt server.py ./

ENV PYTHONDONTWRITEBYTECODE=1

USER ctf

EXPOSE 1337

CMD ["socat", "-T", "900", "TCP-LISTEN:1337,reuseaddr,fork,max-children=64", "EXEC:python3 -u /app/server.py,stderr"]
