# Analysis datasets

The historical Phase 1 [datasets.manifest.json](datasets.manifest.json) and
`kernels.manifest.json` remain metadata-only snapshots. Phase 2 now has separate
actual acquisition records described below. Numerical terrain files are not
bundled in the repository. One unmodified, hash-pinned Earth-orientation kernel
is retained in [pinned/](pinned/README.md) because its original rolling NAIF URL
no longer serves that revision. It preserves the existing scientific inputs;
the retained file does not upgrade the ephemeris or change the frame realization.

`synthetic-contract-v1` declares the supported coordinates and UTC dates for
invented contract inputs: planetocentric latitude from −90 to −80 degrees,
east-positive longitude in [−180, 180), and 14 November 2026 UTC. Its frame is
`MOON_ME_DE421` and its reference sphere radius is 1,737,400 m. These are
validation bounds, not measured terrain coverage or validated kernel coverage.
The empty file list means no numerical surface exists for these inputs.
Hand-calculated contact expectations belong to the synthetic fixtures and are
not an engine-generated mission prediction.

The planned Phase 2 terrain source is the [NASA PGDA South Pole LOLA DEM
Mosaic, product 81](https://pgda.gsfc.nasa.gov/products/81). The project evidence
register, [D04](../plan/06-Research-and-Source-Register.md#d04), records its
five-meter pixels, south-polar stereographic coordinates, DE421 mean-Earth
frame, interpolated elevation fill, and count products. The manifest records
these source facts without asserting that the files are locally available.
Hashes and acquired coverage remain `null` until acquisition and inspection.
Download and redistribution terms still require review; linking a NASA source
does not establish permission to bundle every file.

Before analysis, record the exact source revision, file URLs, checksums, bounds,
reference radius, elevation datum, interpolation rules and count/fill masks.
A windowed extract also needs its parent product and extraction metadata.
Select matching lunar frame, orientation, planetary ephemeris and leap-second
kernels, then verify their actual coverage. A DE440 upgrade requires the
documented transformation and registration test; `IAU_MOON` and a generic
`MOON_ME` alias are not replacements for the declared DE421 realization.

Missing terrain produces an unknown horizon, never a clear view or a sentinel
of −90 degrees. Antenna and panel heights remain separate inputs. Future
horizon caches must include the site, observer height, DEM hashes, frame,
sampling parameters and algorithm version. Finite spacecraft links need a
segment-limited terrain and body test; a distant skyline alone cannot decide
them. Cesium meshes provide display data and cannot substitute for this DEM.

## Acquired Phase 2 data

- [de421-phase2.manifest.json](de421-phase2.manifest.json): five matched NAIF
  kernels, exact hashes, per-object binary coverage and a bounded verification
  date. ITRF93 station geometry uses the separately identified Earth PCK,
  including predicted orientation. No generic lunar alias substitutes for
  `MOON_ME_DE421`.
- [lola-phase2.manifest.json](lola-phase2.manifest.json): a 2000-by-2000-pixel,
  five-meter window of the PGDA 87S elevation and count rasters, with the
  original polar grid, floating-point return counts and nodata. The 3.5 GB
  elevation mosaic is read through HTTP ranges. The compact count mosaic is
  cached locally because remote tiled count reads failed. Source object
  identity, the extract hashes, and the full cached count-parent hash are
  recorded. The full elevation-parent hash remains unknown, not fabricated.
- [lola-far-phase2.manifest.json](lola-far-phase2.manifest.json): the last 640
  rows of the native 64-pixel-per-degree LDEM/LDEC grids, covering −90 to −80
  degrees at all longitudes. Each source range is 29,491,200 bytes. No
  reprojection occurs. Height is signed little-endian DN times 0.5 meters;
  the 1,737,400-meter radius offset is not added to elevation. LDEM V3.1 and
  LDEC V3.0 are pinned separately and share the acquisition cutoff documented
  in their labels.

All source grids explicitly identify the DE421 mean-Earth realization. PDS
labels and source URLs remain in the manifests. Numerical files are local
analysis inputs; this repository makes no redistribution grant. Cite Barker
et al. (2021) for the PGDA product and retain the LOLA/PDS product attribution.

Acquire or verify the pinned local bundle with:

```sh
.venv/bin/python -m soma fetch-geometry-data --data-root /private/tmp/soma-phase2-data
```

The reader uses a known count-positive pixel for the declared numerical test.
The original synthetic site has missing terrain. Any zero count, missing
contributor or unsupported far sample remains unknown. Detailed terrain holes
do not silently fall through to a smoother coarse surface. The actual test
horizons therefore remain nonconverged and unknown; no illumination or radio
visibility is claimed from them.

## Phase 3 diagnostic evidence

`phase3-evidence.manifest.json` identifies generated illumination/power/contact
artifacts and their exact recorded Phase 2 geometry source. It does not acquire
or bundle another DEM/kernel set. The real LOLA case preserves missing-data
unknowns. Invented sky/skyline/contact assumptions remain separate synthetic
algorithm fixtures. None of these diagnostic files is a selected delivery plan.

