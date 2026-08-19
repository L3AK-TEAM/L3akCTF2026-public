FROM alpine:3.20

RUN apk add --no-cache aria2

WORKDIR /data

# Bring in the torrent and the file it seeds
COPY . .

RUN chown -R 10000:10000 /data

USER 10000:10000

EXPOSE 6897/tcp
EXPOSE 6897/udp

CMD ["aria2c", \
     "--check-integrity=true", \
     "--seed-ratio=0.0", \
     "--enable-dht=true", \
     "--listen-port=6897", \
     "--dht-listen-port=6897", \
     "important files.torrent"]
