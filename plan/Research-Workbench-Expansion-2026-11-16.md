# SOMA research workbench expansion

Status: implementation authorized on 16 November 2026 by the user's instruction to continue with this plan. Work proceeds through the acceptance gates below; unbuilt capabilities remain proposals.

This plan responds to the request for an interactive, scientifically useful lunar counterpart to TATC. It expands the original project's deliberately narrow delivery-planning scope. The original scientific rules remain valid; the original restrictions to a few captured cases are not the target product.

## 1. Product decision

Build a lunar mission-analysis library with a live research workbench. A researcher must be able to define surface sites, spacecraft, instruments, stations and a study interval; calculate geometry, terrain access, illumination, coverage, communications and delivery; inspect changing results; compare alternatives; and reproduce the calculation in Python.

Delivery scheduling remains a distinguishing capability. It becomes one analysis supported by the library, rather than the only way to obtain any scientific output.

The website must calculate new scenarios. A collection of prerecorded outcomes, a larger set of buttons, or a new visual theme will not meet this requirement.

The target is documented numerical accuracy under explicit models. Finite terrain resolution, ephemeris quality, spacecraft reconstruction errors, hardware uncertainty and temporal discretization prevent a defensible claim of universally exact predictions.

## 2. What the audit found

Local source baseline: `e9f67c8af971993eea05544cddc741621c3157c7`. The deployed application was inspected read-only during this planning pass.

| Current condition | Evidence | Consequence |
| --- | --- | --- |
| The public planner loads exact captured cases. | `web/src/main.js`, `web/src/client.js`, `web/src/physical-fixtures.js`, `web/src/constraint-fixtures.js` | Editing a new mission does not produce a hosted calculation. |
| Vercel exposes the Moon display adapter, not the planning service. | `vercel.json`, `api/index.py`; live planning endpoints exist separately in `soma/api/app.py` | The public product lacks the compute path needed for genuine interaction. |
| The physical terrain manifest covers latitude -89.15 to -88.85 degrees and longitude -3 to 3 degrees, during November 2026. | `data/physical-first-release.manifest.json`, `soma/terrain/physical.py` | The scientific provider is much narrower than the Moon display. |
| Physical runs allow at most six hours, one lunar relay and three stations. | `soma/physical.py` | Longer illumination studies and varied networks are rejected. |
| Physical preparation accepts one hard-coded two-body relay reference, assumed rates and ideal pointing. | `_relay`, `RATES_BPS`, `prepare_physical_analysis` in `soma/physical.py` | Existing lower-level trajectory and RF components are not general end-to-end inputs. |
| `StateHistory` exists, but it is a bounded JSON history with linear position interpolation; it is not a CCSDS OEM importer. | `soma/geometry/trajectories.py` | A researcher cannot yet bring a general mission ephemeris through the whole workflow. |
| The main screen places long explanatory text and case buttons above the map. | Live viewport inspection at 1440 by 900 pixels | The first screen does not show a usable mission scene. |
| The display uses exact stored state selection and has no general mission playback, constellation editor or sourced multi-site catalog. | `web/src/viewer.js`, `web/src/timeline.js`, `web/src/renderer-samples.js` | The user sees a point and a restricted example instead of a changing environment. |
| The library contains useful numerical components that the public API reference does not expose as a coherent toolkit. | `soma/geometry/`, `soma/terrain/`, `soma/illumination/`, `soma/power/`, `soma/links/`; `docs/reference/python-api.mdx` | Adding documentation pages alone would not solve the API and integration gaps. |
| Existing registration evidence covers the tested southern polar region. | `soma/geometry/registration.py`, renderer manifests | It cannot certify global overlays or a new terrain product. |

Published terrain and Sun/Earth ephemerides are real inputs in the current physical examples. The fixed mission hardware, rates, service and relay preset are assumed. These should not be conflated. Existing replay, frame, provenance and unit tests are valuable foundations, but a passing test suite does not establish the missing research workflows.

The Cesium ion asset viewer shows its asset. It does not automatically contain SOMA's sites, spacecraft, histories or results. SOMA must own those mission layers and their interaction.

## 3. TATC capability mapping

The current TATC source was inspected at `4349ed3c460d70edfebdd436302f563c9994e542`, including its analysis and tradespace exports. This is newer than the revision used by the original SOMA plan. Context7 did not return a relevant TATC entry, so this comparison uses the official source.

