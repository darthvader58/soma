# SOMA

**Selenographic Observation and Mission Atlas**

SOMA is a Python library and web workbench for lunar geometry and data-delivery planning.
The live workbench calculates multi-site Sun/Earth geometry from matched DE421
kernels and plays a reconstructed LRO trajectory from the NASA PDS/NAIF archive.
Given a landing site, data-ready time, file size, deadline, hardware profile,
and declared network, it builds an explainable schedule for direct-to-Earth
delivery or delivery through one lunar relay. Contact capacity, storage,
radio conflicts, propagation delay, and lander energy constrain the plan.

[Web demo](https://soma-atlas-two.vercel.app) ·
[Python quickstart](#use-the-python-library) ·
[Local web application](#run-the-web-application) ·
[Scientific methods](plan/README.md)

SOMA is a planning model under declared assumptions. The original examples use
synthetic geometry. The physical first release connects published LOLA terrain
and DE421 ephemerides to the scheduler for a bounded south-polar region and
operating period. Hardware, radio rates, station service and the two-body relay
remain declared assumptions; these results are not lunar mission predictions.

The [physical first-release report](soma/docs/physical-first-release/README.md)
maps the required `plan/` scope to computed evidence and exact run commands.

## Try the web demo

Open **[soma-atlas-two.vercel.app](https://soma-atlas-two.vercel.app)** to calculate
a new geometry study without installing anything. The app and public Python API
run on Vercel.

- Select from 15 sourced lunar locations or add a custom coordinate.
- Change UTC dates, sampling and separate antenna/panel heights, then run Python analysis.
- Use the reconstructed LRO coverage interval and play its supplied position history.
- Inspect per-site Sun/Earth elevation histories, sources and exact sampled readouts.
- Export the returned scientific JSON and reproduce it with the documented library.

The geometry endpoint uses a declared reference sphere. It does not evaluate terrain
shadowing, solar-disk fractions, power, usable radio contacts or delivery. Catalog
crater centers are context references, not certified landing sites. The workbench
shows source coverage and rejects unsupported requests rather than inventing results.
See the [live research tutorial](docs/getting-started/live-research.mdx),
[API reference](docs/reference/research-api.mdx) and
[source notes](docs/science/research-sources.mdx).

To reproduce the three-site historical LRO study locally:

```sh
python scripts/prepare-research-data.py --output /tmp/soma-research-sources
python examples/research_geometry.py --data-root /tmp/soma-research-sources --output /tmp/lro-three-sites.json
```

The **[delivery archive](https://soma-atlas-two.vercel.app/?mode=archive)** accepts only exact matches
to the supplied scenarios. An edited scenario needs a live Python service;
the browser does not calculate a replacement result or scale a saved schedule.
The hosted display adapter serves the corrected Cesium Moon representation.
The mission cases retain published numerical LOLA terrain and DE421 geometry;
hardware, rates, station service and the synthetic two-body relay remain assumptions.
All five use the same 16 MiB task and six-hour deadline rule. The low-battery and
unavailable-service cases reject the known baseline in independent replay and
retain native `unknown` outcomes because contact coverage is incomplete.

Use the [seven-minute recording guide](soma/docs/hackathon-demo-script.md) for
exact screen actions and narration. Its [published documentation page](https://soma-ce3178ca.mintlify.site/guides/hackathon-demo)
includes the mission brief and source links.

Original synthetic packages preserve their original export format. The synthetic relay archive
passes numerical replay but predates the display artifact required by the
current complete-export verifier. Generate a fresh run with the CLI below to
produce and verify the current package format.

For live delivery calculations and editable delivery scenarios, run the application locally below.

## Use the Python library

### Installation

Use Python **3.12 or newer** for the full analysis stack. Python 3.14 has been
used for project verification. Install from this repository:

```sh
git clone https://github.com/darthvader58/soma.git
cd soma
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[analysis,planning,service]"
```

The package distribution is named `soma-lunar`; Python imports use
`soma`. The installation above includes numerical analysis, the bounded
PuLP/CBC scheduler, and the local API service. Add the `verification`
extra for independent ephemeris checks and `test` for the engine test suite.

### Plan a delivery

Run this example from the repository root after installation:

```python
import json
from pathlib import Path

from soma import plan_delivery

scenario = json.loads(
    Path("fixtures/synthetic-relay/scenario.json").read_text()
)
result = plan_delivery(scenario)

print(result["status"])
print(result["solver_status"])
print(result["model_fidelity"])
print(result["delivered_bytes"])
print(result["final_byte_arrival_utc"])
```

A feasible result is released only after independent schedule replay passes.
Solver status is separate from scientific status: a time-limited feasible
incumbent can deliver the complete file without proving optimality.

For the full calculation record, use `soma.engine.plan_run(scenario)`.
It returns the scenario, native result, analysis inputs, independent validation,
and solver/software details. Scheduler options include `chunk_bytes`,
`bin_s`, and `time_limit_s`:

```python
from soma.engine import plan_run

run = plan_run(
    scenario,
    options={"chunk_bytes": 16_777_216, "bin_s": 5, "time_limit_s": 15},
)
result = run["result"]
replay = run["validation"]  # None when no candidate schedule was replayed.
```

### Understand a result

| Field | Meaning |
| --- | --- |
| `status: feasible_under_assumptions` | The complete delivery schedule passed replay under the declared inputs. |
| `status: infeasible_in_model` | The bounded, discretized model proved that no complete-file schedule satisfies its constraints. |
| `status: unknown` | Coverage, assumptions, or solver evidence are insufficient for a conclusion. |
| `solver_status` | Distinguishes a proven optimum, feasible incumbent, proven infeasible discretized model, and unresolved run. |
| `model_fidelity` | Identifies assumed-rate simulations separately from modeled link budgets. |
| `assumptions`, `warnings`, `provenance` | Explain input classes, sources, limitations, and why the result was returned. |

All scenarios require explicit units, timezone-qualified UTC, a Moon-fixed
frame realization, an elevation datum, separate panel and antenna heights,
finite resource profiles, and declared service assumptions.
See the [JSON contracts](schemas/README.md) and
[sample scenarios](fixtures/synthetic-relay/README.md).

## Use the command line

Validate a scenario, calculate an auditable run, and replay the saved result:

```sh
python -m soma validate fixtures/synthetic-relay/scenario.json
python -m soma run fixtures/synthetic-relay/scenario.json --output-dir /tmp/soma-relay
python -m soma replay /tmp/soma-relay/run.json
python -m soma.verification.exports /tmp/soma-relay/run.zip
```

Use `python -m soma plan SCENARIO.json` for result JSON on stdout.
`python -m soma --help` lists the geometry, environment, data-acquisition,
planning, and replay commands.

The run package includes scenario and result JSON, a manifest with checksums,
contacts and schedule CSVs, energy and buffer histories, summary JSON, display
data, CZML, and a structured Markdown explanation. Schedule exports preserve
source-transmit times, receiver occupancy, and byte-availability times.
Unknown values remain distinct from numeric zero.

## Run the web application

Install the Python package above and use **Node.js 22.12+ or Node.js 24**.
From the repository root, start the Python service:

```sh
source .venv/bin/activate
uvicorn soma.api.app:app --host 127.0.0.1 --port 8000
```

In another terminal, install and start the browser application:

```sh
npm --prefix web ci
npm --prefix web run dev
```

Open **http://127.0.0.1:5173/**. The development server forwards `/api`
requests to the local Python service. Choose a declared network, select
**Plan delivery**, inspect the schedule and resource histories, and download
the run package. Input edits invalidate previous results; failed live requests
never substitute captured results.

To inspect the same saved examples as the public demo without the service:

```sh
VITE_SOMA_MODE=fixture npm --prefix web run dev
```

The [web application guide](web/README.md) covers client settings and downloads.
The Python engine owns physics and scheduling; the browser displays its
stored results and changes the selected display time.

### Local API

The service exposes its interactive API reference at
**http://127.0.0.1:8000/docs**.

| Endpoint | Purpose |
| --- | --- |
| `POST /plans` | Submit a complete scenario and receive a job identifier and scenario hash. |
| `GET /plans/{id}` | Read job progress and the completed immutable result. |
| `DELETE /plans/{id}` | Cancel queued or running work. |
| `GET /plans/{id}/export` | Download the completed run package. |

For example:

```sh
curl --request POST http://127.0.0.1:8000/plans \
  --header "Content-Type: application/json" \
  --data-binary @fixtures/synthetic-relay/scenario.json
```

Jobs run in isolated Python processes. The current service keeps a bounded,
in-memory job registry and is intended for local use. A public live planner
requires a separately designed service deployment; the Vercel display adapter
does not host the planning job API.

### Vercel deployment

Library documentation is published with [Mintlify](https://soma-ce3178ca.mintlify.site/).
The application's Documentation button opens `/docs`, which redirects to that
site. Documentation source lives in [`docs/`](docs/README.md).

Deploy from the **repository root**, with the framework preset **Other**.
The root `vercel.json` installs and builds `web/`, serves `web/dist`, and routes
`/api/moon/*` to the Python function in `api/index.py`. The public deployment
at [soma-atlas-two.vercel.app](https://soma-atlas-two.vercel.app/) has been
checked with rendered terrain, exact stored relay states, computed schedules,
and a byte-identical run download. See the
[hosted verification record](soma/docs/hosted-deployment-verification.md).

The Python function exposes registration, conversion metadata, and the bounded
registered Moon tile stream. It reuses the engine's pinned display conversion
and registration evidence, retains source attribution, and returns private,
nonpersistent responses. It does not run planning jobs or replace numerical
terrain analysis. Unsupported or oversized tile objects fail explicitly.
The Linux build bundles its system Expat library and license texts for
Rasterio, records the package and checksum, and verifies the library before
loading it. Generated native binaries stay out of Git.

Configure these deployment environment variables without committing token values:

| Variable | Type and purpose |
| --- | --- |
| `VITE_SOMA_MODE` | Public build setting: `fixture` selects exact captured results. |
| `VITE_SOMA_API_URL` | Public build setting: `/api` is the same-origin API prefix. |
| `VITE_CESIUM_ION_TOKEN` | Public browser credential: a read-only application token scoped to Moon asset 2684829 and the intended public origin. Treat every `VITE_` value as visible to visitors. |
| `SOMA_CESIUM_ION_TOKEN` | Server-side credential for the same authorized Moon asset, configured separately from browser build settings. |
| `SOMA_PUBLIC_ORIGIN` | Server-side HTTPS origin: `https://soma-atlas-two.vercel.app`, used for authorized upstream requests. |

Rotate the deployed ion application tokens by **December 15, 2026**. Keep their
asset scope and allowed origins restricted, and recheck account access and
usage terms when rotating them. Preview domains need their own explicitly
authorized origin configuration.

Captured physical examples preserve Python-calculated contacts, trajectories,
energy histories, and schedules. An arbitrary edited site, date, or hardware
profile requires the Python analysis engine and its datasets; neither this
display function nor the browser computes a replacement plan.

## Terrain, ephemerides, and the optional Moon view

The synthetic examples run without downloading lunar rasters or kernels.
For numerical geometry diagnostics, acquire the pinned data separately:

```sh
python -m pip install -e ".[verification]"
python -m soma fetch-geometry-data --data-root /tmp/soma-data
python -m soma verify-geometry --data-root /tmp/soma-data
```

Dataset manifests record sources, hashes, extraction bounds, count masks,
reference surfaces, and frame realizations. Missing measured terrain remains
unknown; an interpolated or rendered surface does not establish a clear
horizon. Read the [data guide](data/README.md) before downloading large products.

The optional local Cesium Moon view needs a scoped ion application token in
ignored `web/.env.local` and the matching Python display service.
The versioned registration applies to the corrected representation from
**87.5°S to the south pole**, at the tested source-grid and mesh resolution.
It is a relative display check, not absolute navigation accuracy.
See the [map registration method](soma/docs/phase-5/map-alignment.md) and
[source and usage review](soma/docs/phase-6/source-and-license-audit.md).
The repository-root Vercel configuration supports this display stream when
the deployment credentials and origin are configured as described above.

## Model scope

- Synthetic examples retain their fixed declared coverage. The physical provider
  supports a small region near 89°S, 0°E during November 2026, with analysis
  horizons of at most six hours. Unsupported inputs fail explicitly or remain
  unknown; arbitrary global coverage is not claimed.
- Direct-to-Earth and one configured store-and-forward lunar relay are the
  supported baseline route families. Earth-orbit routing is not enabled.
- The physical date comparison uses published-grid interpolation with count
  masks, explicit coarse fallback, separate equipment heights and checked
  horizon extent. Strict measured-only diagnostics retain their gaps. No
  interpolated sample is relabeled as a measurement.
- Contact-only relay examples contain no spacecraft ephemeris. Missing
  spacecraft states stay unknown rather than becoming an invented orbit.
- Time bins and chunk sizes introduce declared conservatism. Fresh,
  time-limited optimization can choose a different valid incumbent;
  replaying a recorded run verifies that specific result.
- SOMA does not reserve ground service, implement a flight DTN stack,
  certify a landing site, or model thermal survival or mission-success probability.

To prepare and run the physical demonstration after installing the full stack:

```sh
python -m soma fetch-geometry-data --data-root /private/tmp/soma-phase2-data --physical
SOMA_DATA_ROOT=/private/tmp/soma-phase2-data python soma/docs/physical-first-release/reproduce.py --output-dir PHYSICAL_RUNS
python -m soma.verification.exports PHYSICAL_RUNS/relay-later/run.zip
python -m soma.verification.physical_completion
```

In the live interface, select a **Physical** network example. The recorded story
is direct success on November 24, direct-only failure on November 30, and
store-and-forward relay delivery on November 30 under the same six-hour deadline
rule. The hosted configuration also includes these captured physical runs;
fresh calculations remain part of the Python engine workflow.
The local service has finite result retention; export needed runs and restart it
if the stated retention limit is reached. Optional Phase 7 additions remain future
work.

## Verification and documentation

Install the test dependencies and run the relevant checks:

```sh
python -m pip install -e ".[test,verification]"
python -m pytest tests/engine -q
npm --prefix web test
npm --prefix web run build
```

Additional browser checks and reproducibility commands are documented in the
[integrated verification guide](soma/docs/phase-6/README.md).

| Resource | Contents |
| --- | --- |
| [Scientific plan](plan/README.md) | Geometry, illumination, communications, power, scheduling, and design boundaries. |
| [Physical first release](soma/docs/physical-first-release/README.md) | Computed date comparison, required-plan coverage, reproduction and numerical limits. |
| [Research and source register](plan/06-Research-and-Source-Register.md) | Papers, official datasets, standards, and the claims each supports. |
| [Scheduler methods](soma/docs/phase-4/scheduler.md) | Objective ordering, event bins, capacity, storage, conflicts, and energy constraints. |
| [Independent replay](soma/docs/phase-4/replay.md) | Byte conservation, causality, occupancy, storage, energy, and deadline checks. |
| [Export and service reference](soma/docs/phase-4/service-exports.md) | Job lifecycle, artifact formats, and implementation limits. |
| [Challenge alignment](soma/docs/challenge-alignment.md) | Relationship to the NASA Space Apps Lunar Landing Site Navigator brief. |

## Authors, acknowledgments, and license

SOMA is developed by **Shashwat Raj and Saanvi Kakde**, students at
Arizona State University. We acknowledge Dr. Paul T. Grogan of ASU's
Collective Design Lab for his mentorship, an initial discussion of SOMA,
and permission for Shashwat Raj to base the project on TAT-C.

SOMA is a companion project informed by TAT-C's mission-analysis patterns.
Its lunar geometry and scheduling require their own validation.
The [NASA Space Apps challenge](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/)
provides the site/date, Sun/Earth/horizon, solar-power, and direct Earth
communications objectives; relay delivery planning is SOMA's extension.

The project is distributed under [GNU GPLv3](LICENSE).
External data, Cesium content, and dependencies retain their own terms and
attribution requirements. No NASA, ASU, or other institutional endorsement
is implied.
