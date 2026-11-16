# Implemented capability inventory

Audit date: 17 November 2026. Package version: 0.1.0. This inventory follows actual exports, source branches and test contracts. It separates reusable Python operations, provider integration, public HTTP exposure and workbench controls. It does not count wrapper aliases as extra scientific capabilities.

## Scope and sources

Read `soma/__init__.py`, `soma/engine.py`, the `geometry`, `time`, `terrain`, `illumination`, `power`, `links`, `schedule`, `exports`, `research` modules, validation, preparation and current API adapters. Required plan chapters and the research expansion's workbench/scientific rules remain the interpretation boundary. Function signatures were inspected directly with Python `inspect.signature`, including generated dataclass constructors.

The original root `soma.plan_delivery` is a lazy wrapper for `soma.engine.plan_delivery`; both return the same native delivery result. `plan_run` is the richer run/evidence entry point. They are not three distinct planning algorithms.

## Public library inventory

| Family | Implemented entry points | Principal bounds / caveats | New documentation |
| --- | --- | --- | --- |
| Surface geometry | `SurfacePoint`, `surface_position`, `local_basis`, `vector_direction`, `segment_intersects_sphere`; position/inverse/basis methods | Planetocentric latitude/east longitude, explicit lunar frame and reference sphere, separate heights, pole meridian. No DEM or RF conclusion from pure coordinates. | `docs/reference/geometry-time.mdx` |
| Kernel geometry/time | `SpiceGeometry.state`, `.direction`, `.station_state`, `.transform_position`; `parse_utc`, `format_utc`, `soma.time.spice.utc_to_et` | Matched local kernels/hashes/actual coverage, context/thread ownership, Moon origin, explicit axes, NONE aberration. Station geometry additionally requires ITRF93/WGS84 and Earth PCK. Position transform is not origin/velocity transformation. | `geometry-time.mdx` |
| Trajectories | `StateHistory(...).state`, `SyntheticTwoBodyLunarPreset(...).state`; configured native LRO provider through `analyze_study` | JSON history only, explicit units/gaps/no extrapolation. Synthetic conic <=7 days, no high-fidelity/libration dynamics. Native SPK study source is explicitly configured, not an arbitrary importer or relay booking. | `docs/reference/trajectories.mdx` |
| DEM / horizons / finite range | `RasterDEM`, `GeographicRasterDEM`, `SyntheticDEM`, `CompositeDEM`, `TerrainSample`; `HorizonSite`, `HorizonSampling`, `HorizonBand`, `HorizonProfile`, `HorizonCache`; `build_horizon`, `horizon_cache_key`, `finite_segment_visibility`, `SegmentVisibility` | Strict aligned meter/count grids and matched frame; missing remains unknown. Distinct strict measured-count and declared physical published-grid policies. Horizon <=2M workload; finite segment defaults <=100000 samples. No infinite-horizon substitution for finite spacecraft. | `docs/reference/terrain.mdx` |
| Illumination | `solar_disk_visibility` | Uniform sampled disk, shared terrain/Earth ray masks, unknown/convergence provenance. Unknown-ray bounds are not total quadrature/DEM accuracy bounds. | `docs/reference/illumination-power.mdx` |
| Electrical power | `fixed_panel_power`, `integrate_battery` | Fixed normal only, center-projection approximation. 1 to 100,000 contiguous constant-power bins, bus-side W versus RF W, reserve/power/efficiency/curtailment, unknown propagation. | `illumination-power.mdx` |
| Communications | `evaluate_geometry`, `link_budget`, `assess_contact` | Single-epoch geometry versus required interval-wide contact evidence; declared binary RF mode/noise/losses and overhead once; explicit ideal pointing/service/delay. Capacity is not a complete schedule. | `docs/reference/communications.mdx` |
| Scheduling / replay | `solve_schedule`, `replay_schedule`, `plan_run`, `plan_delivery` | Complete-file direct or one selected lunar relay. At most 5,000 nominal bins, 32 chunks, 64 contacts, 25,000 candidates and 8 million candidate/bin pairs. Finite resources, receiver timing, causal forwarding and lander energy; high-level feasibility requires replay. Unknown alternatives block full-network infeasibility/optimality claims. | `docs/reference/scheduling.mdx` |
| Validation | `load_json`, `validate_document`, `validate_documents`, `validate_scenario`, `load_scenario`, `scenario_sha256`, `data_volume_bytes`, `schema_registry`, `resource_directory`; `ScenarioValidationError` | Strict JSON/units/UTC, bounded safe numbers, local schemas. Structural validity and hashing do not establish physical feasibility. | `docs/reference/validation-exports.mdx` |
| Export | `json_bytes`, `summary`, `display_payload`, `explanation`, `create_run_package`; `soma.exports.display.display_data`, `renderer_registration` | Exact native run structures; summary metrics gated on passed replay, unknown not zero, frame registration retained. ZIP construction does not repair/replay a schedule. | `validation-exports.mdx`; existing `exports-replay.mdx` |
| Studies/catalog | `validate_study`, `study_sha256`, `runtime_capabilities`, `analyze_study`; `site_catalog`, `resolve_site`; `StudyValidationError`, `StudyCancelled` | Geometry only in frozen study v1: 1 to 8 sites, at most 31 days, step at least 10 s, at most 2,000 epochs and 5,000 site-epoch pairs, actual source coverage. Explicit separate heights, native LRO six-dimensional output. | Existing `docs/reference/research-api.mdx` |

