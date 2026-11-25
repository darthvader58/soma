# SOMA

**Selenographic Observation and Mission Atlas**

[![PyPI](https://img.shields.io/pypi/v/soma-lunar)](https://pypi.org/project/soma-lunar/)
[![Python](https://img.shields.io/pypi/pyversions/soma-lunar)](https://pypi.org/project/soma-lunar/)
[![CI](https://github.com/darthvader58/soma/actions/workflows/ci.yml/badge.svg)](https://github.com/darthvader58/soma/actions/workflows/ci.yml)
[![License: GPLv3](https://img.shields.io/badge/license-GPLv3-blue.svg)](https://github.com/darthvader58/soma/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-Mintlify-526D3D)](https://soma-ce3178ca.mintlify.site)

SOMA is a Python library and web workbench for lunar geometry and data-delivery
planning. Give it a landing site, data-ready time, file size, deadline, hardware
profile, and declared network. It calculates when to transmit, which contacts to
use, where data waits, and when the last byte reaches Earth. Contact capacity,
relay storage, terminal conflicts, propagation delay, and lander energy constrain
the schedule.

[Documentation](https://soma-ce3178ca.mintlify.site) ·
[Web workbench](https://soma-atlas-two.vercel.app) ·
[Python API](https://soma-ce3178ca.mintlify.site/reference/python-api) ·
[Scientific plan](https://github.com/darthvader58/soma/blob/main/plan/README.md)

SOMA is a planning model under declared assumptions. Published LOLA terrain and
matched DE421 ephemerides support a bounded south-polar analysis. Radio rates,
hardware, station service, and synthetic relay trajectories remain explicit
assumptions. A computed schedule is not a lunar mission prediction.

## Install

Use Python 3.12 or newer. The distribution is `soma-lunar`; the Python import is
`soma`.

```sh
python -m pip install "soma-lunar[planning]"
```

| Installation | Use |
| --- | --- |
| `soma-lunar` | Validate JSON scenarios and inspect the contracts. |
| `soma-lunar[analysis]` | Add SPICE geometry, numerical terrain, illumination, and power calculations. |
| `soma-lunar[planning]` | Add the analysis dependencies and PuLP/CBC delivery scheduler. |
| `soma-lunar[planning,service,verification]` | Add the local HTTP service and independent ephemeris checks. |

Numerical analysis uses native dependencies, including Rasterio, PROJ, and SPICE.
Planning also requires an executable CBC solver. Check your installation with:

```sh
python -c "import pulp; print(pulp.PULP_CBC_CMD().available())"
```

The command should print a solver path. Wheel and executable availability depend
on Python version and platform; see the
[installation guide](https://soma-ce3178ca.mintlify.site/getting-started/installation).
Terrain rasters and large ephemerides are acquired separately. The synthetic
quickstart needs no scientific-data download or browser token.

## Plan a delivery in Python

This example uses an installed, explicitly synthetic 100 MiB fixture. It works
outside a source checkout.

```python
from soma import plan_delivery
from soma.validation import load_scenario, resource_directory

scenario_path = resource_directory("fixtures") / "synthetic-relay" / "scenario.json"
scenario = load_scenario(scenario_path)
result = plan_delivery(
    scenario,
    options={"chunk_bytes": 104_857_600, "bin_s": 5, "time_limit_s": 30},
)

print(result["status"])
print(result["solver_status"])
print(result["model_fidelity"])
print(result["delivered_bytes"])
print(result["final_byte_arrival_utc"])
```

A single whole-file chunk keeps this introductory optimization small; its
5-second bins and 30-second solver budget are explicit choices. A feasible
result delivers all 104,857,600 bytes and passes independent schedule
replay. `model_fidelity` remains `assumed_rate_simulation`. A time-limited run may
return a feasible incumbent without proving optimality; an unresolved run remains
`unknown`.

For the analysis inputs, replay record, solver details, and export package:

```python
from pathlib import Path
from soma.engine import plan_run
from soma.exports import create_run_package

run = plan_run(
    scenario,
    options={"chunk_bytes": 104_857_600, "bin_s": 5, "time_limit_s": 30},
)
Path("soma-run.zip").write_bytes(create_run_package(run))
print(run["validation"])  # None if no candidate schedule was replayed.
```

The hand check behind this fixture is simple: 100 MiB is 838,860,800 bits. Its
20-minute direct contact at 256,000 net payload bits/s can carry only 307,200,000
bits. A 2,000,000 bit/s relay hop needs 419.4304 seconds, followed by 83.88608
seconds at 10,000,000 bit/s to ground. Those are invented contact inputs with
light time disabled for arithmetic. Storage, radio use, energy, and deadline
still have to pass the engine's checks. They are separate from the workbench's
16 MiB default task.

## Read a result

| Field | Meaning |
| --- | --- |
| `status: feasible_under_assumptions` | Complete delivery passed independent replay under the declared inputs. |
| `status: infeasible_in_model` | The bounded, discretized model proved that no complete schedule satisfies its constraints. |
| `status: unknown` | Coverage or solver evidence is insufficient for a conclusion. |
| `solver_status` | Separates a proven optimum, feasible incumbent, proven infeasible discretized model, and unresolved run. |
| `model_fidelity` | Distinguishes assumed rates from modeled link budgets. |
| `assumptions`, `warnings`, `provenance` | Record input classes, sources, coverage, and limitations. |

Scenarios require explicit units, timezone-qualified timestamps, a Moon-fixed
frame realization, an elevation datum, separate antenna and panel heights,
finite resource profiles, and service assumptions. Missing resources never
become unlimited resources. Unknown terrain remains unknown.

## Use the command line

Copy a bundled scenario into your working directory, then validate, run, and
replay it:

```sh
python -c "from pathlib import Path; from soma.validation import resource_directory; Path('scenario.json').write_bytes((resource_directory('fixtures') / 'synthetic-relay' / 'scenario.json').read_bytes())"
python -m soma validate scenario.json
python -m soma run scenario.json --output-dir soma-run --chunk-bytes 104857600 --bin-s 5 --time-limit-s 30
python -m soma replay soma-run/run.json
python -m soma.verification.exports soma-run/run.zip
```

`soma` is also available as a command. `python -m soma --help` lists geometry,
environment, acquisition, planning, and replay operations.

Run packages contain scenario and result JSON, source and software manifests,
contacts and schedule CSVs, energy and buffer histories, replay evidence, display
data, CZML, and a Markdown explanation. Native contacts use source-transmit
times. Allocations retain receiver occupancy and byte-availability times;
delivery means last-byte arrival by the deadline.

## How the library fits together

The Python engine owns the calculations. The browser displays the returned
states, schedule, and resource histories.

```text
Scenario validation → terrain and ephemerides → illumination and usable contacts
                    → energy-constrained scheduling → independent replay → exports
```

| Task | Entry point | Reference |
| --- | --- | --- |
| Validate and identify a scenario | `soma.validation.load_scenario`, `scenario_sha256` | [Contracts](https://soma-ce3178ca.mintlify.site/reference/scenarios-results) |
| Transform frames and query states | `soma.geometry.spice.SpiceGeometry` | [Geometry and time](https://soma-ce3178ca.mintlify.site/reference/geometry-time) |
| Build horizons and test finite paths | `soma.terrain.horizons.build_horizon`, `finite_segment_visibility` | [Terrain](https://soma-ce3178ca.mintlify.site/reference/terrain) |
| Calculate sunlight and electrical power | `soma.illumination.solar_disk_visibility`, `soma.power.fixed_panel_power` | [Illumination and power](https://soma-ce3178ca.mintlify.site/reference/illumination-power) |
| Assess a configured contact | `soma.links.contacts.assess_contact` | [Communications](https://soma-ce3178ca.mintlify.site/reference/communications) |
| Plan and independently replay delivery | `soma.engine.plan_run`, `soma.schedule.replay.replay_schedule` | [Scheduling](https://soma-ce3178ca.mintlify.site/reference/scheduling) |
| Export the complete run | `soma.exports.create_run_package` | [Validation and exports](https://soma-ce3178ca.mintlify.site/reference/validation-exports) |

## Terrain-backed analysis

Install the planning and verification extras, then acquire the pinned data:

```sh
python -m pip install "soma-lunar[planning,verification]"
python -m soma fetch-geometry-data --data-root soma-data --physical
python -m soma verify-geometry --data-root soma-data
```

Acquisition downloads matched kernels and bounded numerical elevation/count
extracts. Manifests preserve source URLs, hashes, coverage, sampling, frame, and
quality conventions. Set `SOMA_DATA_ROOT` to that directory for physical planning.
Read the [physical-run guide](https://soma-ce3178ca.mintlify.site/getting-started/physical-runs)
and [data guide](https://github.com/darthvader58/soma/blob/main/data/README.md)
before acquisition.

The [recorded physical demonstration](https://github.com/darthvader58/soma/blob/main/soma/docs/physical-first-release/README.md)
compares direct delivery on November 24, 2026, direct-only failure on November
30, and store-and-forward relay delivery on November 30. It holds the 16 MiB
file, hardware, initial battery state, site, and six-hour deadline rule constant.
The results and reproduction commands identify the assumptions behind that
comparison.

## Web workbench and local service

Open the [public workbench](https://soma-atlas-two.vercel.app) to calculate
multi-site Sun/Earth geometry or a bounded delivery plan. Its geometry tool uses
a reference sphere and a sourced historical LRO trajectory. Its delivery tool
uses numerical terrain and the Python scheduler. Geometry-only output does not
establish sunlight, power, or usable communications.

To run the interface locally, clone the repository and install the engine:

```sh
git clone https://github.com/darthvader58/soma.git
cd soma
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[planning,service]"
uvicorn soma.api.app:app --host 127.0.0.1 --port 8000
```

In another terminal, use Node.js 22.12+ or Node.js 24:

```sh
npm --prefix web ci
npm --prefix web run dev
```

Open `http://127.0.0.1:5173/`. The optional Moon tiles require appropriately scoped
Cesium ion credentials; numerical results remain available if tiles fail. See the
[web setup](https://github.com/darthvader58/soma/blob/main/web/README.md)
and [analysis/map guide](https://soma-ce3178ca.mintlify.site/guides/analysis-and-map).

The loopback service exposes `POST /plans`, `GET /plans/{id}`,
`DELETE /plans/{id}`, and `GET /plans/{id}/export`, with interactive API docs at
`http://127.0.0.1:8000/docs`. Jobs run in isolated Python processes with finite
retention. The hosted workbench uses separate bounded synchronous endpoints;
it does not provide this local job registry. See the
[service reference](https://soma-ce3178ca.mintlify.site/reference/service).

## Model boundaries

- Terrain-backed planning supports a declared small region near 89°S, 0°E during
  November 2026, for horizons of at most six hours. Global reference-sphere
  geometry does not expand that terrain coverage.
- Baseline routes are direct-to-Earth or one configured store-and-forward lunar
  relay. Earth-orbit routing and general constellation optimization are future work.
- Synthetic contact fixtures have no physical spacecraft ephemeris. Synthetic
  two-body lunar presets are not operational frozen or libration-point orbits.
- Published interpolated terrain and coarse fallback retain their quality flags.
  Missing measurements cannot establish a clear horizon.
- Sampling, event guards, time bins, and chunk sizes introduce declared
  approximations. A solver time limit can leave optimality or feasibility unresolved.
- SOMA does not reserve ground service, certify landing safety or flight
  readiness, model thermal survival, or assign mission-success probabilities.
  It does not claim CCSDS SABR or LunaNet compliance or full TAT-C feature parity.

See the [capability matrix](https://soma-ce3178ca.mintlify.site/science/capability-matrix),
[assumptions and limits](https://soma-ce3178ca.mintlify.site/science/assumptions-limits),
and [research register](https://github.com/darthvader58/soma/blob/main/plan/06-Research-and-Source-Register.md).

## Contribute and cite

Bug reports should include a minimal scenario, package version, units, frame,
UTC interval, and relevant data hashes. Read the
[contribution guide](https://github.com/darthvader58/soma/blob/main/CONTRIBUTING.md)
for development setup and verification commands. Release changes are recorded in
the [changelog](https://github.com/darthvader58/soma/blob/main/CHANGELOG.md).

Use the repository's [citation metadata](https://github.com/darthvader58/soma/blob/main/CITATION.cff)
when citing the software, and cite the original datasets and methods used by
your analysis. A software citation does not replace those scientific sources.

## Authors, acknowledgments, and license

SOMA is developed by **Shashwat Raj and Saanvi Kakde**, students at Arizona State
University. We acknowledge Dr. Paul T. Grogan of ASU's Collective Design Lab for
his mentorship, an initial discussion of SOMA, and permission for Shashwat Raj
to base the project on TAT-C.

SOMA is a companion project informed by TAT-C's mission-analysis patterns. Its
lunar geometry and scheduling require their own validation. The
[NASA Space Apps challenge](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/)
provides the site/date, Sun/Earth/horizon, solar-power, and direct Earth
communications objectives; relay delivery planning is SOMA's extension.

The project is distributed under [GNU GPLv3](https://github.com/darthvader58/soma/blob/main/LICENSE).
External data, Cesium content, and dependencies retain their own terms and
attribution requirements; see the
[third-party notices](https://github.com/darthvader58/soma/blob/main/THIRD_PARTY_NOTICES.md).
No NASA, ASU, or other institutional endorsement is implied.