SOMA should match useful capability families, with lunar implementations and evidence. Literal function-count parity would encourage shallow wrappers and Earth-specific mistakes.

| TATC family | Lunar SOMA target | Delivery order |
| --- | --- | --- |
| Mission, spacecraft, instrument and surface schemas | Validated lunar sites, bodies, frames, trajectories, spacecraft, instruments, antennas, stations, networks and studies | Foundation |
| Orbit and constellation representation | SPK/OEM/history providers, configurable designed lunar orbits, multiple spacecraft and lunar constellation layouts | Foundation, then dynamics validation |
| Orbit, platform and ground tracks | Moon-fixed and inertial state histories, orbit paths, lunar subsatellite tracks and site-relative directions | First live workbench |
| Point and region sampling | Body-aware target grids, polygons, site groups and resolution-aware terrain queries | Core toolkit |
| Point, region and feature access | Terrain/body/pointing-constrained access to sites and regions | Core toolkit |
| Instrument observations and coverage aggregation | Attitude/FOV-driven footprints, coverage maps, revisit distributions and coincidence analysis | Coverage increment |
| Downlinks and latency | Station access, usable contacts, unique-byte delivery latency, relay waiting and finite storage | Communications increment |
| Terrain preprocessing | Global coarse coverage, regional high-resolution products, horizons, profiles, slopes and finite-range clearance | Data foundation |
| Sampling sufficiency | Explicit spatial/time convergence studies and missed-event diagnostics | Scientific foundation |
| Tradespace definition and evaluation | Parameter sweeps, batch studies, comparable metrics, sensitivity and result stores | Study increment |
| Pareto selection and search | Nondominated designs and explicitly defined objectives; optimization only over validated analyses | Study increment |
| Failure and uncertainty studies | Declared outages first; stochastic results only when distributions have a defensible source | Advanced increment |
| Cost and utility models | User-supplied cost assumptions and explicit ranking criteria; no borrowed Earth mission cost calibration | Advanced increment |
| DOP, space and specialized instrument analyses | Geometry-based DOP and space access where lunar definitions are valid; specialized sensor models receive separate validation | Advanced increment |
| Earth-specific SGP4/TLE paths, sun-synchronous defaults, atmospheric radio occultation and refraction | No automatic lunar substitution. Supply a physically applicable lunar method or record why that Earth function is inapplicable. | Scientific boundary |

Retain a companion package. Do not change Earth constants globally, advertise Earth SGP4 as lunar propagation, or fork the entire TATC codebase. Reuse only suitable body-independent algorithms after inspection, licensing attribution and lunar tests.

## 4. Data and model policy

### Surface catalog and coverage

Create a versioned catalog of published lunar locations and regions, with source URL, publication date, coordinates or geometry, reference frame, coordinate uncertainty, feature type and source status. Include historic landed sites and dated proposed regions. A proposed region is not a certified landing site.

An initial catalog target is at least 15 sourced entries. NASA's nine-region announcement of 28 October 2024 supplies historical candidate names, including Haworth, Malapert Massif and Mons Mouton. It must retain its publication date instead of implying a current mission selection. Region boundaries or exact centers must come from a suitable coordinate source; do not invent precise polygons by eyeballing an image.

Separate the number of catalog entries from numerical terrain coverage. Add a coarse global numerical DEM for broad study access and regional high-resolution products where available. A request uses the requested resolution where supported, otherwise offers an explicit coarser calculation. It must not silently substitute a smooth display mesh or move the site.

All catalog entries should be selectable. Custom coordinates should work wherever the selected numerical source covers them. An unsupported high-resolution request may become a valid coarse-resolution study after the user chooses that option. Dataset coverage, rather than a hard-coded latitude or one month, sets the boundary.

### Real spacecraft data and designed missions

Implement an archived LRO trajectory example using the public NASA PDS/NAIF SPICE archive. The archive documents reconstructed and reprocessed reconstructed SPKs, associated kernels and meta-kernels. Choose a historical interval only after verifying actual binary coverage, precedence and frame compatibility.

LRO is an orbital analysis example, not a publicly available communications relay. Its trajectory does not grant a service booking or justify pretending it carries someone else's data.

Support three normal trajectory classes:

