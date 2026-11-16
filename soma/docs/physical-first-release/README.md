# Physical first release

The required bounded first release in `plan/` now has a terrain/ephemeris input
path feeding the same energy-constrained delivery scheduler, independent replay,
service and interface. The recorded demonstration uses one numerical LOLA site
and two operating dates. It is an assumed-rate planning model, not an operational
mission prediction. Optional Phase 7 extensions are not implemented.

## Reproduce the physical demonstration

Install the full stack from the repository root using Python 3.12 or newer:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --editable '.[analysis,planning,service,verification,test]'
.venv/bin/python -m soma fetch-geometry-data --data-root /private/tmp/soma-phase2-data --physical
SOMA_DATA_ROOT=/private/tmp/soma-phase2-data .venv/bin/python soma/docs/physical-first-release/reproduce.py --output-dir REPRODUCED_PHYSICAL_RUNS
.venv/bin/python -m soma.verification.exports REPRODUCED_PHYSICAL_RUNS/relay-later/run.zip
```

Acquisition is an explicit network operation. It obtains matched kernels and
bounded elevation/count extracts; hashes, parent URLs, coverage and quality
conventions are recorded in the data manifests. Source binaries stay local.
The small polar patch uses verified byte ranges rather than a full 3.5 GB parent.
The original near/count acquisition can download the compact count parent.

To use the interface, run the following in separate terminals:

```sh
SOMA_DATA_ROOT=/private/tmp/soma-phase2-data .venv/bin/uvicorn soma.api.app:app --host 127.0.0.1 --port 8000
```

```sh
npm --prefix web ci
npm --prefix web run dev
```

Open `http://127.0.0.1:5173/` in live mode. Select a **Physical** network example,
press **Plan delivery**, and inspect the numerical location, Sun/Earth horizon,
power, contacts, allocations, storage, battery and exact stored state samples.
The optional registered Moon needs the existing scoped local token. Without
tiles, the numerical result, graphics, comparison and download remain available.

The local service has finite job and byte retention. Export runs you need to
keep; restart the local service when its stated retention limit is reached.
A failed job displays its error and is not replaced by a captured success.

## Recorded controlled comparison

Both dates use latitude −89.03093035536243°, east longitude 1.389336784014743°,
the same 16 MiB file, hardware, 80 Wh initial battery, 10 Wh reserve, three
educational station proxies and declared network. Readiness is 08:00 UTC and
the deadline is six hours later. The operating date, finite service calendars
and synthetic trajectory coverage move together; this is the same mission-age
deadline rule rather than an extra delivery allowance for one date.

| Case | Computed result | Final byte arrival UTC |
| --- | --- | --- |
| November 24, direct only | Feasible under assumptions, proven optimum in the discretized direct model | 08:10:01.201519 |
| November 30, direct only | Infeasible in the discretized model; zero usable direct capacity | Unknown |
| November 30, configured lunar relay enabled | Feasible incumbent; full-network optimality unproved | 09:37:01.238933 |

The later direct case has zero available payload bits for a 134,217,728-bit file.
The relay run sends the file to the relay, waits after byte availability, then
forwards it to the ground network. Minimum replayed battery energy is about
46.11 Wh. Numerical geometry and terrain produce 9.65–9.66 W modeled generation
on November 24 and zero generation on November 30 for the declared fixed panel.
These are computed outputs; the requests do not encode a favorable schedule.

Archived results and exact ZIP hashes are in
[`fixtures/physical-south-pole/`](../../../fixtures/physical-south-pole/README.md).
An independent non-author agent verified and reoptimized all three archives.
This is automated review, not a separate human usability study.

## Terrain, timing and trajectory model

The engine resolves ground elevation to −301.98974609375 m in the declared
DE421 mean-Earth frame at a positive-count 5 m source pixel. Panel and antenna
heights remain separate. Each release horizon uses 1° azimuth samples, 5 m
near-field steps, 120 m far-field steps, and extent checks through 250 km.
The last extent increment changes the sampled skyline by zero at this site.
Under the explicit 12 km global height cap, the omitted outer terrain envelope
lies below every sampled band. That cap is an assumption, not a measured global
accuracy guarantee.

