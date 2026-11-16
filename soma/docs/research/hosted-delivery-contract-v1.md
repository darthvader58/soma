# Hosted delivery transport, version 1.0.0

This transport exposes the existing native `0.1.0` planning contract. It does not
change a scientific schema or create a second scheduling authority in the browser.

## Operations

- `GET /api/research/delivery/capabilities`: readiness, exact coverage and workload
  limits, a complete native `scenario_template`, and implemented method availability.
- `POST /api/research/delivery/analyze`: bounded synchronous fresh calculation.
  Request is `{"scenario": <native scenario>, "options": <optional scheduler options>}`.
  Options remain `chunk_bytes`, `bin_s` and `time_limit_s`.

The Python pipeline validates the scenario, prepares numerical terrain/ephemeris
inputs, solves the resource-constrained schedule, independently replays a candidate
and creates the canonical export. It must not substitute a recorded result.

## Response envelope

```text
delivery_api_version: "1.0.0"
scenario_sha256: canonical native scenario hash
scenario: exact validated native scenario
result: native result
summary: Python export summary
display: Python display_data plus source-labeled supplementary endpoint states
environment: Python analysis environment
replay: independent replay report, or null when no candidate was replayed
export:
  encoding: "gzip+base64"
  media_type: "application/zip"
  sha256: SHA-256 of the original canonical ZIP bytes
  size_bytes: size of those ZIP bytes
  bytes_base64: base64 of gzip(original ZIP bytes)
```

The outer HTTP JSON response uses gzip content encoding when required by the
bounded response budget. This is separate from the inner export encoding. The
browser's HTTP stack decodes the outer response. Download code decodes base64,
decompresses the inner gzip, checks original ZIP size and SHA-256, then downloads
those exact bytes. It does not rebuild the run package from display records.

The hosted adapter supplements map endpoints at 60-second and exact allocation
epochs using the same Python geometry and resolved site. It labels that addition
in `additional_states_provenance`. The native ZIP retains the original exporter
display and complete scientific run; no native interval, allocation or replay
input is changed by the additional view samples.

The decoded response is capped at 16 MB and the wire response below 4 MB. A request
that cannot fit is rejected explicitly; scientific arrays are never silently
truncated to fit. Clients that do not accept the required content encoding receive
an explicit error rather than an oversized successful response.

## Lifecycle and scientific boundary

There is no durable job identifier, retained run registry, polling contract or
server cancellation claim. Browser cancellation stops waiting. The isolated worker
and its solver process are terminated at the declared wall-clock budget. Capability
readiness requires source verification and a working solver, not merely imports.

The hosted provider retains its regional/date/hardware/network limitations.
Assumed rates, service and pointing remain assumptions. A configured synthetic
two-body relay remains synthetic. Reconstructed LRO geometry is not relay service.
An infeasible result is released only at the scope justified by known inputs and
solver evidence; unknown remains distinct from infeasible and zero.

The browser may validate contracts, associate hashes, render stored states and
intervals, and format units/timestamps. It must not recompute visibility, link
performance, energy, routing or delivery metrics. These are Python outputs.
