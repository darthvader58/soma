# Vercel research compute and optional local reproduction

The public workbench and its Python geometry API run on Vercel. No second hosting provider or external compute service is required by this slice. The browser calls same-origin `/api/research/catalog`, `/api/research/capabilities` and `POST /api/research/analyze`.

The Vercel build runs `scripts/prepare-research-data.py` to fetch pinned scientific sources into the function-private `api/_data` directory. Every file must match its recorded size and SHA256 before the build succeeds. The four-role DE421 set supplies Sun/Earth geometry. An optional pinned LRO source adds only its recorded historical interval and does not imply relay service. Scientific files are bundled with the Python function, outside the public `web/dist` output; requests never fetch missing kernels or fabricate replacement results.

The hosted adapter reports `service_mode: serverless`, `async_available: false` and `persistence.kind: none`. Job submission, polling, cancellation and job exports return HTTP 503 because a Vercel invocation does not supply durable job storage. The synchronous endpoint returns the scientific result directly. Browser exports use that exact result and normalized request.

Hosted limits are 128,000 request bytes, one active synchronous calculation per function process, a 60-second worker wall-time cap and a 4,000,000-byte result cap. Each calculation runs in a spawned process with its own SPICE kernel pool. The synchronous worker uses no multiprocessing queues or semaphores, so it does not require shared-memory filesystems. Linux workers have a 1.5 GiB virtual-address limit. The adapter forces native numerical thread counts to one before importing NumPy and before spawning workers, including when the host supplies a larger default. No manual Vercel thread configuration is required. A disconnected caller is not guaranteed to cancel work; the server deadline still applies. Over-budget requests fail explicitly and should reduce epochs/sites. Arrays are never truncated to fit.

`GET /api/research/capabilities` checks local source hashes and actual binary coverage. Missing or invalid sources produce an unavailable state. Core readiness and each spacecraft profile's availability are separate. Existing Cesium asset access still uses its server-only token and configured public origin; those credentials are unrelated to scientific kernel access.

## Optional local service

The library also supports a local durable job store for reproducible research on the user's own computer. This is independent of the Vercel application and is not an external hosting recommendation.

```sh
python3 -m pip install -r requirements-research.txt '.[analysis,planning,service]'
python3 scripts/prepare-research-data.py --output /private/tmp/soma-research-sources
SOMA_DATA_ROOT=/private/tmp/soma-research-sources \
SOMA_RESEARCH_RUN_ROOT=/private/tmp/soma-research-runs \
SOMA_RESEARCH_ALLOWED_ORIGINS=http://localhost:5173 \
uvicorn soma.api.app:app --host 127.0.0.1 --port 8000 --workers 1
```

Local routes use `/research` instead of `/api/research`; health check is `GET /health`. Set `SOMA_RESEARCH_RUN_ROOT` to enable durable jobs. Use one Uvicorn process per store. Startup refuses a second owner of the same volume. `POST /research/jobs` returns a job ID and study hash; poll `GET /research/jobs/{id}`, cancel queued/running work with `DELETE /research/jobs/{id}`, and export completed jobs with `GET /research/jobs/{id}/export`.

The ZIP contains exact study/result JSON and a checksum manifest. Requests, progress stages and completed artifacts are persisted in SQLite. Complete artifacts are committed in one transaction and remain identical after restart. Interrupted queued/running jobs become `failed` with stage `interrupted`; they never become fabricated completed jobs.

Local defaults are one asynchronous worker, 32 retained jobs, 16,000,000 result bytes, 32,000,000 export bytes and 128,000,000 retained logical artifact bytes. Workers have a 300-second wall-time bound. Completed/canceled/failed jobs expire after seven days, pruned on startup/submission. SQLite can retain reusable free pages after expiry. A full store rejects submissions with HTTP 429 until retention permits pruning. The store survives service restarts when its directory survives; it does not survive deletion of that directory.

For optional local container reproduction:

```sh
docker build -f Dockerfile.research -t soma-research-local .
docker volume create soma-research-local-data
docker run --name soma-research-local --init --memory 2g --cpus 2 \
  -p 127.0.0.1:8000:8000 \
  --mount source=soma-research-local-data,target=/data \
  -e SOMA_RESEARCH_ALLOWED_ORIGINS=http://localhost:5173 \
  soma-research-local
```

The image seeds verified sources into `/data/sources` and stores SQLite jobs under `/data/runs`. A changed source hash requires an explicit source/image update; startup rejects conflicting persistent source bytes. The Docker image is an optional local tool and is not deployed by the Vercel workflow.
