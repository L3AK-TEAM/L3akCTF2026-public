FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=1337

WORKDIR /challenge

RUN useradd --create-home --shell /usr/sbin/nologin chall \
    && python3 -m pip install --no-cache-dir --upgrade pip

COPY --chown=chall:chall requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=chall:chall server.py flag.txt ./
COPY --chown=chall:chall static ./static

USER chall
EXPOSE 1337

CMD ["gunicorn", "--bind", "0.0.0.0:1337", "--workers", "1", "--threads", "4", "--timeout", "30", "server:app"]
