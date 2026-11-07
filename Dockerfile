FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /srv
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app
COPY web ./web
COPY eval ./eval

RUN useradd --create-home --uid 10001 appuser
USER appuser

# Render sets $PORT. --proxy-headers lets rate limits see the real client IP
# behind Render's proxy. Uvicorn's access log is off; the app logs method,
# path, status and duration only (never message text).
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*' --no-access-log --timeout-keep-alive 30"]
