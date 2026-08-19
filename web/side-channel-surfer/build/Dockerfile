FROM python:3.11-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    SITE=http://127.0.0.1:5000 \
    FLAG=flag{fake_flag_for_testing}

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium \
    && chmod -R o+rx /ms-playwright

RUN useradd --create-home --uid 1000 appuser && chown appuser:appuser /app
COPY --chown=appuser:appuser app.py bot.py ./
COPY --chown=appuser:appuser templates ./templates

USER appuser

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--worker-class", "gthread", "--timeout", "180", "app:app"]
