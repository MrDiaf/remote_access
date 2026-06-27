COMPOSE ?= docker compose
GUACAMOLE_VERSION ?= 1.6.0
BACKUP_DIR ?= backups
BACKUP_FILE ?= $(BACKUP_DIR)/server-control-panel-$$(date +%Y%m%d-%H%M%S).tar.gz

.PHONY: help up down shutdown maintenance-stop refresh restart build logs ps remote-up remote-down apply-remote-input guacamole-init check-remote install-host-remote-desktop enable-physical-screen backend-shell frontend-shell db-shell clean backup restore

help:
	@printf "server-control-panel commands\n\n"
	@printf "  make up                Start dashboard, backend, proxy, and Portainer\n"
	@printf "  make down              Stop the default stack\n"
	@printf "  make shutdown          Gracefully stop dashboard and remote desktop stacks\n"
	@printf "  make refresh           Rebuild/recreate dashboard and refresh remote helpers\n"
	@printf "  make restart           Restart the default stack\n"
	@printf "  make build             Rebuild images\n"
	@printf "  make logs              Follow logs\n"
	@printf "  make ps                Show container status\n"
	@printf "  make remote-up         Start Guacamole, guacd, and PostgreSQL\n"
	@printf "  make remote-down       Stop the Guacamole remote desktop stack\n"
	@printf "  make apply-remote-input  Apply saved keyboard setting to Guacamole RDP connections\n"
	@printf "  make guacamole-init    Generate Guacamole PostgreSQL init schema\n"
	@printf "  make check-remote      Check Guacamole and host RDP readiness\n"
	@printf "  make install-host-remote-desktop  Install xrdp + XFCE on Ubuntu/Debian host\n"
	@printf "  make enable-physical-screen       Share the logged-in GNOME monitor over RDP\n"
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

shutdown: maintenance-stop

maintenance-stop:
	@printf "Stopping Guacamole remote desktop stack...\n"
	$(COMPOSE) --profile remote stop guacamole guacd guacamole-db
	@printf "Stopping default dashboard stack...\n"
	$(COMPOSE) down
	@printf "All project services are stopped for maintenance.\n"

refresh: guacamole-init
	@printf "Rebuilding and recreating dashboard containers...\n"
	$(COMPOSE) up -d --build --force-recreate frontend backend reverse-proxy
	@printf "Starting remote desktop containers...\n"
	$(COMPOSE) --profile remote up -d guacamole-db guacd guacamole
	$(MAKE) apply-remote-input
	@printf "Refresh complete. Hard-refresh the browser if an old asset is still cached.\n"

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

apply-remote-input:
	COMPOSE_CMD="$(COMPOSE)" sh ./scripts/apply-guacamole-input-settings.sh

guacamole-init:
	mkdir -p data/guacamole
	@if [ -d data/guacamole/initdb.sql ]; then \
		printf "data/guacamole/initdb.sql is a directory; remove it and rerun make guacamole-init\n" >&2; \
		exit 1; \
	elif [ -s data/guacamole/initdb.sql ]; then \
		printf "data/guacamole/initdb.sql already exists\n"; \
	else \
		if [ -f data/guacamole/initdb.sql ]; then \
			printf "data/guacamole/initdb.sql exists but is empty; regenerating\n"; \
		fi; \
		tmp=$$(mktemp data/guacamole/initdb.sql.XXXXXX); \
		if docker run --rm guacamole/guacamole:$(GUACAMOLE_VERSION) /opt/guacamole/bin/initdb.sh --postgresql > "$$tmp"; then \
			if [ ! -s "$$tmp" ]; then \
				printf "Generated Guacamole schema is empty\n" >&2; \
				rm -f "$$tmp"; \
				exit 1; \
			fi; \
			mv "$$tmp" data/guacamole/initdb.sql; \
		else \
			rm -f "$$tmp"; \
			exit 1; \
		fi; \
		printf "Generated data/guacamole/initdb.sql\n"; \
	fi

check-remote:
	./scripts/check-remote-desktop.sh

install-host-remote-desktop:
	sudo ./scripts/install-xrdp-xfce-ubuntu.sh

enable-physical-screen:
	./scripts/enable-gnome-physical-rdp.sh

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