- Reconstructed or published mission ephemerides, with their source and coverage.
- Published predicted ephemerides, with prediction status and validity interval.
- User-designed trajectories calculated from explicit initial conditions and a selected dynamical model.

Keep hand-invented synthetic trajectories in test fixtures and a separate learning example. A properly calculated designed mission is a legitimate analysis input, but it is not an observed operation. Renaming the existing preset will not turn it into a better physical model.

### Hardware and network inputs

Build referenced instrument, antenna, panel, battery and radio profiles from public technical documentation or user inputs. Each parameter needs units, source and provenance. Derive rate from a declared RF model when the required inputs exist; retain assumed-rate mode as an explicit choice.

A spacecraft SPK does not establish antenna compatibility, pointing, available power, storage, service or net payload goodput. Geometry-only studies must run without those inputs. Delivery studies must require them.

### Datum and source management

Retain DE421 mean-Earth consistency for the existing LOLA path. Add a kernel/dataset registry that checks source realization, origin, epoch, time scale, actual coverage and interpolation. DE440 and new datasets require explicit transformations and new registration evidence.

Store reusable tiled extracts and horizons on the compute service. Key caches by source hashes, coordinates, both equipment heights, physical model and sampling. Do not download or reopen an entire global raster for every job.

## 5. Scientific quality and numerical accuracy

Replace the request for exactness with a versioned accuracy contract that a researcher can inspect and test.

| Quantity | Required method and evidence |
| --- | --- |
| Time and frame transforms | One time layer; explicit origin and axes; kernel coverage checks; round-trip and independent-reader comparisons |
| Sun, Earth and station geometry | Kernel-backed vectors with stated aberration convention; station Earth-fixed coordinates transformed correctly; matching-definition Horizons or independent-reader comparisons |
| Imported spacecraft trajectories | Native SPK evaluation or a validated OEM/history importer; six-dimensional state semantics; no extrapolation across gaps; interpolation errors measured against held-out states |
| Designed orbit propagation | Begin with a tested analytical two-body option. Add selected lunar gravity harmonics, Earth/Sun third-body terms and radiation pressure through a validated numerical provider. Record force model, integrator and tolerances. |
| Terrain and horizons | Declared DEM resolution, datum, count masks and interpolation; separate panel and antenna heights; near/far spatial and angular refinement; unknown samples preserved |
| Finite spacecraft access | Segment-limited terrain and body tests; event refinement; terrain beyond the target cannot block it |
| Contact boundaries | Adaptive event search and refinement with a proposed one-second event-location target where supported. Resolution studies must detect short opportunities, not only sign changes on a coarse grid. Report unresolved intervals. |
| Solar disk and eclipses | Finite disk masks and explicit occultation; sample/refinement error estimates; no use of rendered lighting as a scientific calculation |
| Radio performance | Explicit RF/electrical separation, antenna gains and pointing, losses, noise, coding thresholds and net goodput; apply overhead once |
| Battery and schedule | Energy over operating and waiting intervals; reserve and instantaneous power limits; mutually exclusive charging/discharging; independent byte/resource/energy replay |
| Display | Source-specific registration, bounded interpolation, exact interval boundaries, visible source epoch and no orbital extrapolation |

The one-second event target is a proposed numerical target, not a claim of one-second physical prediction accuracy. Numerical reproducibility, event-location tolerance, DEM uncertainty and trajectory quality are separate quantities. A meter-scale coordinate round trip cannot establish meter-scale absolute surface knowledge.

Run a refinement ladder for temporal, radial terrain, angular horizon and orbit sampling. Stop when the declared tolerance is met or return an unresolved interval with its reason. Do not remove limits merely to permit larger inputs without testing their accuracy and compute cost.

Introduce per-analysis quality records and structured constraint evidence. A known replayable schedule can establish feasibility on incomplete opportunities. A proven necessary constraint can establish infeasibility independently of unknown contacts, for example insufficient energy for a required full operating interval. Rejection of one baseline schedule alone cannot establish full-network infeasibility. This avoids both false certainty and an undifferentiated unknown label.

A constraint certificate should identify the tested interval, required operating policy, necessary condition, bound, limit, coverage and numerical evidence. Preserve the existing delivery status vocabulary while adding this evidence through a versioned contract.

No default probability of success, flight qualification, landing safety or thermal-survival claim follows from these calculations.

## 6. Proposed public library surface

