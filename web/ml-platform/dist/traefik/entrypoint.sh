#!/bin/sh
set -eu

pw=$(head -c 1024 /dev/urandom | tr -dc 'A-Za-z0-9' | head -c 32)
hash=$(printf '%s' "$pw" | sha1sum | cut -d' ' -f1 | xxd -r -p | base64)
printf 'admin:{SHA}%s\n' "$hash" > /tmp/users

if [ "${1:-}" = "traefik" ]; then shift; fi
exec traefik "$@"
