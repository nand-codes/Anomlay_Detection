FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingest_worker ./ingest_worker
COPY config.example.yaml ./config.example.yaml

ENV KAFKA_BOOTSTRAP=redpanda-0:9092
ENV KPI_TOPIC=kpis.raw
ENV DATABASE_URL=postgresql://netintel:netintel@timescaledb:5432/netintel
ENV METRICS_PORT=9101

EXPOSE 9101

CMD ["python", "-m", "ingest_worker"]