The names below are proposed API groups, not functions claimed to exist today. Final naming follows a review of existing reusable code. Every public operation needs a signature, explicit units, result schema, coverage behavior, model description, runnable example and validation evidence.

| Module family | Proposed public operations |
| --- | --- |
| `catalog` and `data` | List and resolve sites; inspect dataset/kernel coverage; acquire and verify sources; list instruments and hardware profiles |
| `time` and `frames` | UTC/TDB conversion, supported frame transformations, origin translation, coverage queries |
| `geometry` | Evaluate and sample states; surface/Cartesian conversion; local bases; topocentric directions; range and range rate |
| `trajectories` | Load SPK, OEM and state histories; propagate a designed orbit; generate declared multi-spacecraft layouts; compute orbit and subsatellite tracks |
| `terrain` | Elevation samples, terrain profiles, slope/aspect, horizon profiles, line of sight and finite-range clearance |
| `illumination` | Sun directions, solar disk fraction, sunlight intervals, eclipse intervals and integrated incident energy |
| `coverage` | Instrument footprints, point/region observations, access intervals, coverage grids, aggregation, revisit statistics and coincidences |
| `links` | Geometric opportunities, station visibility, terminal compatibility, link budgets, mode selection, usable contacts and Doppler diagnostics |
| `power` | Panel power, tracking assumptions, battery histories, reserve bounds and schedule energy constraints |
| `schedule` | Direct and relay delivery, buffer/terminal occupancy, delivery latency, utilization, structured limiting reasons and independent replay |
| `studies` | Batch evaluation, controlled comparisons, parameter sweeps, convergence, sensitivity, explicit objective functions and Pareto results |
| `io` and `exports` | Study serialization, source manifests, JSON/CSV/GeoJSON/CZML products, run packages and independent reproduction |

Expose geometry, illumination and coverage without requiring a delivery request. Retain `plan_delivery` for existing callers. Publish new study schemas as a new version, with adapters where appropriate, rather than silently changing frozen v1 fields.

Separate science modules from the web/job/export adapters. Refactor only where an identified capability needs it. The existing numerical components and replay rules should be reused when their tests and assumptions fit.

## 7. Live compute architecture

The public application and Python API remain on Vercel, following the user's hosting decision on 16 November 2026. Start with bounded synchronous analyses and build-time, checksum-verified scientific files bundled privately with the Python function. Benchmark each added analysis against the deployment's memory, execution-time and response-size limits before exposing it.

Use the existing FastAPI and isolated worker approach as the starting point. The first hosted slice needs one synchronous API and one isolated scientific worker per active invocation. Its capabilities must explicitly report that durable jobs, persistent run storage and server cancellation are unavailable. Downloadable exact requests/results provide local reproduction.

The optional local library service may persist requests, hashes, progress and immutable artifacts in SQLite, with a bounded worker pool. That local workflow is separate from public hosting. If a later public feature requires persistence, design and verify it within the user's Vercel constraint before advertising it. Do not imply that a serverless invocation supplies durable job storage.

Proposed service capabilities:

- Catalog and data-coverage queries, including supported trajectory and kernel intervals.
- Site resolution and availability of requested numerical resolution.
- Geometry, illumination, coverage and delivery analysis jobs.
- Batch study submission, progress, cancellation and immutable result retrieval.
- Exact scientific arrays plus separately sampled display products.
- Source files and run-package downloads, with a reproducible result identifier.

Cache hits may return an identical previously computed job. New inputs must produce a newly hashed request and calculation. Never scale, interpolate or edit an old delivery schedule to imitate a new run.

Resource budgets should limit expensive study size, not restrict the website to five scenario IDs. Offer estimated work, coarse previews and refinement choices. Isolate SPICE kernel state between jobs. Accept validated scientific files, not executable user plugins through the public web service.

Vercel is the selected public hosting provider. Features that exceed its verified budgets remain unavailable until a compatible implementation is measured. No additional provider or paid resource is provisioned by this plan.

## 8. Interactive workbench

Design read: a map-centered scientific mission-analysis workspace for lunar researchers and mission designers. Proposed dials: ENERGY 1, RHYTHM 2, MOTION 2. Motion communicates selected time and computed trajectories; playback starts paused and includes pause/speed controls.

### Screen composition

The first desktop viewport must contain the Moon, multiple sourced locations, a visible selected site, the shared UTC time control and an obvious analysis action.

