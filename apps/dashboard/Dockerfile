FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dashboard ./dashboard
COPY static ./static

ENV DATABASE_URL=postgresql://netintel:netintel@timescaledb:5432/netintel
ENV KAFKA_BOOTSTRAP=redpanda-0:9092
ENV REDPANDA_ADMIN_URL=http://redpanda-0:9644
ENV KPI_TOPIC=kpis.raw
ENV PORT=8088

EXPOSE 8088

CMD ["python", "-m", "dashboard"]
