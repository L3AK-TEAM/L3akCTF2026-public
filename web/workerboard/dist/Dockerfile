FROM gcc:14 AS readflag
COPY readflag.c /readflag.c
RUN gcc -static -O2 -o /readflag /readflag.c

FROM golang:1.24-bookworm AS builder

WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY main.go startup.go ./
COPY api ./api
COPY public ./public
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /workerboard .

FROM node:24-bookworm-slim

COPY --from=readflag --chown=root:root --chmod=0111 /readflag /readflag

RUN npm install --global "workerd@1.20260713.1" && npm cache clean --force

RUN apt-get update && apt-get install -y ca-certificates

WORKDIR /app
COPY --from=builder --chown=node:node /workerboard /app/workerboard
COPY --chown=node:node config.capnp runtime.js ./

COPY default /app/default/

RUN mkdir -p /data/workers && chown -R node:node /data

USER node
EXPOSE 8080

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD ["/app/workerboard", "-healthcheck"]

CMD ["/app/workerboard"]