The data models in this table are included because they define required arguments and returned evidence, not to inflate an algorithm count. Registration calibration/mesh-correction internals and service/job-store helpers are implementation infrastructure, not general user-facing lunar analysis functions.

## Exposure and integration audit

- Public Vercel geometry exposes catalog/capabilities and bounded synchronous `POST /api/research/analyze`. The current workbench reads the returned arrays; it does not evaluate terrain, disk fraction, power, RF or delivery in JavaScript.
- The local planning service's `/plans` jobs, CLI and full `plan_run` implement delivery with preparation, MILP and replay. General helper availability does not mean every helper is an individually exposed REST operation.
- The existing physical provider is still region/date bounded: -89.15 to -88.85 latitude, -3 to 3 east longitude, November 2026 and at most 6 hours; assumed net rates/ideal pointing, at most 1 configured synthetic relay and 3 stations. Global reference-sphere geometry is broader geographically but computes fewer physical quantities.
- The reusable `link_budget` is implemented and can gate `assess_contact`. However `prepare_physical_analysis` currently rejects `rate_method != assumed_net_rate`; arbitrary RF hardware is not integrated end to end into that provider.
- At the 17 November module audit, a fresh Vercel delivery route was under separate implementation/verification. The deployment update below records the subsequent measured exposure; no endpoint or UI is inferred from a proposed registry entry.
- LRO SPK provenance establishes trajectory geometry, not relay service, terminal compatibility, allocated power/storage, attitude or an instrument footprint.

## Important implementation/documentation discrepancies found

Deployment update, 18 November 2026: preview deployment `AXkxtJTCwVQgH9yVRAJnnS3p2Qrt`
at commit `63ff67f` built on Linux with 11 verified delivery sources totaling
133,092,198 bytes, a successful CBC integer smoke solve, and runtime readiness.
A fresh Data delivery calculation returned a replayed 16 MiB assumed-rate
incumbent. Its browser-downloaded native ZIP passed all 72 independent export
checks on the local verifier. The public HTTP operations are
`GET /api/research/delivery/capabilities` and `POST /api/research/delivery/analyze`.
They use the corrected complete-window `physical-lola-de421-v2` dataset and the
bounded synchronous contract; they do not add a durable job registry or complete
RF-budget integration. Existing v1 inputs and archived runs retain their original
hashes. Publication verification is recorded separately from this module audit.

1. `StateHistory` requires/stores velocity arrays, but `state()` currently returns only the position record. The class docstring's phrase about reported velocities must not be read as a six-dimensional public output. The new reference describes the actual returned fields.
2. The `soma.time` module's older top-level docstring says UTC/TDB conversion is unimplemented; `soma.time.spice.utc_to_et` is implemented through the active LSK. The new reference distinguishes strict civil parsing from SPICE conversion without changing engine source.
3. A physical pipeline using real DEM/ephemerides can still be an assumed-rate simulation. It must not inherit the reusable RF helper's stronger fidelity label automatically.
4. An angular Sun-center plot in the global study is not the finite-disk terrain illumination or battery calculation already present elsewhere in the library.

