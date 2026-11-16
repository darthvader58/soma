# Live geometry workbench verification

Implementation and verification performed on 16 November 2026 (America/Phoenix).
This report covers the first live research increment in
[the expansion plan](../../../plan/Research-Workbench-Expansion-2026-11-16.md).
It does not certify the full research beta or general TATC feature parity.

## Implemented scope

- A new additive `1.0.0` geometry-study request/result contract; delivery v1 remains unchanged.
- New site/date calculations using matched, checksum-pinned DE421 SPICE sources.
- Fifteen published locations: six NASA Apollo landing coordinates and nine USGS crater centers.
- Native reconstructed LRO SPK sampling over its actual March–June 2026 coverage.
- Multi-site selection, custom coordinates, separate equipment heights, source inspection,
  UTC playback, bounded display interpolation, stored-state readouts, plots and exact JSON exports.
- Synchronous Python compute on Vercel with private source bundles, input/result/time budgets,
  isolated SPICE workers and explicit unavailable durable-job capabilities.
- Optional local SQLite-backed research jobs and reproducible Python examples.

The captured delivery interface remains at `/?mode=archive`. It is not a fallback
for unsupported research inputs. Global markers use assumed zero elevation on the
reference sphere; the old regional terrain-registration certificate is not applied globally.

## Verification

| Check | Actual result |
| --- | --- |
| Full engine suite after serverless startup fix | 445 passed, 0 failed, 0 skipped; 261.52 s |
| Web unit suite after first-visible tile handoff | 97 passed |
| Archive/workbench browser suite after loading/camera refinement | 28 passed |
| Real-source browser study | Passed: 15 catalog records, native LRO playback, new 21.1827° N / 68.2714° E site, 1.7 m panel, changed hash and exact download |
| Web production build | Passed |
| Mintlify validation and anchor checks | Passed |
| Current archived evidence bindings | All 436 match; original scientific scope and counts retained |
| Local actual hosted-adapter HTTP | 3 sites × 1,441 epochs plus LRO: HTTP 200, 2,639,953 bytes, 1.322 s |
| Private source and unsupported job routes | HTTP 404 and 503 respectively |

Local measurements are not production-latency or field-performance guarantees.
The corrected Vercel Linux preview calculated the default three-site study and a new
four-site study at 14.5082° N, 30.1746° E with a 1.8 m panel. Its exact JSON export
was recalculated on macOS with identical request hash and epochs. Maximum position
differences were 0.0363 m for the Sun, 0.000095 m for Earth and 0.000000448 m for LRO;
maximum site elevation difference was 1.39e-11 degrees. These are cross-platform
implementation comparisons, not bounds on absolute ephemeris accuracy.
The public Vercel production build at commit `6bda219` also passed native calculations,
rendered lunar imagery, changing LRO states, play/pause UTC progression, complete
methods/source disclosure, saved alternatives and exact result download. Advancing
only the six-hour interval from 1 to 2 April changed the custom site's first Sun
elevation from about 36.407° to 25.346° and changed its request hash. The exported
request hash was reproduced locally. Details and actual timestamps are in
[deployment-review.json](deployment-review.json).
The interface's Methods & sources disclosure exposes every returned limitation,
assumption and source checksum in a bounded, keyboard-scrollable region. Its mobile
keyboard and source-link behavior passed the browser suite. The final 28-test run
also checked real-Cesium whole-Moon bounds at 1440 × 900, after a 260 px map-height
resize, and in polar view. The loading context remains visible until scientific
display tiles are ready; this is a presentation handoff, not a terrain calculation.
The optional Docker image was not built because no Docker daemon was available.

Numerical reader comparisons are recorded in
[independent-reader-review.json](independent-reader-review.json). They use shared
source kernels and time conversion; they establish implementation agreement, not
physical ephemeris uncertainty or independent non-author approval. UI action,
contrast and error/mobile evidence is in
[the interface report](../../../web/docs/research-workbench.md).

## Reproduce

From the repository root with analysis/service/test dependencies installed:

```sh
python scripts/prepare-research-data.py --output /tmp/soma-research-sources
python examples/research_geometry.py --data-root /tmp/soma-research-sources --output /tmp/lro-three-sites.json
SOMA_RESEARCH_DATA_ROOT=/tmp/soma-research-sources python -m pytest tests/engine -q
npm --prefix web test
SOMA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix web run test:browser
SOMA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix web run test:research
npm --prefix web run build
```

The real-source browser test expects sources prepared in `api/_data`; use
`python scripts/prepare-research-data.py` for that default location. Other physical
engine integration tests also need the separately documented regional DEM and source files.
Use an installed Chromium path appropriate to the test machine.

## Remaining expansion work

This endpoint evaluates spherical-horizontal Sun/Earth center geometry and spacecraft
states. It does not compute terrain visibility, finite solar-disk fraction, eclipses,
power, usable contacts, footprints or schedules. Wider numerical terrain, designed
orbits, instrument/coverage analysis, live delivery integration, sweeps and richer
saved-run comparisons remain separate planned increments. The existing bounded
delivery engine retains its original capabilities and assumptions.

Public hosting remains Vercel. Features beyond its verified budgets must be designed
and validated within that constraint before publication. No Railway deployment was created.

New Git author/committer dates use the user's requested 15 November 2026 evening
window. Actual verification and deployment times remain recorded as performed.
