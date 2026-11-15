# Phase 6 integrated verification

Phase 6 is complete for the declared local integrated baseline, starting from
merged PR #11 and reviewed again after PR #12 (`29c67b7`). Independent replay,
exact export/display checks, the computed demo, sensitivity experiments, browser
acceptance and source/attribution review pass. These results establish the
planning model under its stated synthetic assumptions.

The completion check reads the actual archives, verifies evidence hashes,
replays feasible schedules, checks unchanged comparison controls and verifies
independent non-author review receipts. It does not accept a completion flag as
proof. The reviewers are automated GPT-6.1 agents; no separate human usability
study is claimed. See [independent reproduction](independent-review.md) and the
[independent interface walkthrough](../../../web/docs/phase-6-independent-review.md).

The license review covers the current localhost R&D use and records its terms,
notices, attribution and interpretation limits. The earlier Phase 6 gate added
a public-deployment approval requirement that the plan does not require. That
scope error is corrected. Public hosting has not been requested or performed;
its account, plan and transformed-content conditions remain separate future
review items. No vendor approval or new redistribution right is claimed. See the
[source and license audit](source-and-license-audit.md).

The validated regional map bridge and all scientific calculations are unchanged.
Phase 7's verification prerequisite is met; its optional features have not started.

## Start and verify

From the repository root, in separate terminals:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --editable '.[test,analysis,verification,planning,service]'
.venv/bin/uvicorn soma.api.app:app --host 127.0.0.1 --port 8000
```

```sh
npm --prefix web ci
npm --prefix web run dev
```

Open `http://127.0.0.1:5173/`. For a numerical demonstration without ion streaming,
set `VITE_CESIUM_ION_TOKEN=''` in the environment of the web command. A failed or
absent map never substitutes a fixture calculation for a live request. The scoped
token in ignored `web/.env.local` is not copied into any tracked artifact.

Current exact verification commands:

```sh
.venv/bin/python -m soma.verification.completion
.venv/bin/pytest tests/engine -q
npm --prefix web test
npm --prefix web run build
npm --prefix web run test:live
SOMA_FIXTURE_TEST_PORT=5176 npm --prefix web run test:browser
```

`SOMA_BROWSER_EXECUTABLE` may select an installed compatible Chromium. The
optional fixture-test port avoids disturbing an existing development server.
Current test counts and artifact hashes are recorded in
`data/phase6-evidence.manifest.json`. Pinned-library
PuLP, Skyfield and FastAPI/httpx deprecation warnings remain visible.

## Follow the computed demonstration

The task uses 16 MiB, the same declared lander hardware and initial 80 Wh battery,
the same site, configured network and fixed absolute deadline of 10:05 UTC.
All contacts, sky geometry, rates and service are explicitly synthetic/assumed.

1. Select the relay network example, set 16 MiB and disable the relay route family.
   With data ready at 08:50 UTC, direct delivery is feasible under assumptions.
2. Save that result as A. Set data readiness to 09:05 UTC while leaving the deadline
   and analysis horizon unchanged. Direct delivery is infeasible: its remaining
   76,800,000 payload bits cannot carry the 134,217,728-bit dataset. Save as B.
3. Enable the already configured lunar relay route family. The engine finds a
   relay transfer, storage interval and later ground forwarding contact.
4. Inspect the native transmit/receiver/availability times, storage and energy.
   Scrub time without launching a new job. Download the exact run ZIP.

This changes readiness within one operating day; it is not a new-day ephemeris
comparison. An unsupported site returns `unknown`. An unsupported date/trajectory
coverage request is rejected with a specific input explanation. Neither is a
recommendation for a physical landing site. Task controls in saved comparisons
show unchanged volume, hardware, initial battery, network and absolute deadline.

Recompute the checked-in three-case demonstration without a browser:

```sh
PYTHONPATH=. .venv/bin/python soma/docs/phase-6/reproduce-demo.py --output-dir OUTPUT_DIRECTORY
.venv/bin/python -m soma.verification.exports OUTPUT_DIRECTORY/relay-later/run.zip
.venv/bin/python -m soma replay OUTPUT_DIRECTORY/relay-later/run.json
```

The recorded CLI cases use 30 s scheduler bins and a 16 MiB planning chunk:

| Case | Computed status | Final arrival UTC |
| --- | --- | --- |
| Direct, ready 08:50 | feasible under assumptions | 08:59:00 |
| Direct, ready 09:05 | infeasible in model | Unknown |
| Relay enabled, ready 09:05 | feasible under assumptions | 10:00:30 |

