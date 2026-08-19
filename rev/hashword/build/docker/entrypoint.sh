#!/bin/sh

set -eu

: "${FLAG:?FLAG is not set - set it in docker-compose.yml}"

BASE_URL=${BASE_URL:-http://localhost:8000}

cd /srv/app
HINT_PATH=$(python3 -c 'import app; print(app.HINT_PATH)')
HINT_URL="${BASE_URL%/}${HINT_PATH}"

echo "==> sealing the flag"
echo "    hint URL: $HINT_URL"
cd /src/gen/genflag
go run . -flag "$FLAG" -hint "$HINT_URL" -out /src/hashword/flag.go

echo "==> building the challenge binary"
cd /src/hashword
go build -trimpath -ldflags='-s -w' -o /srv/dist/hashword .
sha256sum /srv/dist/hashword

unset FLAG

echo "==> starting the web server"
cd /srv/app
exec gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 2 \
    --access-logfile - \
    --error-logfile - \
    app:app
