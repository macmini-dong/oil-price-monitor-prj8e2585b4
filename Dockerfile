FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN mkdir -p /app/data/backups

ENV OIL_DB_PATH=/app/data/oil_prices.db
ENV OIL_BACKUP_DIR=/app/data/backups
ENV FETCH_INTERVAL_SECONDS=600
ENV APP_VERSION=1.0.0
ENV APP_UPDATED_AT="2026-03-08 06:21 CST"

EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

