#!/bin/sh

exec socat -dd tcp-l:1337,reuseaddr,fork,keepalive exec:"python3 ./server1.py"
