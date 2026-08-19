#!/usr/bin/env bash
set -euo pipefail

randhex() { LC_ALL=C tr -dc 'a-f0-9' </dev/urandom | head -c 64; }

APP_PW="c43146fec7e455ce7f116a0198efe0ea"

export POSTGRES_PASSWORD="$(randhex)"
export POSTGRES_INITDB_ARGS="--auth-local=scram-sha-256 --auth-host=scram-sha-256"

cat > /docker-entrypoint-initdb.d/10-app.sql <<SQL
CREATE ROLE app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD '${APP_PW}';
CREATE TABLE submissions(
  id serial PRIMARY KEY,
  len int NOT NULL,
  hex text NOT NULL,
  won boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now());
GRANT SELECT, INSERT ON submissions TO app;
GRANT USAGE, SELECT ON SEQUENCE submissions_id_seq TO app;
SQL

export DATABASE_URL="postgres://app:${APP_PW}@127.0.0.1:5432/postgres?sslmode=disable"

docker-entrypoint.sh postgres &

until PGPASSWORD="$APP_PW" psql -U app -h 127.0.0.1 -d postgres -qtAXc 'SELECT 1' >/dev/null 2>&1; do
    sleep 0.5
done
rm -f /docker-entrypoint-initdb.d/10-app.sql

exec socat TCP-LISTEN:1337,reuseaddr,fork EXEC:/app/outer