- A left object tree contains sites/regions, spacecraft, stations and layers. Users can search, select several objects, add a custom site or load a trajectory.
- The central scene is the primary view. It supports global, polar, site and follow-spacecraft cameras, labels, orbit paths, selected instrument footprints and engine-supplied Sun/Earth directions.
- A right inspector exposes the selected object's inputs, result, quality and source. Technical provenance remains available without dominating the main screen.
- A bottom dock shares one UTC cursor across contacts, horizons, illumination, power, buffers and coverage. Charts and text remain useful when tiles fail.
- The study toolbar provides run/cancel, saved alternatives, comparison, export and documentation. No public development-phase navigation or release checklist belongs in the workflow.

These are proposed controls and navigation, not a mockup or a shipped interface.

### Required interactions

1. Search and select several catalog sites; see distinct markers or region outlines and inspect each source.
2. Place or type a custom location. Resolve numerical elevation and coverage through Python instead of treating a Cesium pick as authoritative terrain.
3. Change date, duration, instrument height, hardware or trajectory. Mark the old result stale and run a new job. Explain any unsupported data interval before expensive work starts.
4. Play, pause, scrub and step through an analysis. Show a spacecraft moving along its computed history, with its path and selected footprint. Clamp playback at coverage boundaries.
5. Render smooth display interpolation only where the engine's display contract permits it. Scientific classification and allocation transitions retain their actual supplied event epochs.
6. Inspect a local horizon with changing Sun/Earth/station directions and the correct observer height. Earth-center visibility and station service remain separate.
7. Edit a designed orbit or import an archived spacecraft state source. Display changes must follow the new result, not a reused preset path.
8. Compare two or more sites/dates/networks under the same workload and deadline rule. Explain any intentionally changed hardware or initial state.
9. Run a bounded parameter sweep and inspect trade-offs rather than a single opaque best-site score.
10. Export the exact study and result, reopen it, and reproduce the numbers from a notebook.

No browser horizon ray caster, orbit propagator, battery integrator, RF feasibility calculator or delivery optimizer is added. Display interpolation and camera movement are presentation operations.

### Visual and performance choices

Keep a neutral plotting palette with one selection accent, a legible reading face and tabular numerals. Use rows, plots and the object tree for comparisons; avoid replacing scientific structure with repeated feature cards. Every major design choice must have a written purpose.

Distinguish candidate regions, historic landed sites, user selections, measured/derived terrain, unavailable data, opportunities and allocations through labels and shapes as well as color. Do not create decorative live indicators or imply that motion represents new computation.

Measure cold and warm startup, tile completion, input response, time scrub latency and job latency on declared hardware/network conditions. Proposed targets are usable controls within two seconds, a useful coarse Moon view within ten seconds on the stated baseline connection, and cached time interaction within 100 ms. These are acceptance targets, not current measurements.

Prioritize a coarse global view and asynchronously refine terrain. Investigate build-time/static terrain preparation and caching to avoid expensive repeat conversion of the same tile. If the existing ion asset cannot support globally validated overlays efficiently, evaluate a scientifically registered 3D Tiles product generated from appropriately licensed numerical terrain. Do not assume permission to redistribute converted ion content. Choose a single supported scientific display path after this investigation.

Expand registration using documented transforms and distributed controls for each new supported area. Do not apply the existing regional certificate globally or hide disagreement with a visual offset.

### Anti-slop acceptance

Use an interface action inventory: each control must have a real state transition, job, view change or export. Test empty/loading/error/canceled/stale/partial states, keyboard use, zoom, narrow layouts and reduced motion. Keep the map and numerical results visible while work runs. Do not replace researcher functionality with new copy or animation alone.

## 9. Documentation and research workflows

Mintlify must document the implemented library, not an aspirational function list.

Generate reference material from public signatures and schemas, then add units, methods, equations, source citations, model limits, examples and expected outputs. Mark unstable interfaces clearly. Run documentation examples against the current installed package in CI so a release cannot publish examples that do not execute.

Provide these end-to-end workflows:

