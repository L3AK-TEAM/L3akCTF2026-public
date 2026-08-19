#!/bin/sh

cd /opt/bosh

/opt/bosh/chal
status=$?

echo
printf '[process exited with status %s]\n' "$status" 
exit "$status"
