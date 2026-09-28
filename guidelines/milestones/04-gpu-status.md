# Milestone 04 — GPU usage on the Status page

## Objective

Show GPU utilization and GPU memory (VRAM) next to CPU and RAM on the Status
page.

## Dependencies

None. Extends `GET /api/system` in `backend/app/system_info.py`.

## Scope

- Backend: `GpuStats` model, `gpus` on `SystemInfo`, `nvidia-smi` reader
- `docker-compose.gpu.yml`: grants the backend the NVIDIA GPU (`utility`
  capability, which injects `nvidia-smi` and NVML)
- `Makefile`: adds the override only when `docker info` lists the `nvidia`
  runtime
- Frontend: one GPU stat card per GPU, API client type
- `backend/tests/test_gpu_stats.py`

Out of scope: AMD/Intel GPUs, per-process GPU usage, history graphs.

## Accepted limitations

- NVIDIA only, and only with the NVIDIA Container Toolkit installed. Without
  it the card is hidden and everything else works. AMD could be added later
  from sysfs (`gpu_busy_percent`, `mem_info_vram_*`) if the server has one.
- Plain `docker compose up` does not include the override; use `make up`.

## Completion criteria

- [x] `make test` passes (nvidia-smi parsing, `[N/A]` values skipped)
- [x] With the override, the backend container reads the RTX 3060 on this machine
- [x] Without the override, `gpus` is empty and the card is hidden
- [ ] User sees the GPU card on the real server after `make up`

## Verification

- `make test` → 6 tests OK.
- `docker compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm --no-deps backend python -c '…_gpu_stats()'`
  → `NVIDIA GeForce RTX 3060, 2%, 776 MiB / 12 GiB`; without the override → `[]`.
- Frontend image builds (`tsc && vite build`).
