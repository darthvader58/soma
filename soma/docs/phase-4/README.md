# Phase 4: auditable delivery planning

This implements plan Parts 3, 4 and 5: bounded scheduling, independent replay,
isolated service jobs and reproducible exports. The six v0.1.0 schemas remain
unchanged. Separate analysis and summary artifacts use version 0.4.0.

The default provider supports the explicitly synthetic site/network and fixed
08:50–10:05 UTC horizon on 14 November 2026 in the fixtures. It derives usable
contacts and generation through the Phase 3 Python modules, then solves the
schedule. It never reads `expected.json`. A site, equipment-height, trajectory,
station-geometry or horizon change needs new analysis inputs; unsupported
coverage returns `unknown`. Sky geometry does not move with an edited ready
time. Missing terrain or generation never becomes clear terrain or zero load.

## Reproduce and inspect

From the repository root, using Python 3.12 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --editable '.[test,analysis,verification,planning,service]'
.venv/bin/python -m pytest tests/engine -q
.venv/bin/python -m soma validate fixtures/synthetic-direct/scenario.json
.venv/bin/python -m soma validate fixtures/synthetic-relay/scenario.json
.venv/bin/python -m soma run fixtures/synthetic-direct/scenario.json --output-dir /private/tmp/soma-direct-run
.venv/bin/python -m soma run fixtures/synthetic-relay/scenario.json --output-dir /private/tmp/soma-relay-run
.venv/bin/python -m soma replay /private/tmp/soma-relay-run/run.json
.venv/bin/uvicorn soma.api.app:app --host 127.0.0.1 --port 8000
```

`plan_delivery(scenario)` returns the native result. `plan_run(scenario)` also
returns analysis inputs, independent validation and solver/software details.
The CLI `run` command writes one calculation and its exact package members;
`replay` checks stored inputs and allocations without rerunning the solver.
Explicit analysis inputs must declare completeness, version and the exact
scenario hash. They are a trusted scientific input boundary, not independent
proof of geometry or link closure.

## Captured synthetic acceptance case

The recorded runs are in [`fixtures/phase-4`](../../../fixtures/phase-4/README.md).
The 100 MiB file is 104,857,600 bytes or 838,860,800 bits. The direct contact
has at most 307,200,000 payload bits: its complete-file result is
`infeasible_in_model` with `proven_infeasible_discretized_model`. This is not a
maximum-partial-delivery calculation.

The relay capture delivers all bytes and passes independent replay. Its solver
status is `feasible_incumbent`: the default 15-second CBC budget did not prove
optimality. Seven chunks produce fourteen transmissions. Five-second event
bins round payload occupancy upward, so captured times differ from the
continuous hand arithmetic. Different machines or time-limited searches can
choose a different valid incumbent. Replaying the captured run and verifying
its member hashes reproduces its evidence exactly; rerunning optimization is
not promised to choose byte-identical allocations.

Both cases use invented geometry, assumed net rates, ideal pointing, assumed
service and explicitly disabled light time only for the synthetic fixture.
They are software acceptance cases, not lunar predictions or network access.

## Constraint and validation evidence

Owner verification: **281 engine tests pass**. Both scenarios validate against
the frozen contract. The recorded relay passes a fresh CLI replay with zero
errors and 104,857,600 unique delivered bytes. Every ZIP member checksum and
the corresponding browser fixture copy were verified. No engine test was
skipped. Pinned PuLP, Starlette and Skyfield dependencies emit deprecation
warnings; those warnings do not indicate a skipped scientific check.

The [scheduler](scheduler.md) uses PuLP/CBC with event-aligned whole-chunk
choices, finite contact/storage/radio resources, arrival-time service and
causal forwarding. The lander energy balance includes waiting and base demand
over the full horizon. Charge/discharge are exclusive, deficits discharge the
bus, and surplus is charged or curtailed within the declared limits.

The [replay validator](replay.md) imports no optimizer state. It rejects
duplicate bytes, unavailable forwarding, late arrival, over-capacity contacts,
buffer overflow, endpoint conflicts and power/reserve violations. A candidate
is released as feasible only after replay passes and all unique bytes arrive.
Unknown or time-limited runs cannot be relabeled as proven infeasible.

Focused commands are:

```sh
.venv/bin/python -m pytest -q tests/engine/test_scheduler.py tests/engine/test_replay.py
.venv/bin/python -m pytest -q tests/engine/test_engine.py tests/engine/test_api.py tests/engine/test_exports.py tests/engine/test_cli.py
```

The tests include changed buffer limits, disabled forwarding, radio conflicts,
service and energy limits, huge workload rejection, corrupted schedules, stale
or canceled jobs, immutable downloads and exact CSV epochs. Solver assertions
check the MILP energy balance as well as the independently replayed result.

## Service and artifact boundary

The [service/export reference](service-exports.md) documents POST/GET/DELETE
jobs, process isolation, bounded retention and cached ZIP downloads. The run
package includes scenario, result, manifest, contacts, schedule, battery and
buffer CSVs, summary, metadata-only CZML, structured Markdown, analysis inputs
and replay evidence. CSV headers carry units; unknown is distinct from zero.
Manifest checksums cover every member except the manifest itself. No kernel,
raster, tile or restricted paper is redistributed.

The Python summary supplies byte-weighted relay wait, lander communications
electrical energy and minimum reserve margin only for replayed feasible runs.
Browser comparison may display these versioned fields; it must not derive them
from histories. The scientific diagnostic battery remains a separate base-load
trace; selected-schedule battery history is in the native delivery result.

The local headless service is available. Live browser integration, versioned
renderer registration and landmark residual checks remain Phase 5 work. CZML
contains no unregistered positions. Phase 6 integrated acceptance and challenge
completion are not claimed. SOMA is a planning model under declared assumptions.