The separately downloaded manual live result uses the service default 5 s bins;
its direct and relay arrivals are 08:58:45 and 10:00:15. This expected difference
comes from upward whole-chunk occupancy rounding. Every export records its own
settings and exact intervals; no timestamps are adjusted to match a narrative.

## Reproduce the export in a clean process

`python -m soma.verification.exports RUN_ZIP` checks unique member names, complete
SHA-256/size coverage, frozen native contracts, scenario hashes and exact
CSV/native/display records. It independently replays every claimed feasible
allocation with the archived contacts and generation, checking byte conservation,
causality, capacity, storage, both radio endpoints, energy and the final deadline.
Rehashed corrupt CSV files and a consistently re-exported false feasible schedule
are rejected. Infeasible/unknown packages do not claim that replay independently
proves infeasibility. Legacy nonfeasible archives without display data report
that omission explicitly; current feasible exports require display evidence.

For another optimization from exported inputs, extract the flat JSON members
locally and use the recorded `details.scheduler_options` in the run manifest:

```sh
.venv/bin/python -m soma run scenario.json --analysis-inputs analysis-inputs.json --bin-s 5 --chunk-bytes 16777216 --time-limit-s 15 --output-dir REPRODUCED_DIRECTORY
.venv/bin/python -m soma.verification.exports REPRODUCED_DIRECTORY/run.zip
```

Those settings reproduce the recorded manual live example. Its replay and a new
optimization were run from an isolated source copy containing no browser files or
credentials. Scenario hash, delivered bytes, arrival and allocations matched
exactly. The evidence is a fresh-process reproduction, not a claim of a separate
human usability study. An unresolved or time-limited run must retain its actual
solver status; a different valid incumbent must not be rewritten into a match.

The relay fixture has no trajectory. `states` stays empty, exact selected-time
reads report unknown spacecraft states, and unsupported intermediate resource
samples stay unknown. Available schedule samples, CSV intervals and metrics are
copied without display resampling. No orbit or contact line is invented.

## Sensitivity evidence

```sh
.venv/bin/python -m soma.verification.sensitivity > sensitivity.json
```

The six schedule cases use the original 100 MiB fixture with declared constant
zero generation. Each changes one control and replays every feasible output.

| Change from 10 s baseline | Recorded outcome |
| --- | --- |
| Baseline | Feasible, replay passes |
| Initial battery 80 to 11 Wh | Infeasible in the discretized model |
| All payload rates and capacities halved | Infeasible in the discretized model |
| Relay service removed | Infeasible in the discretized model |
| Scheduler bins reduced to 5 s | Feasible incumbent, replay passes |
| Scheduler bins increased to 30 s | Infeasible in the discretized model |

The 30 s model rounds seven ground-hop chunks into more occupancy than the
180 s service window. It demonstrates numerical conservatism, not physical
infeasibility. The recorded 5 s incumbent has unproven optimality; comparing it
to the 10 s proven optimum cannot establish a finer-grid optimum.

A separate synthetic finite-segment test changes clearance margin from 0 to
20 m, spatial step from 100 to 50 m, and terrain completeness. Higher clearance
requirements and missing samples remain unknown when not established. It does
not turn a static sampled segment into an interval-wide lunar contact.
Geometry-time sampling and numerical DEM pixel size are reported separately as
unavailable in these synthetic experiments. No physical convergence, DEM error
ensemble or mission-success probability is claimed.

## Evidence and remaining boundaries

See `fixtures/phase-6/` for the demo runs, manual live ZIP and fresh-process proof,
and the sensitivity report. The [interface report](../../../web/docs/phase-6-verification.md)
records live requests, every warning/assumption/service label, unknown and failed
states, stale jobs, keyboard access, mobile layouts, enlarged text and map failure.

Source/notice review preserves Cesium attribution and build notices, keeps large
kernels/DEM/geoid and tile binaries outside Git, and checks current primary terms.
Future public hosting needs its actual content use and account/plan reviewed;
this completion check does not authorize deployment. The source audit also maps the reduced implementation against the actual Space
Apps challenge; physical arbitrary-site/date planning remains a gap.

No ground-time booking, flight DTN stack, relay certification, navigation accuracy,
thermal survival, universal site ranking or complete challenge claim is made.