## TATC breadth comparison

Root independently consulted TATC's official 3.6.0 [API reference](https://tatc.readthedocs.io/en/latest/api_reference/index.html) and [analysis families](https://tatc.readthedocs.io/en/latest/api_reference/analysis/index.html), plus the pinned Earth-observing source used by the original plan. The new `docs/science/capability-matrix.mdx` compares families rather than pretending function-name counts establish parity.

Missing general workflows include instrument/attitude catalogs and FOV footprints; target grids/polygons and region/feature/space coverage; revisit/statistical sufficiency/coincidence; generic ground/subsatellite-track products; arbitrary SPK/OEM mission import; validated high-fidelity designed dynamics and constellations; broad station/network/radio integration; batch/trade/Pareto studies; DOP/radio occultation/limb sounding; defensible stochastic success probabilities. Earth SGP4/TLE, atmosphere and Earth-calibrated cost/orbit assumptions are not automatic lunar implementations.

## Evidence and runnable examples

All Python example blocks in the seven new module pages are complete executable examples; API signature blocks use `text` fences. They run from the repository with relevant extras and, for the prepared-kernel example, existing hash-pinned `api/_data` sources. Synthetic examples are labeled and are software checks, not mission predictions.

Executed all 13 Python example blocks successfully on 17 November 2026 using `.venv/bin/python /private/tmp/soma-capability-doc-examples.py`. Saved output: `/private/tmp/soma-capability-doc-examples.log`. The helper extracts the seven pages' `python` fences, parses each with `ast.parse`, and executes each in a fresh globals dictionary. Signature-only fences are excluded. To repeat without that temporary helper:

```sh
.venv/bin/python - <<'PY'
from pathlib import Path
import ast, re
pages = ('geometry-time', 'trajectories', 'terrain', 'illumination-power',
         'communications', 'scheduling', 'validation-exports')
count = 0
for page in pages:
    source = Path('docs/reference') / (page + '.mdx')
    for block in re.findall(r'```python\n(.*?)\n```', source.read_text(), re.S):
        ast.parse(block)
        exec(compile(block, str(source), 'exec'), {})
        count += 1
assert count == 13
print(f'{count} examples passed')
PY
```

The examples assert separate surface/equipment heights and inverse conversion; pinned-kernel Earth position units/origin; UTC offset normalization; bounded synthetic history interpolation; converged synthetic horizon bands; partial disk visibility; 160 W synthetic panel arithmetic; battery energies `[50, 58, 48]` Wh; 800,000 net bit/s RF arithmetic; 307,200,000-bit assumed-rate contact capacity; complete 104,857,600-byte synthetic relay delivery and independent replay; canonical hash/volume checks; native ZIP signature, byte stability for the same run and exported byte count.

Relevant source-contract regression checks:

```sh
.venv/bin/pytest -q tests/engine/test_geometry.py tests/engine/test_time.py tests/engine/test_trajectories.py tests/engine/test_horizons.py tests/engine/test_terrain.py tests/engine/test_illumination.py tests/engine/test_power.py tests/engine/test_links.py tests/engine/test_link_budget.py tests/engine/test_contract.py tests/engine/test_research_contract.py tests/engine/test_research_catalog.py
```

Result: **199 passed in 4.63 s**, no skips. Saved output: `/private/tmp/soma-capability-doc-tests.log`. The eight new public pages contain 62 links: 38 GitHub source/test links, 21 internal page references and 3 external primary references. Static checks found no missing local source/page target, unbalanced code fence or trailing whitespace. The external reference checks are separate from local target validation.

These checks establish runnable examples and source consistency. They do not verify a new deployed delivery endpoint, full lunar scientific accuracy or rendered Mintlify layout. Root owns navigation, documentation build/publish and public runtime verification. No implementation or test was changed by this documentation task.
