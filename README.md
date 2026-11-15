# SOMA: A Research-Grounded Lunar Communications Planner

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
.venv/bin/python -m pip install --editable '.[test,analysis,verification]'
.venv/bin/python -m pytest tests/engine -q
.venv/bin/python -m soma validate fixtures/synthetic-direct/scenario.json
.venv/bin/python -m soma validate fixtures/synthetic-relay/scenario.json
.venv/bin/python -m soma plan fixtures/synthetic-relay/scenario.json
```

The library entry point is `from soma import plan_delivery`. The CLI emits
JSON to stdout and rejects invalid inputs with a nonzero exit code and a
diagnostic on stderr. It works without a browser. The planner currently returns
`unknown`, `unresolved`, and `not_implemented`, with empty computed histories
and `null` delivery metrics. Illumination, power integration, usable contacts,
optimization, independent schedule replay, the HTTP service, and display
exports are not implemented in the delivery pipeline. Phase 2 geometry and
terrain diagnostics are available separately, as described below.
There is no service start command at this phase.

The [direct fixture](fixtures/synthetic-direct/README.md) proves by arithmetic
that the supplied 256,000 net bit/s contact cannot carry 100 MiB. The
[single-relay fixture](fixtures/synthetic-relay/README.md) records the
419.4304 s uplink, storage wait, and 83.88608 s downlink expected from the
plan's invented example. These are hand calculations, with propagation
disabled only for the arithmetic test. Energy feasibility and solver
optimality have not been evaluated. `expected.json` is never loaded as the
planner's output. To run the fixture/schema checks alone:

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

