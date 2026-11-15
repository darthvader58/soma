# SOMA: A Research-Grounded Lunar Communications Planner

The Python engine now selects energy-constrained delivery schedules, independently
replays them, serves isolated jobs and exports complete run packages. The current
100 MiB synthetic direct case fails capacity; the relay case passes replay with
optimality unproven. The browser now runs live Python jobs by default. See the
[Phase 4 run commands and limits](soma/docs/phase-4/README.md) and the
[live integration guide](soma/docs/phase-5/README.md). Renderer registration remains an unfinished Phase 5
gate. SOMA is a planning model under declared assumptions.

## What this project is

SOMA should do one useful job: take a proposed lunar landing location, an operating date, a quantity of data, and a delivery deadline, then produce an explainable schedule for getting that data to Earth using a specified lander and network. The result should say when to transmit, which receiving asset to use, where the data waits between contacts, when the final data reaches its destination, and whether the lander's modeled energy reserve is respected. The Python library supplies the calculations. The Cesium application lets someone choose the site, inspect the terrain and moving assets, understand the schedule, and export the result. This is a proposed product definition, not a claim that SOMA has already implemented or validated these capabilities.

“Lunar TATC” in this plan means a lunar mission-analysis library inspired by the Tradespace Analysis Toolkit for Constellations. It does not mean a physical lunar taxi or a new spacecraft. More importantly, SOMA should not try to become a general-purpose lunar simulator. It should not optimize launch trajectories, design a whole constellation, certify a landing site, or become another all-purpose planetary atlas. Its distinctive output is a **data-delivery plan**, with site and date comparison serving that decision rather than becoming the product itself.

This focus still fits the NASA Space Apps Lunar Landing Site Navigator challenge. The challenge asks for intuitive site/date evaluation, Sun and Earth positions relative to the local horizon, and information about solar-power potential and direct-to-Earth communications. SOMA turns those environmental quantities into a concrete question: “Can this lander deliver this dataset by this time, and what must it do?” A second site or date is useful because the user can see whether it changes the answer and why. The challenge does not require the relay-routing extension; that is SOMA's proposed way to make the environmental analysis actionable. ([Challenge brief, D01](06-Research-and-Source-Register.md#d01))

## How the evidence is used

This plan distinguishes research evidence from software documentation and from our own design decisions. Published papers support the scientific methods: terrain-horizon illumination modeling, sensitivity to elevation errors and instrument height, time-dependent communications, and lunar power budgeting. A paper is cited near the claim it supports, not merely placed in a long bibliography. The research register explains what each paper actually demonstrates and what cannot be inferred from it. NASA and CCSDS specifications supply implementation constraints and terminology. Current source code and official Cesium documentation establish what the software presently exposes. None of those sources proves the complete proposed SOMA application works. That will require implementation and testing.