Finite published interpolated heights are model terrain with count-mask quality
preserved. Coarse fallback is explicit. The release horizon has zero unresolved
samples in this selected model; strict measured-only sampling still has 11,988
unknown samples per height. About 18.6% of samples carry interpolation flags and
82.5% carry coarse-source flags; these flags overlap. Actual NaN/nodata and
unresolved coverage remain unknown. The original strict diagnostic readers are
unchanged. Four scalar reference directions agree with the vector implementation
within 1.08×10⁻¹⁰ degrees, using shared source data and geometry primitives.

Finite spacecraft paths test only the segment to the target, using 5 m sampling
through the first/last 5 km and 120 m far-field sampling inside an assumed
12 km terrain envelope. Source windows are transmit UTC; constant conservative
delay is applied separately to receiver service, occupancy and byte availability.
Observed geometry transitions are refined to two-second brackets. Clear contact
bins require endpoint and midpoint samples and outer guards. Those assumptions
do not prove continuous visibility or exclude every short unsampled event.

The preset named `soma-polar-200km-v1` is a synthetic conic about Moon-centered
J2000 axes: semimajor axis 1,937,400 m, eccentricity 0.01, inclination 90° about
J2000 axes, node/periapsis/initial mean anomaly zero, GM 4.902800066×10¹² m³/s²,
and epoch equal to the requested horizon start. J2000 inclination is not an
inclination relative to the lunar equator. It omits nonspherical gravity,
third-body dynamics and radiation pressure, and is not a frozen or operational
relay orbit. States are exported at exact stored epochs and transformed into
the registered display frame by the Python exporter.

The 60/30-second sampling comparison preserves the tested contact topology and
feasibility, with a maximum common contact-boundary difference of 45 seconds.
The guard scales with the sampling step and both values are recorded. Different
time-limited incumbents do not establish a finer-grid completion optimum.
Representative future-receiver checks give angular differences below 0.006°,
less than the declared 0.1° station margin; these are not interval-wide bounds.

## Required plan coverage

| Plan requirement | Delivered evidence |
| --- | --- |
| Part 1: companion engine, matched frames/time/kernels, numerical terrain and declared trajectories | Existing geometry checks plus `soma/physical.py`, pinned near/far/polar manifests and terrain verification. |
| Part 2: Moon configuration, registered coordinates, service-resolved point, one immutable timeline and fallback | Regional registration retained; engine-authored renderer samples and exact UI sample control; physical browser walkthrough. |
| Part 3: generated opportunities, usable contact gates, delay, finite storage/radios, constrained scheduling and replay | Three physical archives and independent reoptimization; unknown contacts cannot support infeasibility or full optimality claims. |
| Part 4: separate horizons, disk illumination, panel power, battery constraints and controlled site/date comparison | November 24/30 comparison; terrain/sampling evidence; existing power and illumination tests and sensitivity cases. |
| Part 5: same Python/service engine, cancellation/stale protection, complete exports and reproducibility | Existing service acceptance plus physical live browser checks, canonical ZIPs and exact reproduction commands above. |
| Part 5 demonstration: direct success, controlled date failure, relay waiting/forwarding, exact export | `direct-ready`, `direct-later`, and `relay-later` computed archives. |
| Part 6 source register and attribution | Existing source/license audit; new polar source metadata; external binaries excluded. |

Run the completion and regression checks:

```sh
.venv/bin/python -m soma.verification.physical_completion
.venv/bin/python -m soma.verification.completion
.venv/bin/pytest tests/engine -q
npm --prefix web test
npm --prefix web run build
```

The challenge Details and Resources were reread through Aside on November 15,
2026. The bounded site/date, Sun/Earth horizon, power and direct-communications
workflow addresses its central task; relay scheduling is SOMA's extension.
No challenge submission, award, NASA endorsement, flight certification,
ground-service booking or operational relay access is claimed.

Arbitrary global coverage, long seasonal analysis, optional Earth-orbit routing,
additional hardware presets, earliest-delivery policy controls and a terrain
ensemble remain outside this required first release. Public hosting of corrected
ion content remains a separate usage decision; local verification grants no new
vendor or redistribution rights.
