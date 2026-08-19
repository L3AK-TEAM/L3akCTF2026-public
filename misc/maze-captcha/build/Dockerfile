FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=1337

WORKDIR /challenge

RUN useradd --create-home --shell /usr/sbin/nologin chall \
    && pip install --no-cache-dir wcwidth

COPY --chown=chall:chall server.py flag.txt banner.txt ./

USER chall
EXPOSE 1337

CMD ["python3", "server.py"]
