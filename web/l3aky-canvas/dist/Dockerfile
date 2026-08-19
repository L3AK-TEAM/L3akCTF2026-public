FROM ubuntu:24.04
RUN userdel -r ubuntu 2>/dev/null || true; \
    useradd -m -u 1000 -s /usr/sbin/nologin web
COPY --chmod=0755 l3aky-canvas /l3aky-canvas
COPY --chown=web:web rooms/ /srv/rooms/
COPY --chown=web:web flag /home/web/flag
COPY --chmod=0755 entrypoint.sh /entrypoint.sh
ENV PIXEL_COOLDOWN=60
EXPOSE 8000
USER web
ENTRYPOINT ["/entrypoint.sh"]
