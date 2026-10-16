# Se construye desde la RAÍZ del repo para poder copiar la librería común:
#   docker build -f services/availability/Dockerfile .
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app/shared \
    PYTHONUNBUFFERED=1 \
    DB_PATH=/data/availability.db

COPY services/availability/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/availability/app/ /app/app/

RUN mkdir -p /data
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
