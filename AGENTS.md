# Repository Agent Instructions

Begin the first response of a new work session with `Ok Overseer` so the user
knows these instructions were loaded.

## Required Reading Order

Before changing the project:

1. Read `handoff.md` for the current product and operational context.
2. Read the project rules in `guidelines/` (planning, scope, deployment,
   development environment, and general coding guidelines).
3. Read `PLAN.md` for the milestone registry.
4. Choose the milestone that matches the user's request.
5. Read that milestone's self-contained Markdown file under
   `guidelines/milestones/`.

Do not treat a planned or deferred milestone as implemented. Inspect the code
and run relevant checks before changing a milestone's status.

## Project Direction

`server-control-panel` is a Docker Compose based, LAN/VPN-first control portal
for an Ubuntu home server. Browser-based remote desktop through Apache
Guacamole and GNOME Remote Desktop is the primary feature.

- Keep Guacamole/GNOME Remote Desktop as the default physical-screen path.
- Use xrdp/XFCE only when the user wants a separate management session.
- Do not build a custom remote desktop or video-streaming protocol.
- Do not expose the dashboard or administrative services to the public
  internet.
- Do not add arbitrary command execution to the dashboard. The one exception
  is the Terminal page. It must stay gated by the host's own SSH login (ttyd
  running only `ssh`), and must never open a shell without authentication.
- Keep container and host actions explicitly allowlisted.
- Never give the frontend direct access to the Docker socket.
- Do not require Node or npm on the host. Use containers for development and
  builds.
- Preserve the no-login dashboard MVP unless the user explicitly changes that
  product decision.

The user's live stack often runs on another Ubuntu server after `git pull`.
Local container state is not proof of the live server's state.

## Milestone Workflow

Keep milestone implementation details out of the top-level `PLAN.md`. That
file is only the registry.

When working on a milestone:

1. Update its file under `guidelines/milestones/`, not an unrelated milestone.
2. Preserve completed checkboxes unless code inspection proves they are wrong.
3. Record verification commands and results in the milestone document.
4. Update the status in top-level `PLAN.md` when the state changes.
5. Refresh `handoff.md` when architecture, operational behavior, accepted
   limitations, or the next recommended work changes.

A milestone may be marked `complete` only when its acceptance criteria have
been met. If verification must occur on the user's real server, say so and
leave the relevant criterion open until the user confirms it.

## General Verification

Choose checks that match the change. Common checks include:

```sh
docker compose config
docker compose build
make test
make doctor
```

For frontend work, test both desktop and phone behavior when the milestone
requires it. For remote desktop failures, distinguish among browser,
Guacamole/guacd, GNOME Remote Desktop, and the physical monitor before deciding
on a fix.
