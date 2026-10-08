# Every target works on the whole project, including the Guacamole services
# that live in the "remote" Compose profile.
# docker-compose.gpu.yml lets the backend report NVIDIA GPU usage. It is added
# only when Docker has the NVIDIA runtime, since the GPU request fails without it.
GPU_COMPOSE := $(shell docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q nvidia && echo "-f docker-compose.yml -f docker-compose.gpu.yml")
COMPOSE ?= docker compose $(GPU_COMPOSE) --profile remote
GUACAMOLE_VERSION ?= 1.6.0
BACKUP_DIR ?= backups
BACKUP_FILE ?= $(BACKUP_DIR)/server-control-panel-$$(date +%Y%m%d-%H%M%S).tar.gz

.PHONY: help setup env setup-host up tui down shutdown maintenance-stop refresh restart build logs ps status doctor test preflight remote-up remote-down apply-remote-input guacamole-init check-remote install-host-remote-desktop enable-physical-screen enable-steam-control data-dirs backend-shell frontend-shell db-shell clean backup restore

help:
	@printf "server-control-panel commands\n\n"
	@printf "Everyday\n"
	@printf "  make up                Set up and start everything; asks about any host step still missing\n"
	@printf "  make down              Stop everything (keeps all data)\n"
	@printf "  make status            Show container status\n"
	@printf "  make doctor            Check boot autostart, terminal SSH, and remote desktop\n"
	@printf "  make logs              Follow logs\n"
	@printf "  make tui               Open the terminal UI (every dashboard feature, no browser)\n\n"
	@printf "After git pull / troubleshooting\n"
	@printf "  make refresh           Rebuild and force-recreate dashboard containers\n"
	@printf "  make restart           Restart all containers\n"
	@printf "  make build             Rebuild images\n"
	@printf "  make check-remote      Check only the Guacamole -> RDP path\n"
	@printf "  make apply-remote-input  Apply saved keyboard setting to Guacamole RDP connections\n"
	@printf "  make remote-up         Start only Guacamole, guacd, and PostgreSQL\n"
	@printf "  make remote-down       Stop only the Guacamole stack\n"
	@printf "  make test              Run backend and TUI tests in containers\n\n"
	@printf "Single setup steps (make up already offers these)\n"
	@printf "  make setup-host        Ask again about every host step, even ones you skipped\n"
	@printf "  make setup             Only create .env and the Guacamole schema\n"
	@printf "  make enable-physical-screen  Share the logged-in GNOME monitor over RDP\n"
	@printf "  make enable-steam-control    Let the dashboard start and quit Steam\n\n"
	@printf "Other\n"
	@printf "  make install-host-remote-desktop  Install xrdp + XFCE (separate session, uses sudo)\n"
	@printf "  make guacamole-init    Generate Guacamole PostgreSQL init schema\n"
	@printf "  make backend-shell     Open a shell in the backend container\n"
	@printf "  make frontend-shell    Open a shell in the frontend container\n"
	@printf "  make db-shell          Open psql in the Guacamole database container\n"
	@printf "  make clean             Remove stopped containers and build cache (asks first)\n"
	@printf "  make backup            Archive config, data, and .env\n"
	@printf "  make restore           Print restore guidance\n"

setup:
	@if [ -f .env ]; then printf ".env already exists; leaving it unchanged.\n"; fi
	@$(MAKE) --no-print-directory env guacamole-init
	@printf "\nNext: make up\n"

# Create .env with a random database password; never overwrites it.
env:
	@if [ ! -f .env ]; then \
		password=$$(LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32); \
		sed "s/^POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$$password/" .env.example > .env; \
		chmod 600 .env; \
		printf "Created .env with a random POSTGRES_PASSWORD.\n"; \
	fi

preflight: env
	@command -v docker >/dev/null 2>&1 || { \
		printf "Docker is required. Install Docker Engine with the Compose plugin, then retry.\n" >&2; exit 1; }
	@docker info >/dev/null 2>&1 || { \
		printf "Docker is installed but not reachable.\n" >&2; \
		printf "Start it with: sudo systemctl enable --now docker\n" >&2; \
		printf "and make sure your user is in the docker group.\n" >&2; exit 1; }
	@docker compose version >/dev/null 2>&1 || { \
		printf "The Docker Compose plugin is required (docker compose ...).\n" >&2; exit 1; }
	@[ -f .env ] || { printf ".env is missing. Run: make setup\n" >&2; exit 1; }
	@if grep -q '^POSTGRES_PASSWORD=replace-with' .env; then \
		printf "warning: POSTGRES_PASSWORD in .env is still the example value.\n" >&2; \
	fi

