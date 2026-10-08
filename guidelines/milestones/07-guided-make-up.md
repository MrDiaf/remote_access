# Milestone 07 — `make up` sets up everything

## Objective

A fresh server needs only `make up`. It creates `.env`, starts the stack, and
then asks the user about each one-time host step that is still missing,
instead of the user hunting through the README for separate commands.

## Dependencies

Builds on Milestone 03 (one-command lifecycle) and Milestone 06 (Steam
control). On 2026-10-09 the user overrode Milestone 03's "do not install host
packages or change systemd settings from the Makefile". Such steps are now
allowed, but only behind an explicit `[Y/n]` prompt, and with `sudo` asking for
the user's own password.

## Existing-state check

1. Inspect `scripts/setup-host.sh`, the `env`, `up`, `preflight`, and
   `setup-host` targets in the `Makefile`, and the README "First-Time Setup".
2. Evaluate the criteria below and implement only what is missing.

## Design

`make up` → `env` (create `.env` if missing) → preflight → build and start →
`scripts/setup-host.sh` → `apply-remote-input` → print URLs.

`setup-host.sh` steps. Each checks its state first and prints `ok` when the
step is done:

| Step | Done when | Action after "yes" |
| --- | --- | --- |
| docker-boot | `systemctl is-enabled docker` | `sudo systemctl enable docker` |
| ssh-server | something listens on `TERMINAL_SSH_PORT` | `sudo apt-get install openssh-server` and enable it |
| physical-screen | `grdctl status` shows RDP enabled | prompts for a login, then `enable-gnome-physical-rdp.sh` (`RDP_USERNAME`/`RDP_PASSWORD` env) |
| guacamole-connection | any RDP row in `guacamole_connection` | inserts "Ubuntu Physical Desktop" with `guacadmin` permissions |
| guacamole-password | `guacadmin` hash no longer matches `guacadmin` | new salt and SHA-256 hash, the way Guacamole stores them |
| steam-control | key and `authorized_keys` line exist (offered only if Steam is installed) | `enable-steam-control.sh` |

- Secrets are passed to psql through `docker compose exec -e NAME` (the value
  comes from the environment) and psql `\getenv`. They never appear on a
  command line or in output.
- An "n" answer goes into `data/host-setup.skip` (gitignored), so `make up`
  does not nag. `make setup-host` sets `SETUP_HOST_ASK_ALL=1` and asks
  everything again.
- Without a TTY, nothing is asked; missing steps print `todo`.
- GNOME automatic login is only pointed out, never changed, because it is a
  security trade-off in GDM's config.

## Completion criteria

- [x] `make env` creates `.env` (mode 600, random password) once and never overwrites it
- [x] Without a TTY, `setup-host.sh` only reports and reflects this machine's real state
- [x] With answers, it creates a working Guacamole connection and changes the
      `guacadmin` password (Guacamole 1.6.0 accepts the new password and rejects the old one)
- [x] "n" is remembered, and a later run shows `skipped`
- [x] `make test` still passes
- [ ] On the real server, after `git pull`, one `make up` in a terminal finishes setup
      and the phone reaches the desktop through Guacamole

## Verification

- Non-interactive run here: docker-boot, ssh-server, physical-screen, and
  guacamole-connection `ok`; guacamole-password and steam-control `todo`.
- Disposable `postgres:16-alpine` loaded with the generated `initdb.sql`,
  driven through `script` with answers. The connection parameters were stored
  exactly, including a password with `'`, space, `$`, and `\`. `guacadmin`
  READ/UPDATE/DELETE/ADMINISTER were granted. A disposable
  `guacamole/guacamole:1.6.0` returned HTTP 200 for the new password and 403
  for `guacadmin`. A second run printed `ok` for both, and `skipped` for the
  declined Steam step.
- `make build`, `make test`: 13 backend and 12 TUI tests OK.
- The sudo steps were not exercised here (already done on this machine).