The strongest methodological chain is straightforward. Mazarico and colleagues establish a terrain-horizon approach to lunar illumination; Gläser and colleagues examine higher-resolution terrain and different observer heights; Barker and colleagues quantify how terrain uncertainty affects the predicted lighting. Saliwanchik and colleagues provide a concrete lunar-instrument example of translating time-varying sunlight into power generation, storage, and operating choices. Communications papers and the CCSDS routing standard establish why a route must account for contact timing, transmission capacity, and waiting between contacts. SOMA proposes to combine these methods within a deliberately limited planning task. ([P03](06-Research-and-Source-Register.md#p03), [P04](06-Research-and-Source-Register.md#p04), [P05](06-Research-and-Source-Register.md#p05), [P06](06-Research-and-Source-Register.md#p06), [P11](06-Research-and-Source-Register.md#p11), [D07](06-Research-and-Source-Register.md#d07))

## The five parts

[Part 1, Lunar TATC and the analysis foundation](01-Lunar-TATC-and-Analysis-Foundation.md), explains what the existing toolkit offers, which Earth-specific assumptions cannot be carried over, and how a companion Python package should handle lunar reference frames, ephemerides, terrain, and reproducible inputs. [Part 2, Cesium and the map interface](02-Cesium-and-Map-Interface.md), explains how to display the Moon correctly, place a lander, animate relays, and make a schedule understandable without letting graphics become the physics engine.

[Part 3, Communications, relays, and scheduling](03-Communications-Relays-and-Scheduling.md), develops the central product: turning geometric opportunities into usable contacts and a finite-volume transfer schedule. It separates direct-to-Earth links, lunar relays, and optional Earth-orbit relays. [Part 4, Sunlight, power, and site comparison](04-Sunlight-Power-and-Site-Comparison.md), explains how local horizons and solar-array geometry affect the power available for that schedule. [Part 5, Python library and application delivery](05-Python-Library-and-Application-Delivery.md), brings the components together into an implementation sequence, public interfaces, export format, verification plan, and focused demonstration. The [research and source register](06-Research-and-Source-Register.md) is the accompanying evidence map.

## The baseline and its limits

The recommended first release uses a stationary lander, a small region with suitable lunar elevation data, a bounded analysis period, a small fixed relay set, and a few defined Earth receiving stations. Direct-to-Earth is considered first as the simplest available architecture; relays are selected when the stated objective or constraints justify them. This does not mean a direct link always has lower energy cost or earlier completion. All routes must compete using the same hardware assumptions, availability calendars, and data volume. Published lunar relay operations demonstrate that lunar-relay-to-ground architectures are real, while preliminary constellation studies and emulated protocol experiments must remain labeled as such. ([P07](06-Research-and-Source-Register.md#p07), [P08](06-Research-and-Source-Register.md#p08), [P10](06-Research-and-Source-Register.md#p10))

A valid result is “feasible under these inputs and this model,” not “approved for flight.” A visible relay can have inadequate link margin, incompatible equipment, no service allocation, or insufficient storage. A sunny location can still exhaust a battery during transmission or a long shadow. A failed search is not proof that every possible constellation or operating strategy would fail. These boundaries should appear in the application and every exported plan, not only in documentation.

## Audit date and delivery status

This plan was prepared against sources inspected on **13 November 2026**. The TATC implementation audit is pinned to commit **b459b9a02b53cb8d7a171a81fa995df0856dff53**, which matched the repository's public main branch when checked. Older revisions discussed during exploration are not used as evidence of the current implementation. This folder contains a researched project plan, not a working library, deployed website, completed simulation, live network booking, or performance benchmark. Implementation schedules and acceptance thresholds below are proposed development choices.

## Engine development: Phase 1

The complete scientific plan is in [`plan/`](plan/README.md). The initial
Python package now validates standalone JSON scenarios, explicit finite
resource profiles, coordinate/frame metadata, units, UTC timestamps, and the
declared synthetic fixture domain. The six [JSON schemas](schemas/README.md)
are a v0.1.0 review candidate. The user has delegated both developer roles to
this team. An independent GPT-6.1 interface agent completed the
[Phase 1 contract review](web/docs/contract-review.md); this is an automated
review, not a human Developer B approval or a merge.

The [live 2026 challenge](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/)
was reviewed alongside the plan. The [alignment review](soma/docs/challenge-alignment.md)
tracks its site/date, Sun/Earth/horizon, solar-power, and direct Earth objectives,
including the environmental export records still needed in Phases 2 and 3.
Relay scheduling is a SOMA extension to those objectives.

For all current engine tests, use Python 3.12 or newer (3.14.7 was tested).
The contract-only package still supports Python 3.11.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --editable '.[test,analysis,verification,planning,service]'
.venv/bin/python -m pytest tests/engine -q
.venv/bin/python -m soma validate fixtures/synthetic-direct/scenario.json
.venv/bin/python -m soma validate fixtures/synthetic-relay/scenario.json
.venv/bin/python -m soma plan fixtures/synthetic-relay/scenario.json
```

The library entry point is `from soma import plan_delivery`. The CLI emits
JSON to stdout and rejects invalid inputs with a nonzero exit code and a
diagnostic on stderr. It works without a browser. Phase 1 originally returned
`unknown` placeholders. The current pipeline calculates synthetic usable
contacts and generation, constrains scheduling with energy, independently
replays allocations and exports the resulting evidence. Unsupported analysis
coverage remains `unknown`. Start the loopback service with
`.venv/bin/uvicorn soma.api.app:app --host 127.0.0.1 --port 8000`.

The [direct fixture](fixtures/synthetic-direct/README.md) proves by arithmetic
that the supplied 256,000 net bit/s contact cannot carry 100 MiB. The
[single-relay fixture](fixtures/synthetic-relay/README.md) records the
419.4304 s uplink, storage wait, and 83.88608 s downlink expected from the
plan's invented example. These are hand calculations, with propagation
disabled only for the synthetic test. The separately captured Phase 4 relay
schedule passes energy replay, with solver optimality unproven. `expected.json`
is never loaded as the planner's output. To run the fixture/schema checks alone:

```sh
.venv/bin/python -m pytest tests/engine/test_contract.py tests/engine/test_fixture_arithmetic.py -q
```

[Data manifests](data/README.md) distinguish the historical Phase 1 metadata
from the new, acquired and hash-checked Phase 2 kernel and terrain bundle.
The current synthetic validation domain is latitude −90 to −80 degrees,
longitude [−180, 180) east positive, and 14 November 2026 UTC. This is a
fixture boundary, not physical data coverage or arbitrary global planning.
Missing storage limits, unsupported coordinates/dates, unqualified times,
and ambiguous volume units fail explicitly. Planned data hashes remain
`null`; [`fixtures/manifest.json`](fixtures/manifest.json) records the actual
checksums of the local contract and fixture inputs.

SOMA is a planning model under declared assumptions. The engine and interface
are now coordinated by one team. Live integration and
the Phase 6 product checks have not begun.

## Phase 2 geometry and numerical terrain

The geometry layer reads a matched, hash-pinned DE421 planetary ephemeris,
lunar frame and orientation, leap seconds, and Earth orientation. It provides
explicit Moon-fixed/J2000 states, local directions, coordinate round trips, a
defined polar basis, WGS84/ITRF93 station translation, finite body tests,
bounded state-history interpolation, and an explicitly synthetic two-body
relay preset. Its scoped context restores the previous SPICE kernel pool.

Numerical terrain uses an aligned five-meter PGDA LOLA elevation/count window
and a coarser native 64-pixel-per-degree PDS LOLA south-polar cap. Both identify
DE421 mean-Earth. Counts, source revisions, native pixel registration,
extraction bounds and checksums are preserved. Zero counts, nodata and
unsupported coverage remain unknown. Files are acquired locally and are not
bundled in this repository.

```sh
.venv/bin/python -m soma fetch-geometry-data --data-root /private/tmp/soma-phase2-data
.venv/bin/python -m soma verify-geometry --data-root /private/tmp/soma-phase2-data
.venv/bin/python -m soma geometry fixtures/synthetic-relay/scenario.json \
  --data-root /private/tmp/soma-phase2-data \
  --latitude-deg -89.03093035536243 --longitude-deg-east 1.389336784014743 \
  --synthetic-relay
```

The explicit override is a count-positive numerical verification point, not a
landing recommendation. The original synthetic location has unknown measured
terrain and is rejected; it is never moved silently. `geometry` writes a
separate versioned artifact with Sun/Earth center directions and ranges,
station/relay states, per-height horizons, sampled geometric intervals,
source manifests and warnings. Intervals have sampling uncertainty and may
miss shorter events; they are not usable contacts.

The recorded real-data run retains **unknown horizons** because masked
samples prevent convergence, even with the coarse far source. No clear
skyline, solar generation or delivery success is inferred. The selected
synthetic relay is blocked in that run. The independent Skyfield comparison
passes after explicitly accounting for its single-float Julian-date rotation
precision. This checks implementation and frame handling, not the shared JPL
ephemeris accuracy or renderer registration. See the
[Phase 2 evidence](soma/docs/phase-2/README.md) and
[interface-side review](web/docs/phase-2-contract-review.md).

## Interface development: Phase 1 client and Phase 2 selection

[`web/`](web/README.md) contains a runnable scenario editor, captured-result
view, contact timeline, and Cesium Moon client. It imports the canonical JSON
schemas directly; it does not duplicate the scientific model in JavaScript.
Python and JavaScript share RFC 8785 scenario hashes, including shared
Unicode/number test vectors. Changing an input clears the displayed result.
Offline mode accepts only an exact match to a captured Python result.

From the repository root, after installing the Python package above:

```sh
npm --prefix web ci
npm --prefix web run sync:fixtures
npm --prefix web test
npm --prefix web run build
npm --prefix web run dev
```

The dev server serves `http://127.0.0.1:5173/`. A scoped Cesium ion token can
be configured in `web/.env.local` using `web/.env.example`. Without a token,
the map shows a labelled fallback while the form, text result, timeline and
JSON downloads work. No default evaluation token is used. The corrected Moon representation has a
reviewed regional registration; the engine supplies declared surface points.
Missing spacecraft trajectories remain unknown. See the Phase 5 guide below.

Phase 2 separates the immutable synthetic fixture analysis point from typed
draft coordinates and display-only surface picks. A surface pick creates a
labelled renderer marker without adopting its elevation or changing equipment
heights. Tile/render failures clear selections and preserve text results.
The form states its fixed absolute deadline rule and disables Earth-orbit
routing. Timeline endpoints retain their exact supplied timestamps and offsets;
scrubbing changes the map clock without starting analysis. See the
[Phase 2 interface checks](web/docs/phase-2-verification.md).

The interface is a **visual draft**, pending user design direction. Its
checked-in results come from Python, with hand-calculated relay allocations
kept as a separately labelled reference. The Phase 4 interface branch adds
the actual captured schedules and complete package downloads; its live client
has controlled tests for polling, cancellation, retry and stale responses.
The Phase 5 workflow connects the browser to the running service.

## Phase 3 illumination, power, contacts and scientific display

Python now evaluates a sampled solar disk with combined terrain/Earth masks,
fixed-panel electrical generation and explicit constant-bin battery replay.
Contact construction checks interval-wide geometry evidence, compatible radios,
both endpoint service calendars, acquisition/teardown and propagation. Assumed
rates remain labelled; an optional fully declared Friis/noise/mode budget checks
margin without overriding geometry or service. Phase 3 supplied these components
without selecting a schedule; Phase 4 now connects them to the bounded planner.

```sh
.venv/bin/python -m soma environment soma/docs/phase-2/geometry-diagnostic.json --generation-time-model left_sample_piecewise_constant_assumption
npm --prefix web run sync:science
```

The browser displays supplied horizons, Sun/Earth/station directions, solar
fractions, power and battery samples. It separates invented algorithm fixtures
from the recorded real LOLA site, where horizon gaps still yield unknown power.
Two saved delivery results can be compared under an explicit fixed-deadline rule;
missing schedule summaries stay Unknown. Scientific JSON downloads preserve the
engine output. No browser physics or registered Moon overlays were added.

See [Phase 3 methods and reproduction](soma/docs/phase-3/README.md) and
[interface verification](web/docs/phase-3-verification.md). Generation held
constant between samples is an explicit temporal approximation. The base-load
trace is not evidence that transmissions are affordable; energy must constrain
the Phase 4 scheduler, as implemented below.

## Phase 4 scheduler, service and exports

The engine constrains complete-file direct or single-lunar-relay delivery using
finite capacities, storage, both endpoint radios, arrival-time service, causal
forwarding and lander energy. PuLP/CBC distinguishes proven optimum, feasible
incumbent, proven infeasible discretized model and unresolved run. Independent
replay is required before a schedule can be released as feasible.

```sh
.venv/bin/python -m soma run fixtures/synthetic-direct/scenario.json --output-dir /private/tmp/soma-direct-run
.venv/bin/python -m soma run fixtures/synthetic-relay/scenario.json --output-dir /private/tmp/soma-relay-run
.venv/bin/python -m soma replay /private/tmp/soma-relay-run/run.json
.venv/bin/uvicorn soma.api.app:app --host 127.0.0.1 --port 8000
```

POST a complete scenario to `/plans`, poll `/plans/{id}`, cancel with DELETE,
and download the completed immutable `/plans/{id}/export`. Fresh spawned
processes isolate each job. Exports retain exact allocation epochs, source URLs,
input/source checksums and explicit units. CSV blanks mean unknown. The ZIP
contains no numerical raster, kernel or tiles. CZML has metadata only until
the frame-registration gate passes.

The [recorded runs](fixtures/phase-4/README.md) contain actual solver output:
the direct 100 MiB case is infeasible in the bounded model; the relay delivers
all bytes and passes replay, with `feasible_incumbent` and assumed-rate fidelity.
The fixed synthetic geometry/horizon supports software acceptance, not a lunar
site recommendation. Changed unsupported sites, heights, trajectories or
analysis extents remain unknown. Real LOLA horizon gaps remain unresolved.
No ground-time booking, flight DTN, thermal-survival or relay-certification
claim is made. The [Phase 4 evidence and reproduction guide](soma/docs/phase-4/README.md)
states the discretization, time-limit and coverage limits.

## Phase 5 live integration and map alignment

Start the engine and browser in separate terminals from the repository root:

```sh
.venv/bin/uvicorn soma.api.app:app --host 127.0.0.1 --port 8000
npm --prefix web run dev
```

Open `http://127.0.0.1:5173/`. The browser uses the same-origin `/api` proxy and
displays real job results, summaries and exact stored display samples. A changed
input creates a new scenario hash; canceled or older jobs cannot replace it.
Set `VITE_SOMA_MODE=fixture` explicitly for offline captured results. Live errors
never fall back to those captures. The complete ZIP preserves the native result,
exact CSV intervals and the same versioned display/registration artifacts served
by the job endpoints.

The live 100 MiB relay case passes replay and can be downloaded, independently
of map availability. A 16-byte input edit is genuinely rescheduled; unsupported
site coverage remains unknown. The declared relay fixture contains no trajectory,
so its selected spacecraft state stays Unknown. The browser does not invent one.

The engine corrects the observed coordinate conversion in the streamed Cesium
Moon v6 mesh, preserving attribution and numerical DEM inputs. Its versioned
DE421 mean-Earth bridge passes four independently searched terrain-feature
comparisons at the 5 m source-grid resolution. The measured 3D residuals are
below 0.3 m; adding the declared grid-resolution allowance remains below the
10 m acceptance tolerance. This is relative display registration, not an
absolute lunar navigation accuracy claim or an all-location/LOD guarantee.

The application uses the certificate only from 87.5°S to the south pole. Outside
that region, scientific overlays stay blocked. The contact-only relay fixture
still has no trajectory; the viewer displays its declared analysis point and
keeps spacecraft state Unknown. The [alignment method and reproduction guide](soma/docs/phase-5/map-alignment.md)
records the measured controls, conversion, sampled source fingerprints and limits.
The integration PR requires the repository owner's merge before Phase 6 begins.
See the [integration guide](soma/docs/phase-5/README.md) and
[interface evidence](web/docs/phase-5-verification.md).