up: preflight guacamole-init data-dirs
	$(COMPOSE) up -d --build --wait --wait-timeout 180
	@-COMPOSE_CMD="$(COMPOSE)" ./scripts/setup-host.sh
	@-$(MAKE) --no-print-directory apply-remote-input
	@port=$$(sed -n 's/^DASHBOARD_HTTP_PORT=//p' .env | tail -n 1); port=$${port:-8080}; \
	ip=$$(hostname -I 2>/dev/null | awk '{print $$1}'); ip=$${ip:-localhost}; \
	printf "\nserver-control-panel is running.\n\n"; \
	printf "  Dashboard:  http://%s:%s\n" "$$ip" "$$port"; \
	printf "  Terminal:   http://%s:%s/#terminal\n" "$$ip" "$$port"; \
	printf "  Guacamole:  http://%s:%s/guacamole/\n\n" "$$ip" "$$port"; \
	printf "Containers start again by themselves after a reboot.\n"; \
	printf "Run 'make doctor' to check that the whole server is ready for that.\n"

# make up runs this too, but it skips steps you answered "no" to before.
setup-host: preflight data-dirs
	@SETUP_HOST_ASK_ALL=1 COMPOSE_CMD="$(COMPOSE)" ./scripts/setup-host.sh

tui: preflight
	@port=$$(sed -n 's/^DASHBOARD_HTTP_PORT=//p' .env | tail -n 1); port=$${port:-8080}; \
	ip=$$(hostname -I 2>/dev/null | awk '{print $$1}'); ip=$${ip:-localhost}; \
	SCP_DASHBOARD_URL="http://$$ip:$$port" $(COMPOSE) --profile tui run --rm --build tui

down:
	$(COMPOSE) down

shutdown maintenance-stop: down

refresh: preflight guacamole-init data-dirs
	$(COMPOSE) up -d --build --force-recreate --wait --wait-timeout 180 frontend backend terminal reverse-proxy
	$(COMPOSE) up -d --wait --wait-timeout 180
	@-$(MAKE) --no-print-directory apply-remote-input
	@printf "Refresh complete. Hard-refresh the browser if an old asset is still cached.\n"

restart:
	$(COMPOSE) restart

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f --tail=200

ps status:
	$(COMPOSE) ps

doctor:
	@./scripts/check-host.sh
	@./scripts/check-remote-desktop.sh

test: data-dirs
	$(COMPOSE) run --rm --no-deps -v $(CURDIR)/backend/tests:/app/tests:ro backend python -m unittest discover -s tests -v
	$(COMPOSE) --profile tui run --rm --build --no-deps -v $(CURDIR)/tui/tests:/app/tests:ro tui python -m unittest discover -s tests -v

remote-up: guacamole-init
	$(COMPOSE) up -d --wait --wait-timeout 180 guacamole-db guacd guacamole

remote-down:
	$(COMPOSE) stop guacamole guacd guacamole-db

apply-remote-input:
	COMPOSE_CMD="$(COMPOSE)" sh ./scripts/apply-guacamole-input-settings.sh

guacamole-init:
	@mkdir -p data/guacamole
	@if [ -d data/guacamole/initdb.sql ]; then \
		printf "data/guacamole/initdb.sql is a directory; remove it and rerun make guacamole-init\n" >&2; \
		exit 1; \
	elif [ -s data/guacamole/initdb.sql ]; then \
		:; \
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
			chmod 644 "$$tmp"; \
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

enable-steam-control: data-dirs
	./scripts/enable-steam-control.sh

# Bind-mount sources must exist first, or Docker creates them owned by root.
data-dirs:
	@mkdir -p data/steam-control

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
	tar --ignore-failed-read -czf "$(BACKUP_FILE)" config data .env docker-compose.yml README.md AGENTS.md PLAN.md handoff.md guidelines
	@printf "Backup written to %s\n" "$(BACKUP_FILE)"

restore:
	@printf "Restore is intentionally manual.\n"
	@printf "1. Stop the stack: make down\n"
	@printf "2. Inspect the archive contents.\n"
	@printf "3. Restore selected config/data files carefully.\n"
	@printf "4. Start the stack: make up\n"
