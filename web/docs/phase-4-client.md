# Phase 4 jobs, schedule text and run-package client

The browser consumes the six frozen v0.1.0 schemas and engine-supplied records.
It performs no visibility, power, routing or schedule calculation. The existing
visual draft in `design.md` remains in effect: ENERGY 1 / RHYTHM 1 / MOTION 1.
Precise schedules and text labels use the established table and timeline styles.

## Public client API

Both `createPlanClient(options)` and `createFixtureClient(fixtures, options)`
expose:

- `plan(scenario, {onProgress})`: validates a detached scenario, hashes it and
  returns a deeply frozen, schema-validated result with that exact hash.
- `cancel()`: invalidates callbacks and clears completed downloads and retries.
  The live client also aborts the request and deletes known active jobs.
- `retry({onProgress})`: resubmits only the detached snapshot retained from the
  last failed request. Canceling or starting a new plan clears that snapshot.
  The caller must invoke `cancel()` when an input edit invalidates the scenario.
- `exportRun(scenario)`: returns `{bytes: Uint8Array, filename, fixture}` for
  the most recent validated completion with exactly that scenario hash.

Live options remain `baseUrl`, `fetchImpl` and `pollIntervalMs`. The service
protocol is POST `/plans` returning `job_id`, GET `/plans/{id}` returning
`status`, `stage`, `scenario_sha256` and a canonical result at completion, and
DELETE `/plans/{id}` canceling avoidable work. Supplied stages are forwarded
without invented computation: validation, horizon preparation, contact
construction, scheduling, replay and export are engine responsibilities.

Superseding a request deletes its accepted active job. If a superseded POST
later returns an identifier despite request abortion, the client deletes that
orphan before returning AbortError. Stale progress and results cannot publish.
The completed job identifier is retained separately from the polling request,
so finishing its `finally` block does not erase the export reference.

Fixture options are `{fetchImpl, fixtureDelayMs: 0}`. Nonzero fixture delay is
an explicitly labeled delayed-test stage that says no scientific computation
is running. It supports controlled cancellation tests without pretending to
perform horizon preparation or optimization. Fixtures may provide `packageUrl`
or `packageBytes`; bytes are copied at the boundary to prevent mutation of the
captured package. Edited scenarios require another captured exact hash or the
live service. The client computes no replacement result.

## Exact package download

The live export fetches GET `/plans/{completed_job_id}/export`. Fixture export
fetches its declared package URL or copies its captured bytes. `arrayBuffer()`
becomes a `Uint8Array` without JSON serialization or CSV/ZIP reconstruction.
If the response supplies `X-SOMA-Scenario-SHA256`, it must match the submitted
scenario hash. Export completion rechecks that the artifact is still current;
a canceled or superseded download cannot be presented as the current run.
The package remains authored by Python, including all provenance and checksums.
The client does not claim that optional response metadata independently proves
archive content or scientific validity.

## Structured interpretation

`explainResult(result)` reads only canonical provenance, contacts, allocations,
storage and delivery fields. It names sender and receiver identifiers, each
chunk's range, exact source transmit interval, exact receiver payload interval,
byte availability, supplied storage interval and final-byte arrival. A missing
reason remains Unknown; no terrain, battery or causality explanation is
invented from an empty allocation list or speculative summary fields.

Solver status and model fidelity stay next to delivery status. Assumed-rate
simulation also has a visible sentence preserving the rate/service qualification
for feasible results. Unused contacts say their reason is Unknown because the
frozen contact contract supplies no rejection-reason field. The separate hand
calculation remains explicitly synthetic and separate from the engine result.

The timeline shows engine contact source windows with the established dashed
available style, source and receiver allocation intervals with the solid
selected style, and supplied storage reservations. Matching source-reference
contacts are suppressed by identifier to avoid duplicate opportunity rows.
No allocation is inferred from a contact. Exact supplied epoch strings remain
visible even though timeline bar positions are display proportions.

## Verification and limits

`node --test tests/web/client.test.mjs tests/web/result.test.mjs`: 17 passed.
The complete `npm test` run from `web/`: 49 passed. `npm run build` passes.
Controlled transport tests cover late POST deletion, superseded accepted jobs,
explicit delayed-fixture cancellation, immutable retry, nested result freezing,
exact raw package bytes, header/hash rejection, stale export rejection and
invalid result rejection before progress publication. Structured explanation
tests preserve microsecond text and ignore unapproved summary fields.

This bounded client change adds no colors, icons, motion or new controls.
Existing scrollable tables, text status and native timeline control remain.
The owner's browser workflow must verify the newly wired controls and rendered
schedule at desktop/mobile sizes, including missing-map fallback, and capture
visual evidence. This document does not claim a live integrated Phase 5 run,
validated Moon registration, operational relay service, or mission prediction.
