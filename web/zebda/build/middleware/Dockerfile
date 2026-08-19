FROM node:24.18.0-bookworm-slim

WORKDIR /app

ENV NODE_ENV=production

COPY package.json package-lock.json ./

RUN npm ci --omit=dev

COPY --chown=node:node src ./src

USER node

EXPOSE 8080

CMD ["node", "src/server.js"]