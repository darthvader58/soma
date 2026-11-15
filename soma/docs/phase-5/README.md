# Phase 5 integration handoff

The live numerical workflow and the regional map-alignment gate now pass.
The engine reverses the observed ingestion conversion in the official Cesium
Moon v6 mesh and publishes a versioned identity bridge to the corrected static
representation. Four source-selected terrain features match within the declared
10 m relative display tolerance at the tested grid resolution. See
[map-alignment.md](map-alignment.md) for the method, measurements and limits.
The raw asset remains unregistered. Phase 6 begins only after the integrated
changes are merged by the repository owner.

## Start the integrated application

Install the Python extras listed in the root README and run two terminals from
the repository root:

```sh
.venv/bin/uvicorn soma.api.app:app --host 127.0.0.1 --port 8000
```

```sh
npm --prefix web ci
npm --prefix web run dev
```

Open `http://127.0.0.1:5173/`. Vite proxies `/api` to the loopback service. The
preview server uses the same proxy; a deployed static build needs an equivalent
same-origin reverse proxy. `SOMA_API_PROXY_TARGET` changes the server-side target;
`VITE_SOMA_API_URL` changes the browser base URL. The verified local setup needs
no permissive CORS policy.

Choose a declared network and **Plan delivery**. The result is calculated by
Python for that exact scenario hash. A failed request never substitutes a
captured result. Offline inspection is explicit:

```sh
VITE_SOMA_MODE=fixture npm --prefix web run dev
```

`web/.env.local` is ignored by Git. A scoped Cesium application token can enable
the optional Moon terrain. In the configured local workspace it is restricted
to read access for asset 2684829 and the documented local development/preview
URLs. It is excluded from run packages, manifests and source commits. Use the
exact configured local URL; a different hostname/port needs corresponding token
URL access. A working token establishes access, not scientific registration.

## Immutable display and export boundary

Completed jobs expose `/plans/{id}/display-data` and
`/plans/{id}/renderer-registration` in addition to the native result, summary,
CZML and exact ZIP. The ZIP contains the same `display-data.json` and
`renderer-registration.json` values, plus the pinned `renderer-conversion.json` parameters. The service caches them at completion;
later source/manifest edits cannot change a completed job.

Display format 0.5.0 binds scenario ID/hash, run version and model fidelity. It
copies exact contacts, allocations, storage, energy and buffer records and the
engine's environment diagnostic. No display sampling moves schedule epochs,
recalculates metrics or replaces unknown values with zero. The browser checks
that those fields equal its completed native result and invalidates late
artifacts on cancel or edit. Numerical output/download remains usable when a
display artifact is unavailable.

The source relay fixture explicitly supplies contact windows **without a
trajectory or ephemeris**. Therefore the display contains no spacecraft states,
and the selected-time readout says Unknown. It reads exact stored battery and
buffer records at matching epochs; unsupported times remain unknown. No orbit
was fabricated to animate the chosen contact schedule. A later supported state
source must identify origin, frame, epoch, time scale, units and provenance and
pass registration before an asset can appear as scientific geometry.

## Evidence and acceptance boundary

Current verification commands are listed below; the final counts and capture hashes are recorded in `data/phase5-evidence.manifest.json`. The earlier integration verification includes four live
Chromium checks and seventeen fixture Chromium checks; this diagnostic change
does not modify product UI code. A fresh
CLI replay of the downloaded relay run passes with zero errors and 104,857,600
unique delivered bytes. No engine tests were skipped. Existing pinned-library
deprecation warnings remain visible in test output.

The live Chromium suite starts the actual FastAPI service and Vite proxy. It
calculates the 100 MiB direct failure and relay success, compares the displayed
result to the completed job, checks every schedule CSV epoch and ZIP member hash,
and verifies that time scrubbing sends no new planning request. A 16-byte edit
is genuinely rescheduled; an unsupported site returns unknown. Real running jobs
are canceled, and an older job cannot overwrite the newer scenario.

```sh
.venv/bin/python -m pytest tests/engine -q
npm --prefix web test
npm --prefix web run build
npm --prefix web run test:live
npm --prefix web run test:browser
```

`SOMA_BROWSER_EXECUTABLE` can select an installed compatible Chromium. Fixture
browser checks explicitly disable token access and select offline mode; live
checks use their own loopback ports with the real engine. The token-backed
Moon was also inspected separately through Aside. This distinguishes missing-map
resilience from actual asset access.

See [registration.md](registration.md) for the handoff contract and
[map-alignment.md](map-alignment.md) for the measured evidence. The earlier
[source audit](registration-source-audit.md) preserves the raw asset discrepancy
and sampler calibration; it is historical evidence, not the current gate.
The [interface verification](../../../web/docs/phase-5-verification.md) records
interaction checks and the delivery gate. The recorded live export under
`fixtures/phase-5/` permits independent replay without browser state; its older
registration file documents the state when that run was produced. New runs
export the current certificate and conversion without rewriting old results.

All delivery examples remain synthetic, assumed-rate planning calculations.
Real LOLA horizon gaps remain unknown. No booking, flight certification,
thermal-survival, universal site-ranking or absolute-navigation claim is made.
A registered map does not make an unsupported numerical terrain sample known.