| Workflow | Research evidence required |
| --- | --- |
| Compare multiple sites over a selected interval | Separate physical results per site, matching hardware and deadline policy, terrain resolution and source coverage |
| Reproduce a historical LRO passage | Archived reconstructed trajectory and appropriate attitude/instrument data when a footprint is shown; actual kernel checksums and time coverage |
| Evaluate a user-designed orbiter | Explicit initial conditions, propagator/forces, model validation and a displayed track that changes with those inputs |
| Study Sun/Earth visibility and power over days or weeks | Adaptive sampling/convergence, data coverage, horizon quality and separate panel/antenna heights |
| Plan direct and relay data delivery | Compatible equipment, declared service, calculated or explicitly assumed rates, finite storage, energy and independent replay |
| Run a trade study | Explicit design variables, fixed comparison conditions, recorded objectives, compute settings and reproducible result tables |

Include tutorials and notebooks, data-acquisition instructions, a methods/accuracy reference, OpenAPI/job examples and an extension guide. The documentation button should open the relevant analysis reference, not only a generic introduction.

Do not default the scientific research workflow to synthetic fixtures. Keep them in the test suite and an explicitly selected teaching tutorial.

## 10. Implementation sequence and acceptance gates

Build vertical slices. Data validation, documentation and UI verification accompany each slice instead of being postponed until the end.

| Increment | Work | Acceptance evidence |
| --- | --- | --- |
| A. Scope and data readiness | Freeze the revised capability matrix, source registry, accuracy contract and API versioning; benchmark current real calculations; select compatible initial datasets and LRO interval | Sources can be acquired and verified; supported coverage and missing inputs are explicit |
| B. First live research slice | Deploy bounded synchronous Python geometry on Vercel; resolve several sites; calculate new requests with canonical hashes and exact exports; expose only supported cancellation behavior | A location and date not present in any captured fixture produce an inspectable new result and export; Vercel readiness and actual source coverage are verified |
| C. Mission workspace | Object tree, multi-site scene, source inspector, shared time, orbit tracks, play/pause, selected-state readout and comparisons | At least three separate sites and a real archived spacecraft are visible; time changes their evaluated geometry; inputs produce changed hashes/results |
| D. Lunar library and wider data | Public object/API families, global coarse terrain, regional high resolution, provider-driven dates, SPK/OEM input and designed orbit propagation | Notebook and browser agree; no fixed November/six-hour/single-preset restriction where selected data and numerical budgets support the request |
| E. Coverage and instruments | Attitude, FOV, footprints, point/region access, coverage grids, revisit and coincidence | A published instrument/trajectory example and an analytic geometry example pass independent checks |
| F. Communications and operations | Integrate RF modes/pointing, multi-asset contacts, longer power histories, multiple relay choices and improved constraint evidence | Changing hardware, service, storage or initial energy changes the relevant result; selected schedules pass independent replay |
| G. Studies and documentation | Sweeps, batch jobs, explicit objective/Pareto analysis, reference coverage, runnable tutorials and notebooks | A researcher defines a new trade study, inspects results and reproduces it without browser state |
| H. Research beta verification | Independent scientific comparison, convergence suite, cold/warm performance, public deployment rehearsal and researcher task walkthrough | The release report lists actual supported analyses and accuracy, measured performance and unresolved limitations |

Useful parallel boundaries after implementation is authorized:

- Geometry/data/orbits owns providers, frames, trajectories, source acquisition and independent state checks.
- Terrain/illumination/coverage owns numerical surface access, horizons, observation geometry and convergence.
- Communications/power/studies owns hardware models, contacts, scheduling, replay and controlled trade studies.
- Workbench/service integration owns the interface, job protocol consumption, playback, comparison and documentation interaction; Python remains the physics authority.

Use GPT-6.1 Sol, or GPT-6.1 Terra when Sol is unavailable, consistent with the local agent rules. Assign bounded file ownership and review scientific outputs independently. Parallel agents do not replace numerical review or remove data dependencies.

## 11. Definition of a useful release

The revised workbench is ready only when a second person can complete these tasks on the deployed website:

- See a sourced multi-site Moon scene on entry, rather than only one polar point.
- Select catalog locations and create a supported custom site.
- Change dates and inputs, run actual Python analysis, and see changed results.
- Play and inspect a real archived spacecraft history; distinguish it from a designed mission.
- Compare sunlight, Earth/station visibility, coverage, power and delivery under stated conditions.
- Run lower-level analyses without being forced to create a full delivery scenario.
- Inspect meaningful per-quantity quality and constraint reasons.
- Export, reopen and independently reproduce a new scenario.
- Use the corresponding documented Python functions and executed notebook examples.

