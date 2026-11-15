# Phase 4 service and exports

This implements the service and artifact boundary in plan Part 5 and the
source-transmit timing and resource-history exports in Parts 3 and 4. It does
not implement renderer registration or a second physics model.

Start locally with `.venv/bin/uvicorn soma.api.app:app --host 127.0.0.1 --port 8000`.
Submit a complete frozen v0.1.0 scenario as the JSON body of `POST /plans`.
A 202 response contains `job_id` and the RFC 8785 `scenario_sha256`. Poll
`GET /plans/{job_id}` for queued, running, completed, failed, or canceled status.
Progress stages are validation, horizon_preparation, contact_construction,
scheduling, replay, and export. Fast stages may finish between polls. Failure is
a job failure, distinct from a scientific result of infeasible or unknown.

Each job runs in a fresh Python process using multiprocessing spawn. No parent
process loads SPICE on behalf of a worker, and no process is reused for a second
job. At most two jobs run concurrently by default. The app factory accepts a
trusted, spawn-picklable planner only at construction for testing; requests
cannot choose Python code, kernels, or filesystem paths through this option.
Worker output is written inside a private temporary directory, so a large
result cannot deadlock a multiprocessing message pipe. Progress messages use a
bounded queue. Application shutdown terminates unfinished jobs and removes
worker files.

`DELETE /plans/{job_id}` terminates queued or running work, waits at most two
half-second process joins, and records canceled with no result or export.
Repeated cancellation is harmless. A completed or failed job is immutable and
is returned unchanged when cancellation arrives too late. Scenario hashes stay
on all states so clients can reject stale results. GET responses are detached
snapshots. This local service has no persistent job database or external
service authentication and is intended for loopback use.

Bounds are two MB per request, eight MB per serialized worker run, sixteen MB
per package, 128 MB accounted retained result bytes, 300 seconds per worker,
and 32 retained jobs by default. Factory bounds permit up to eight concurrent
workers and 128 retained jobs. When retention is exhausted, new submissions
receive 429; restart the local service to clear the retained jobs. Requests
reject duplicate JSON keys, NaN, infinity, invalid UTF-8, and contract violations.
No cross-job scientific cache exists.

For a completed run, `GET /plans/{job_id}/export` returns its cached exact ZIP
bytes. `/summary` and `/display` expose read-only structured derivations.
The Python equivalent is `soma.exports.create_run_package(run)`. It expects
`scenario` and canonical `result`, and preserves `analysis_inputs`, independent
`validation` replay, and `details` when present. It verifies scenario identity
and the result schema, but does not replace independent scientific replay.

ZIP members are scenario.json, result.json, run-manifest.json, contacts.csv,
schedule.csv, energy.csv, buffer-history.csv, summary.json, display.czml, and
explanation.md, plus analysis-inputs.json and replay.json when supplied. Names,
ordering, ZIP metadata, JSON formatting, and newlines are deterministic. The
manifest hashes every member except itself, includes installed dependency
versions, complete result provenance and source URLs, and declares that a blank
CSV numeric cell means unknown. A numeric zero remains `0`.

CSV schedule rows preserve each exact source transmit interval, receiver
occupancy interval, byte availability time, byte offset, and byte length.
Contact rows preserve net payload rates and propagation seconds. Markdown is
generated from those structured fields, including storage intervals, final-byte
arrival, solver status, fidelity, assumptions, warnings, and planning details.
It makes no invented diagnosis of a sole limiting constraint. No kernels, DEMs,
restricted papers, or tiles are bundled.

CZML contains a document packet and metadata properties only. Allocation JSON
retains the original epochs; there is no interpolation or schedule resampling.
Positions are blocked pending the versioned Phase 5 frame registration. This
artifact must not be interpreted as registered lunar geometry.

Verification: `.venv/bin/pytest -q tests/engine/test_api.py tests/engine/test_exports.py`.
The tests exercise spawned process IDs, cancellation, retention, strict request
validation, snapshot isolation, cached downloads, package checksums, exact CSV
epochs, and preservation of unknown values. The production test submits a
16-byte variant of the synthetic relay fixture through the real plan_run
provider, requires completion within 40 seconds, and compares the returned
result and every exported member hash. Synthetic fixture outputs remain
assumed-rate software tests rather than lunar mission predictions.

Framework guidance was checked through Context7 against FastAPI's official
[lifespan](https://fastapi.tiangolo.com/advanced/events/),
[request](https://fastapi.tiangolo.com/reference/request/), and
[test lifespan](https://fastapi.tiangolo.com/advanced/testing-events/) docs.
