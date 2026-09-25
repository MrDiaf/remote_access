# Milestone 03 — One-command setup and reboot recovery

## Objective

Make a fresh install and a server restart need as few steps as possible, and
document them in the README.

## Dependencies

None.

## Existing-state check

Before implementation:

1. Inspect the `Makefile`, `scripts/check-host.sh`, and the README sections
   "First-Time Setup", "Everyday Use", and "After A Reboot".
2. Evaluate every completion criterion below and preserve what already works.
3. Implement only what is missing.

Do not read other milestone files unless strictly necessary.

## Scope

`Makefile`, `scripts/check-host.sh`, `README.md`, `.env.example`, and
`handoff.md`.

Out of scope: installing host packages automatically, changing GDM or systemd
settings from the Makefile, and systemd units for the stack. Docker restart
policies already cover restarts.

## Required work

- `make setup` creates `.env` from `.env.example` with a random
  `POSTGRES_PASSWORD` (mode 600) and never overwrites an existing `.env`. It
  also generates the Guacamole schema.
- `make up` checks prerequisites with clear messages, then starts **all**
  services (including the `remote` profile), waits for them to be healthy,
  applies the saved keyboard layout, and prints the URLs. It is safe to repeat.
- `make down` stops all services, including the Guacamole stack, without
  deleting volumes.
- `make doctor` (read-only) checks Docker on boot, the container restart
  policies, host sshd and reachability from the terminal container, GNOME
  automatic login, and gnome-remote-desktop. It then runs `check-remote`.
- The generated `initdb.sql` must be readable by the Postgres container.
- The README explains what happens after a reboot and what the user must
  configure once (Docker enabled, GNOME automatic login).

## Completion criteria

- [x] `make help` lists only existing commands, grouped by first-time, everyday, and troubleshooting
- [x] `make setup` in a clean copy creates `.env` (mode 600, random password) and `initdb.sql` (mode 644); a second run leaves `.env` unchanged
- [x] A Postgres 16 container initializes the Guacamole schema from that `initdb.sql`
- [x] `make preflight` passes here and warns about the example DB password
- [x] `make doctor` runs on this machine and reports every section
- [ ] `make up` on the real server starts all 8 containers and prints the URLs
- [ ] After a real reboot of the server, the dashboard, terminal, and Guacamole come back without running `make`

## Verification

- `make help`, `make -n up`, `make preflight`, and `make setup` (existing and
  fresh copy).
- A disposable `postgres:16-alpine` container loaded the generated
  `initdb.sql`; `select count(*) from guacamole_user` returned `1`.
- `make doctor` on the dev machine: Docker enabled at boot, 7 of 8 containers
  running (`scp-terminal` not yet created), sshd listening, GNOME automatic
  login and gnome-remote-desktop enabled, and RDP reachable from guacd.
- `make up` was not run on this machine, to avoid recreating the user's
  running containers.
