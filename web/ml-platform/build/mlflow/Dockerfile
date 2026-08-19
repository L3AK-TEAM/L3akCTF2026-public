FROM python:3.12-slim

RUN pip install --no-cache-dir mlflow==3.14.0

COPY flag /flag

WORKDIR /srv
EXPOSE 5000
CMD ["mlflow", "server", \
     "--backend-store-uri", "sqlite:////srv/mlflow.db", \
     "--default-artifact-root", "/srv/artifacts", \
     "--serve-artifacts", \
     "--host", "0.0.0.0", "--port", "5000"]
