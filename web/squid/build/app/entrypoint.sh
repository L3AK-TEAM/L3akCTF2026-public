#!/bin/sh
set -eu

mkdir -p /secrets
if [ ! -s /secrets/flag ]; then
    printf '%s' "${FLAG:-L3AK{missing_flag}}" > /secrets/flag
fi
chown root:root /secrets/flag
chmod 600 /secrets/flag
unset FLAG

mkdir -p /work
chown ctf:ctf /work
chmod 755 /work

python /app/worker.py &

export SECRET_KEY="$(python -c 'import os,base64;print(base64.b64encode(os.urandom(32)).decode())')"
exec gosu ctf gunicorn \
    --worker-class gthread \
    --workers 1 \
    --threads 16 \
    --no-sendfile \
    --bind 0.0.0.0:5000 \
    --access-logfile - \
    --error-logfile - \
    public_app:app
