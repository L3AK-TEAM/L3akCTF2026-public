#!/bin/sh
set -eu

node /app/server.js &
APP_PID=$!

trap 'kill "$APP_PID" 2>/dev/null || true' EXIT INT TERM

exec /usr/local/bin/coraza-waf
