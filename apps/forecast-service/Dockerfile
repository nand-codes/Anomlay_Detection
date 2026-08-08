FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY forecast_service ./forecast_service
COPY config.example.yaml ./config.example.yaml

ENV DATABASE_URL=postgresql://netintel:netintel@timescaledb:5432/netintel
ENV INTERVAL_SEC=900
ENV FORECAST_HORIZON_HOURS=4
ENV FORECAST_MIN_HISTORY_POINTS=48
ENV FORECAST_MODEL=ets
ENV METRICS_PORT=9102

EXPOSE 9102

CMD ["python", "-m", "forecast_service"]
