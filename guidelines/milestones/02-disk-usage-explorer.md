# Milestone 02 — Disk usage explorer

## Objective

Let the user see what takes up space on each drive from the Status page, and
drill down folder by folder.

## Dependencies

None. Uses the existing drive discovery in `backend/app/system_info.py`.

## Existing-state check

Before implementation:

1. Inspect `backend/app/disk_usage.py`, `GET /api/disk-usage`, the backend
   `/host-root` mount in `docker-compose.yml`, and the `DiskUsagePanel` in
   `frontend/src/pages/HomePage.tsx`.
2. Evaluate every completion criterion below and preserve what already works.
3. Implement only what is missing.

Do not read other milestone files unless strictly necessary.

## Scope

- Backend: `disk_usage.py`, models, route, `host_path` on `DiskStats`
- `docker-compose.yml`: read-only `/` → `/host-root` bind (rslave) and
  `HOST_MEDIA_HOST_ROOTS`
- Frontend: Disk usage panel, API client, styles
- `backend/tests/`, `make test`

Out of scope: deleting or moving files, background indexing, and persistent
scan history.

## Required work

- `GET /api/disk-usage?path=<host path>&refresh=<bool>` returns the folder's
  size and its direct children, largest first, with sizes in bytes allocated
  (`du --one-file-system`).
- Other filesystems mounted below the folder are listed as `is_mount` entries
  with their used bytes, so another drive can be opened separately.
- Paths are normalized. Symlinks that resolve outside the host mount,
  `/proc`, and `/sys` are refused, and missing folders return 404.
- One scan runs at a time. Results are cached for 10 minutes. A scan times
  out after 5 minutes with a clear message.
- At most 200 entries are returned. The rest are summarized as a count and a
  size.
- Status page: drive buttons, breadcrumb, up button, size bars, rescan, and a
  "separate drive" marker. The panel never scans automatically on page load.

## Completion criteria

- [x] `make test` passes (ordering, normalization, unsafe paths, cache)
- [x] `/api/disk-usage?path=/` on this dev machine lists `/home`, `/var`, `/usr`, … and marks `/tmp` and `/run` as mounts (took 13 s for 72 GB)
- [x] `/proc` returns 400 and a missing folder returns 404
- [x] Panel drill-down (`/` → `/var`) renders on desktop and phone without horizontal overflow
- [X] User confirms extra drives under `/mnt` or `/run/media` open from their drive buttons on the real server

## Verification

- `make test` → 4 tests OK.
- Isolated verification stack (see milestone 01): `curl` against
  `/api/disk-usage` for `/`, `/home`, `/proc`, and `/nope`.
- Playwright clicked Main drive → `var` at 1280 px and 390 px widths.
