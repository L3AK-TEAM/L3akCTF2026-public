FROM python:3.14-alpine

RUN apk add --no-cache socat && \
    adduser --disabled-password --no-create-home ctf

COPY challenge /usr/src/app/

WORKDIR /usr/src/app

RUN chmod +x ./entrypoint.sh ./server1.py

USER ctf

EXPOSE 1337

ENTRYPOINT ["./entrypoint.sh"]
