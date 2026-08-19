FROM python:3.14-slim@sha256:6a27522252aef8432841f224d9baaa6e9fce07b07584154fa0b9a96603af7456

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends libzbar0=0.23.93-8 socat && \
    rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --shell /usr/sbin/nologin ctf

RUN pip install --no-cache-dir pillow==12.1.1 pyzbar==0.1.9 qrcode==8.2

COPY chall.py flag.txt ./

USER ctf

EXPOSE 10018

CMD exec socat -T 30 TCP-LISTEN:10018,reuseaddr,fork EXEC:"python3 -u /app/chall.py",stderr
