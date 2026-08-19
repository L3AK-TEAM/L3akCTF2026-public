FROM sagemath/sagemath:latest

USER root
RUN apt-get update -y && \
    apt-get install -y socat curl

WORKDIR /app
COPY chal.py run.sh flag.txt /app/

RUN chmod +x /app/chal.py /app/run.sh

USER sage
RUN /home/sage/sage/local/var/lib/sage/venv-python3.12/bin/python3.12 -m pip install pycryptodome

EXPOSE 1337

CMD ["socat", \
     "TCP-LISTEN:1337,reuseaddr,fork", \
     "EXEC:/app/run.sh,stderr"]