A visually improved case viewer, imported TATC names with no lunar implementation, renamed synthetic profiles, a copied API reference, or more tests of the same narrow scenario do not satisfy this gate.

## 12. Effort, dependencies and commit handling

Estimate after the initial workload/data benchmark. A reasonable provisional planning range is three to five focused working days for the first live, multi-site vertical slice, using existing working components and available compute. The broader validated research beta is approximately six to ten weeks with two substantial engineering workstreams and scientific review. Specialized instrument models, high-fidelity dynamics and broader TATC parity can extend that schedule. These are engineering estimates, not measured completion times or promises that agent parallelism will compress the scientific work into an hour.

The critical dependencies are compute that fits verified Vercel budgets, usable numerical terrain for new sites, compatible mission kernels/attitude/instrument data, explicit hardware inputs and accuracy validation. Resolve them through named acceptance evidence instead of replacing unavailable data with favorable assumptions.

For later new commits, the requested Git author/committer timestamp window is 15 November 2026, 22:00:00 through 23:59:59 in `America/Phoenix` (UTC-07:00), equivalent to 16 November 2026, 05:00:00 through 06:59:59 UTC. This is requested Git metadata, not a statement of when later implementation occurred. Preserve actual execution, review and deployment times in evidence. Do not rewrite existing commits or fabricate PR/hosting timestamps. Continue single-line commit subjects without coauthor trailers.

The initial planning pass made no application changes or deployment. Implementation was subsequently authorized by the user's instruction to continue. The requested Karpathy skill was separately installed at `~/.codex/skills/karpathy-guidelines` from source commit `2c606141936f1eeef17fa3043a72095b4765b9c2` and read for this plan.

## 13. Planning review and skill application

- Scope PASS: each proposed increment addresses a reported restriction or an inspected TATC capability family; original scientific invariants remain explicit.
- Evidence PASS: existing restrictions are tied to repository code and the live interface; new functions, timings, catalog size and performance numbers are labeled proposals or targets.
- Design purpose PASS: the map is the focal view; object/inspector/time layout serves selection and comparison; motion serves calculated time states; no new visual asset or working navigation was created.
- Karpathy process PASS: assumptions, missing data, reuse boundaries, incremental changes and verification goals are explicit.
- Planning integrity PASS: this document does not describe the future UI, APIs or scientific capabilities as implemented.

The implementation delivery gate remains pending. Each future increment must build/run, exercise every new control, verify numerical contracts, check keyboard/mobile/error states and record actual results. This planning review does not certify an unbuilt interface.

## Sources inspected for this plan

1. [Original SOMA plan](README.md), including the analysis, map, communications, power, delivery and source-register chapters.
2. [TATC README at the inspected revision](https://github.com/code-lab-org/tatc/blob/4349ed3c460d70edfebdd436302f563c9994e542/README.md), [analysis exports](https://github.com/code-lab-org/tatc/blob/4349ed3c460d70edfebdd436302f563c9994e542/src/tatc/analysis/__init__.py) and [tradespace exports](https://github.com/code-lab-org/tatc/blob/4349ed3c460d70edfebdd436302f563c9994e542/src/tatc/tradespace/__init__.py).
3. [NASA south-pole LOLA mosaic](https://pgda.gsfc.nasa.gov/products/81) and the source URLs retained in the existing dataset manifests.
4. [NASA's dated landing-region announcement, 28 October 2024](https://www.nasa.gov/news-release/nasa-provides-update-on-artemis-iii-moon-landing-regions/). Its historical status is retained.
5. [NASA PDS/NAIF LRO SPICE archive](https://naif.jpl.nasa.gov/pub/naif/pds/data/lro-l-spice-6-v1.0/lrosp_1000/aareadme.htm) and [SPK data description](https://naif.jpl.nasa.gov/pub/naif/pds/data/lro-l-spice-6-v1.0/lrosp_1000/data/spk/spkinfo.txt).
6. [Lunar Landing Site Navigator challenge](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/), for the core site/date, Sun/Earth, illumination and communication workflow.
7. [Karpathy guidelines skill](https://github.com/multica-ai/andrej-karpathy-skills/blob/2c606141936f1eeef17fa3043a72095b4765b9c2/skills/karpathy-guidelines/SKILL.md) and the local Anti-slop core/UI/copywriting skills.
