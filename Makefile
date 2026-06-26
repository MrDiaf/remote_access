COMPOSE ?= docker compose
GUACAMOLE_VERSION ?= 1.5.5
BACKUP_DIR ?= backups
BACKUP_FILE ?= $(BACKUP_DIR)/server-control-panel-$$(date +%Y%m%d-%H%M%S).tar.gz

.PHONY: help up down restart build logs ps remote-up remote-down guacamole-init backend-shell frontend-shell db-shell clean backup restore

help:
	@printf "server-control-panel commands\n\n"
	@printf "  make up                Start dashboard, backend, proxy, and Portainer\n"
	@printf "  make down              Stop the default stack\n"
	@printf "  make restart           Restart the default stack\n"
	@printf "  make build             Rebuild images\n"
	@printf "  make logs              Follow logs\n"
	@printf "  make ps                Show container status\n"
	@printf "  make remote-up         Start Guacamole, guacd, and PostgreSQL\n"
	@printf "  make remote-down       Stop the Guacamole remote desktop stack\n"
	@printf "  make guacamole-init    Generate Guacamole PostgreSQL init schema\n"
	@printf "  make backend-shell     Open a shell in the backend container\n"
	@printf "  make frontend-shell    Open a shell in the frontend container\n"
	@printf "  make db-shell          Open psql in the Guacamole database container\n"
	@printf "  make clean             Remove stopped containers and build cache carefully\n"
	@printf "  make backup            Archive config and local data\n"
	@printf "  make restore           Print restore guidance\n"

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

remote-up: guacamole-init
	$(COMPOSE) --profile remote up -d guacamole-db guacd guacamole

remote-down:
	$(COMPOSE) --profile remote stop guacamole guacd guacamole-db

guacamole-init:
	mkdir -p data/guacamole
	@if [ -d data/guacamole/initdb.sql ]; then \
		printf "data/guacamole/initdb.sql is a directory; remove it and rerun make guacamole-init\n" >&2; \
		exit 1; \
	elif [ -f data/guacamole/initdb.sql ]; then \
		printf "data/guacamole/initdb.sql already exists\n"; \
	else \
		docker run --rm guacamole/guacamole:$(GUACAMOLE_VERSION) /opt/guacamole/bin/initdb.sh --postgresql > data/guacamole/initdb.sql; \
		printf "Generated data/guacamole/initdb.sql\n"; \
	fi

backend-shell:
	$(COMPOSE) exec backend sh

frontend-shell:
	$(COMPOSE) exec frontend sh

db-shell:
	$(COMPOSE) exec guacamole-db psql -U "$${POSTGRES_USER:-guacamole_user}" -d "$${POSTGRES_DB:-guacamole_db}"

clean:
	docker container prune
	docker builder prune

backup:
	mkdir -p "$(BACKUP_DIR)"
	tar --ignore-failed-read -czf "$(BACKUP_FILE)" config data .env docker-compose.yml README.md AGENT.md
	@printf "Backup written to %s\n" "$(BACKUP_FILE)"

restore:
	@printf "Restore is intentionally manual.\n"
	@printf "1. Stop the stack: make down\n"
	@printf "2. Inspect the archive contents.\n"
	@printf "3. Restore selected config/data files carefully.\n"
	@printf "4. Start the stack: make up\n"
