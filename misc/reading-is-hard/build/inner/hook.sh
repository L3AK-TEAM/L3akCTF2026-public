#!/bin/sh
set -eu

grep -q '^clone_newnet:' /tmp/nsjail.cfg 2>/dev/null || printf '\nclone_newnet: false\n' >> /tmp/nsjail.cfg

OUTER_IP=$(awk '$2 == "outer" {print $1; exit}' /etc/hosts)
if [ -z "$OUTER_IP" ]; then
	OUTER_IP=$(nslookup outer. | awk '/^Address: / {ip=$2} END {print ip}')
	[ -n "$OUTER_IP" ]
	printf '%s\touter\n' "$OUTER_IP" >> /etc/hosts
fi

grep -q 'dst: *"/etc/hosts"' /tmp/nsjail.cfg 2>/dev/null ||
	printf '\nmount { src: "/etc/hosts" dst: "/etc/hosts" is_bind: true }\n' >> /tmp/nsjail.cfg

nft() {
	/opt/fw/ld-linux-x86-64.so.2 --library-path /opt/fw/lib /opt/fw/nft "$@"
}

if ! nft list table ip jail >/dev/null 2>&1; then
	nft -f /opt/fw/rules.nft
fi
