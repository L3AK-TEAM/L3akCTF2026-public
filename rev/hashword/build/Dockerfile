FROM golang:1.26-bookworm

ENV GOCACHE=/go/cache \
    GOMODCACHE=/go/pkg/mod \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 python3-venv \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY web/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY hashword/ /src/hashword/
COPY gen/genflag/ /src/gen/genflag/
COPY web/ /srv/app/
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

RUN cd /src/gen/genflag \
 && go run . -flag 'placeholder' -hint 'http://placeholder.invalid' -out /src/hashword/flag.go \
 && cd /src/hashword \
 && go mod download \
 && go build -trimpath -ldflags='-s -w' -o /tmp/warmup . \
 && rm -f /tmp/warmup

RUN useradd --uid 10001 --create-home app \
 && mkdir -p /srv/dist \
 && chown -R app:app /src /srv /go

USER app
WORKDIR /srv/app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python3 -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=4).status==200 else 1)"

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
