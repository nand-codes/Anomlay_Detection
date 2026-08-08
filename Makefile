COMPOSE := docker compose -f docker-compose.dev.yml
REDPANDA := redpanda-0
TOPIC ?= kpis.raw
PARTITIONS ?= 12
RETENTION_MS ?= 900000
INTERVAL_SEC ?= 900

.PHONY: up down ps logs health topics consume produce-smoke sim-install sim sim-docker ingest-install ingest ingest-docker db-query dashboard-install dashboard dashboard-docker help

help:
	@echo "Part A — Redpanda"
	@echo "  make up             Start Redpanda + Console"
	@echo "  make health         Wait until cluster is healthy"
	@echo "  make topics         Create $(TOPIC) (partitions=$(PARTITIONS))"
	@echo "  make produce-smoke  Produce one test message"
	@echo "  make consume        Consume from $(TOPIC) (Ctrl+C to stop)"
	@echo "  make ps / logs      Status / follow logs"
	@echo "  make down           Stop and remove volumes"
	@echo ""
	@echo "Part B — KPI simulator"
	@echo "  make sim-install    Create venv + install deps"
	@echo "  make sim            Run simulator locally"
	@echo "  make sim-docker     Run simulator in Docker (profile sim)"
	@echo ""
	@echo "Part C — Ingest + TimescaleDB"
	@echo "  make ingest-install Create venv + install deps"
	@echo "  make ingest         Run ingest worker locally"
	@echo "  make ingest-docker  Run ingest worker in Docker (profile ingest)"
	@echo "  make db-query       Show kpi_samples counts"
	@echo ""
	@echo "Dashboard"
	@echo "  make dashboard-install  Install dashboard deps"
	@echo "  make dashboard          Run dashboard locally"
	@echo "  make dashboard-docker   Run dashboard in Docker"

up:
	$(COMPOSE) up -d
	@$(MAKE) health

down:
	$(COMPOSE) down -v

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f redpanda-0

health:
	@echo "Waiting for Redpanda healthy..."
	@until docker exec $(REDPANDA) rpk cluster health 2>/dev/null | grep -E 'Healthy:.+true' >/dev/null; do \
		sleep 2; \
	done
	@docker exec $(REDPANDA) rpk cluster health
	@echo "Bootstrap (host): localhost:19092"
	@echo "Console:          http://localhost:8080"

topics:
	@docker exec $(REDPANDA) rpk topic create $(TOPIC) \
		-p $(PARTITIONS) \
		-r 1 \
		--topic-config retention.ms=$(RETENTION_MS) \
		|| echo "Topic $(TOPIC) may already exist — updating retention"
	@docker exec $(REDPANDA) rpk topic alter-config $(TOPIC) --set retention.ms=$(RETENTION_MS)
	docker exec $(REDPANDA) rpk topic list
	docker exec $(REDPANDA) rpk topic describe $(TOPIC)

produce-smoke:
	@echo '{"ts":"2026-08-08T00:00:00Z","device_id":"smoke-01","site":"lab","metric":"latency_ms","value":1.0}' | \
		docker exec -i $(REDPANDA) rpk topic produce $(TOPIC) -k smoke-01
	@echo "Smoke message produced to $(TOPIC)"

consume:
	docker exec -it $(REDPANDA) rpk topic consume $(TOPIC) -n 20

SIM_DIR := apps/kpi-simulator
VENV_PY := $(SIM_DIR)/.venv/bin/python
VENV_PIP := $(SIM_DIR)/.venv/bin/pip

sim-install:
	cd $(SIM_DIR) && python3 -m venv .venv && $(VENV_PIP) install -r requirements.txt
	@test -f $(SIM_DIR)/config.yaml || cp $(SIM_DIR)/config.example.yaml $(SIM_DIR)/config.yaml

sim:
	cd $(SIM_DIR) && $(VENV_PY) -m kpi_simulator

sim-docker:
	$(COMPOSE) --profile sim up -d --build kpi-simulator

INGEST_DIR := apps/ingest-worker
INGEST_VENV_PY := $(INGEST_DIR)/.venv/bin/python
INGEST_VENV_PIP := $(INGEST_DIR)/.venv/bin/pip

ingest-install:
	cd $(INGEST_DIR) && python3 -m venv .venv && $(INGEST_VENV_PIP) install -r requirements.txt
	@test -f $(INGEST_DIR)/config.yaml || cp $(INGEST_DIR)/config.example.yaml $(INGEST_DIR)/config.yaml

ingest:
	cd $(INGEST_DIR) && $(INGEST_VENV_PY) -m ingest_worker

ingest-docker:
	$(COMPOSE) --profile ingest up -d --build ingest-worker

db-query:
	docker exec timescaledb psql -U netintel -d netintel -c "SELECT count(*) AS kpi_site_samples FROM kpi_site_samples;"
	docker exec timescaledb psql -U netintel -d netintel -c "SELECT ts, site, metric, value FROM kpi_site_samples ORDER BY ts DESC LIMIT 15;"

DASH_DIR := apps/dashboard
DASH_VENV_PY := $(DASH_DIR)/.venv/bin/python
DASH_VENV_PIP := $(DASH_DIR)/.venv/bin/pip

dashboard-install:
	cd $(DASH_DIR) && python3 -m venv .venv && $(DASH_VENV_PIP) install -r requirements.txt

dashboard:
	cd $(DASH_DIR) && $(DASH_VENV_PY) -m dashboard

dashboard-docker:
	$(COMPOSE) up -d --build dashboard
