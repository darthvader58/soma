# Dark dashboard: geometry and source-binding verification

Recorded at 2026-11-17T10:44:13.238389Z. The audit used the actual hosted Python adapter through local HTTP TestClient, with fresh isolated native-SPICE calculations and hash-pinned files in `api/_data`. No planner was mocked. This is engine/API evidence, not a deployed-host or browser observation. Engine, schema and archived fixture outputs were not edited.

## What the endpoint calculates

`POST /api/research/analyze` evaluates a declared reference sphere in `MOON_ME_DE421`, centered on the Moon. It returns site/antenna/panel Cartesian coordinates, native Sun/Earth and optional reconstructed LRO six-dimensional state histories, and per-site Sun/Earth azimuth, elevation, range and direction. Sun uses panel height; Earth-center uses antenna height. Corrections are same-epoch geometric `NONE`; velocities are derivatives in the rotating Moon-fixed frame.

The frozen study schema permits only `surface_model: reference_sphere`. The response explicitly sets terrain visibility, solar-disk fraction, power and usable contacts to `not_evaluated`. A request with `surface_model: terrain` was rejected with `surface_model: 'reference_sphere' was expected`. The warning describes the implemented scope, not a terrain-loading failure.

## Controlled real calculations

All requests used a declared custom site at latitude 14.5082 degrees, elevation 0 m, antenna height 2 m and panel height 1.8 m; 181 epochs at 60 s spacing over three hours; and `lro-reconstructed-2026-spring`. A used longitude 30.1746 degrees east on 1 April 2026. B changed only longitude to 45.1746 degrees. C retained A's site and changed only the interval to 2 April 2026. Every response was HTTP 200, matched its normalized RFC8785 study hash and passed result-schema validation.

| Request | Interval UTC | Study SHA256 |
| --- | --- | --- |
| A | 1 April 2026, 00:00–03:00 | `ecdbb7560900f8dd5cd3ce8ea947127dbf98fe77d28028b6bbc3f29623349eb8` |
| B | 1 April 2026, 00:00–03:00 | `d4777b8b07b1e41e4d33dc2d3a9806fcde8092016d9801939f4792fedf136c71` |
| C | 2 April 2026, 00:00–03:00 | `c4382e86219f3e25c1c8774ec6c6d624dffb0bba99103ab000bda0083f6bfd30` |

| Comparison | Site movement | Native global Sun / Earth / LRO maximum position difference | First local Sun / Earth elevation difference |
| --- | ---: | --- | --- |
| A → B, longitude only | 439,089.441 m | 0 / 0 / 0 m | −12.080092663 / −13.875380498 degrees |
| A → C, date only | 0 m | 31,745,926,486.290 / 10,307,314.848 / 3,104,725.161 m | −9.578748097 / +0.151620565 degrees |

Global target histories correctly remain identical when only the observer site changes at the same epochs. They describe Moon-centered bodies/spacecraft, not site-relative directions. All three target-array hashes changed for the date-only case. Date comparisons above pair equal sample indices one day apart; the metre values are state displacements, not errors or physical accuracy claims.

Within A's three-hour result, LRO moves up to 3,655,064.752 m from its first sampled position. Local Sun elevation changes from 71.406343924 to 70.354938764 degrees; Earth elevation changes from 61.818773601 to 61.854445311 degrees. These are sampled geometric quantities, not terrain visibility or illumination fractions.

The endpoint returns arrays; it does not itself alter a Cesium mesh, camera, material or playback cursor. Identical-input reruns produce the same numerical geometry. This audit does not establish whether a particular browser view applies the returned positions and selected epochs correctly.

## Why the terrain capability is separate

The research request path imports no terrain resolver. Its build-time source preparation bundles four DE421 kernels plus the optional LRO SPK, with no numerical DEM. The separate Python terrain library offers pinned elevation/count readers, body-consistent horizon profiles, segment-limited terrain tests and cached profiles. Illumination code combines a finite solar-disk mask with terrain and Earth occultation. The older physical delivery pipeline invokes these methods under its declared resources and assumptions.

Those local datasets are bounded: a 5 m near-89S extract, a small 5 m pole patch, and a 64-pixel/degree coarse south-cap grid covering latitude −90 to −80 degrees. The older physical planner's supported region is narrower: latitude −89.15 to −88.85 degrees, longitude ±3 degrees, November 2026 and at most six hours. Its source-quality policies preserve interpolation/coarse-resolution flags and unknown samples. It is not a global terrain-visibility provider.

Fresh reads from the pinned local numerical grids returned −382.875 m at 89S/0E with a coarse-resolution downgrade, 5,181.25 m at 85S/30E with the same downgrade, and an interpolated-model 1,289.478 m at the pole. The custom northern site above returned missing terrain/unknown. These are declared DEM model samples, not measured elevations guaranteed at those coordinates. Rendered Cesium tiles cannot supply the missing numerical terrain assessment.

Provider versions were SpiceyPy 8.4.0 / CSPICE_N0067. Source manifests were:

- `data/de421-phase2.manifest.json`: `f39c7e8951834cad1cc9104127bf9c31ffe6b41eac71db9df53af243d6255c01`
- `data/research-lro.manifest.json`: `0b79caf08d7124a354048568ed259c8b2e70c7a70a9bf6747fd8f7ddba6c3a95`

Raw controlled requests/results and detailed array hashes are retained locally in `/private/tmp/soma-readonly-geometry-audit/`. The reference sources are the project register's D03/D04 SPICE and LOLA entries and the pinned public NASA PDS/NAIF LRO source manifest. Shared source kernels and stated models constrain interpretation; these checks do not establish exact physical predictions or global map registration.

## Fresh verification and historical bindings

- Targeted contracts, bindings, fixture arithmetic, Phase6 completion and research geometry/contract tests: **97 passed, 0 failed, 0 skipped in 15.44 s**.
- Final binding-only recheck after wording correction: **3 passed in 0.10 s**.
- Independent CLI replay of the retained fresh synthetic 100 MiB test run: **passed**, no errors, **104,857,600 bytes** delivered. This is a synthetic assumed-contact/rate/service fixture, not a lunar mission prediction; its feasible incumbent does not prove optimality.
- A full engine suite was not rerun for this documentation/appearance change. Browser and deployment verification are outside this report.

The frozen README now describes a dark research workspace and neutral scene lighting. Only its physical-evidence and fixture dependency bindings required refresh; Phase6 evidence was unchanged. Original review dates, scientific scopes, archived outputs and historical verification counts are retained. Current appearance/result presentation is not certified by the old physical-release records.

All **438 manifest bindings** match.

| Manifest | Bindings | SHA256 |
| --- | ---: | --- |
| `data/phase6-evidence.manifest.json` | 43 | `4ec2d2ace2f8e9d9426fd2c61828501bc2f8fbb6e5864874b7a111795d8aa770` |
| `data/physical-first-release-evidence.manifest.json` | 97 | `2630987eb02d32878158ef58cd12377e59ab61ffae011f5e1ccb9846d0383e59` |
| `fixtures/manifest.json` | 298 | `e0fbfc3cffcc61863e277c6bc1dc21f47c923ca64a3c1e084b7be1e7d1e4e8ea` |
