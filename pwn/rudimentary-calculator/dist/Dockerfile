FROM ubuntu@sha256:f3d28607ddd78734bb7f71f117f3c6706c666b8b76cbff7c9ff6e5718d46ff64 AS app

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends socat && \
    rm -rf /var/lib/apt/lists/*

COPY chall .

EXPOSE 1337

CMD exec socat TCP-LISTEN:1337,reuseaddr,fork EXEC:"/app/chall"
