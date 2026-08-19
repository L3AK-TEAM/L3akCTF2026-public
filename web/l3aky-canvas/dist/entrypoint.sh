#!/bin/sh
set -e

if [ -e /home/web/flag ]; then
    mv /home/web/flag "/srv/rooms/flag-$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n').bin"
fi
unset FLAG
exec /l3aky-canvas
