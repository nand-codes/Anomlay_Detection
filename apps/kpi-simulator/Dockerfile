FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY kpi_simulator ./kpi_simulator
COPY config.example.yaml ./config.example.yaml

ENV KAFKA_BOOTSTRAP=redpanda-0:9092
ENV KPI_TOPIC=kpis.raw
ENV INTERVAL_SEC=900
ENV METRICS_PORT=9100

EXPOSE 9100

CMD ["python", "-m", "kpi_simulator"]
