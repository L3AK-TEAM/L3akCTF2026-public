FROM node:20-bookworm-slim AS node-deps
WORKDIR /app
COPY package.json ./package.json
ENV PUPPETEER_SKIP_DOWNLOAD=true
RUN npm install --omit=dev --no-audit --no-fund

FROM rust:1.90-slim-bookworm AS build
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/cloudflare/svg-hush.git /app/svg-hush
COPY . ./northstar-portal
COPY --from=node-deps /app/node_modules /app/northstar-portal/node_modules

WORKDIR /app/northstar-portal
RUN cargo build --release --locked && strip target/release/northstar-portal

FROM debian:bookworm-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends nodejs chromium ca-certificates tini && rm -rf /var/lib/apt/lists/*
COPY --from=build /app/northstar-portal/target/release/northstar-portal /usr/local/bin/northstar-portal
COPY --from=build /app/northstar-portal/bot /app/bot
COPY --from=build /app/northstar-portal/node_modules /app/node_modules
COPY --from=build /app/northstar-portal/package.json /app/package.json

ENV BOT_BROWSER_PATH=/usr/bin/chromium
EXPOSE 3000

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["northstar-portal"]
