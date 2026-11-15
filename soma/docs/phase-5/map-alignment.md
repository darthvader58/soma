# Phase 5 Moon map alignment

The corrected static Moon representation passes the preregistered 10 m relative
display-registration test. The application applies this certificate only between
87.5°S and the south pole. It does not certify absolute lunar geolocation,
continuous terrain-peak positions between samples, or accuracy at every map LOD.
The contact-only synthetic relay fixture still has no spacecraft trajectory.

## Cause and correction

The raw streamed asset differed from the published 5 m LOLA product by about
650–659 m at positive-count polar controls. Four exact synthetic planes first
calibrated the browser sampler to 0.0073 m; decoded mesh-triangle intersections
independently agreed with those browser samples to 0.057 m. The earlier
[source audit](registration-source-audit.md) preserves those measurements.

The glTF texture grid independently supplies source latitude and longitude.
A fit using 261,943 vertices from 240 tiles recovers an oblate coordinate
conversion with semimajor axis 1,738,042.3511433182 m and eccentricity squared
0.002412566753187137. For local mesh cylindrical radius rho, z and source
latitude phi, the height-independent relation is:

```text
D = rho / cos(phi) - z / sin(phi)
D = a e² / sqrt(1 - e² sin²(phi))
```

Fitting the linear relation for 1/D² uses neither DEM heights nor the landmark
residuals. RMS residual in D is 0.000070 m; tile-parity holdouts give comparable
residuals. All four feature-control tiles are excluded from that fit.
The axis resembles WGS84 scaled by 0.2725, but this numerical resemblance does
not establish the vendor's implementation.

For each decoded vertex the engine recovers its ellipsoidal height along the
source normal, removes the observed EGM96 grid offset in tile-local coordinates,
and reconstructs the source sphere with radius 1,737,400 m. It reverses the
separately observed global-root scale once, preserves polar root rotations, and
updates positions and bounds together. UVs, indices, imagery and attribution
remain attached to the original asset. This is an empirical display-ingestion
correction. **EGM96 is reversed only as an observed rendering artifact; it is
never used as a lunar physical datum.**

The pinned grid is [PROJ's NGA EGM96 15-minute grid](https://cdn.proj.org/us_nga_egm96_15.tif),
SHA256 `db493027562c9b004d7220fa881f5603adada4e1c5029b933fa7de4547b0e78d`.
[PROJ's vertical-grid documentation](https://proj.org/en/stable/tutorials/EUREF2019/exercises/gridshift.html)
explains its terrestrial use. The service verifies its checksum before conversion.
It downloads the 2.6 MB file into a local temporary cache; `SOMA_RENDERER_GEOID`
can point to an existing verified copy. No geoid, tile binary or credential is
redistributed in this repository.

## Source-first feature correspondence

Four fixed quadrant windows select sharp peaks from published LOLA heights
before requesting corrected-scene measurements. A coarse 20 m search is refined
on the 5 m grid. Each reference freezes a 21 by 21 patch, a connected top 1.25 m
band, no boundary maximum, and positive laser-return count support at the peak.
The renderer then searches its own measured height patch for that band. The
minimum feature separation is 57.47 km. These are source-defined topographic
fiducials, not named crater-center catalog coordinates.

| Source terrain peak | Latitude (°) | East longitude (°) | Resolved 3D residual (m) | With grid allowance (m) |
| --- | ---: | ---: | ---: | ---: |
| 1 | -88.41356120 | 54.59453768 | 0.2304 | 3.7660 |
| 2 | -88.46964138 | 137.57620118 | 0.0160 | 3.5515 |
| 3 | -88.32719219 | -129.97006720 | 0.0861 | 3.6217 |
| 4 | -88.63496332 | -53.51697293 | 0.2328 | 3.7683 |

The reference comes from the
[published LOLA south-pole product](https://pgda.gsfc.nasa.gov/products/81) and its
[PDS height label](https://imbrium.mit.edu/DATA/LOLA_GDR/POLAR/JP2/LDEM_875S_5M_JP2.LBL).
Parent product/label hashes are retained in the source audit and evidence manifest.
Surrounding zero-count interpolated heights help identify a gridded feature;
they are not declared measured terrain or clear numerical horizons. The mesh
may share the source observations, so this is an independent extraction and
registration comparison, not independent absolute geodesy.

The residual table is generated in
`fixtures/registration/landmarks-matched.json` and copied into the versioned
certificate. All four measured 3D residuals are below 0.3 m. Each matched peak
uses the same resolved grid cell in both independently searched fields. Thus
near-zero resolved horizontal displacement must not be read as submeter
horizontal accuracy. The preregistered comparison adds a 3.5355 m grid-resolution
allowance (half a 5 m cell diagonal) to each resolved residual and requires the
sum below 10 m. That allowance is **not a demonstrated bound on a continuous
peak's location between samples**.

An additional 48 source-selected, positive-count pixel controls span -87.6 to
-89.8 degrees across eight longitudes. Corrected-scene height disagreement is
below 0.18 m in the recorded capture. Both tests use the detailed mesh with
reported geometric error 5.21 m. They support empirical regional display
registration under those conditions, rather than a blanket location/LOD guarantee.

## Runtime boundary

The browser still calls `Cesium3DTileset.fromIonAssetId(2684829)`. A public
Cesium JSON loader hook substitutes the local engine-corrected tile transport
for this one asset. Python performs the vertex and bound correction. No custom
shader moves vertices behind Cesium's picking/culling model. The client checks
the approved conversion hash and retains ion attribution.

The service restricts upstream paths to the selected Moon v6 asset, keeps tokens
server-side in this transport, and checks the root and four raw control-tile
fingerprints before releasing the root. These are **sampled snapshot checks**,
not full checksum pinning of every subsequently streamed object. Unsupported
mesh profiles fail explicitly. Corrected tile requests carry the conversion
hash to prevent mixing cached representations after a model change.

The certificate's identity bridge applies only after this conversion. It binds
Python code, parameters, source manifests, independent reference patches and
actual scene capture. Loading it redoes the feature comparison and checks those
hashes. A changed source/certificate, invalid residual, missing terrain sample,
outside-region site or tile/render error cannot authorize scientific overlays.
The text schedule and engine exports remain available on map failure.

## Reproduction

Install the pinned analysis, planning, service and test extras from the root
README. Start the service and Vite as described in [the integration guide](README.md).
Use the scoped local token already configured in ignored `web/.env.local`.
The service can alternatively read `SOMA_CESIUM_ION_TOKEN`. Do not include a
credential in a shell command, export or source artifact.

Recompute the checked-in feature results and certificate without a browser:

```sh
PYTHONPATH=. .venv/bin/python soma/docs/phase-5/reproduction/build_certificate.py
.venv/bin/pytest tests/engine/test_registration.py tests/engine/test_registration_landmarks.py tests/engine/test_renderer_mesh.py tests/engine/test_moon_display_service.py -q
```

To reselect the reference from the four locally acquired published rasters:

```sh
PYTHONPATH=. .venv/bin/python soma/docs/phase-5/reproduction/select_landmarks.py HEIGHT20.jp2 COUNT20.jp2 HEIGHT5.jp2 COUNT5.jp2 OUTPUT_DIRECTORY
```

The input labels/hashes must match the pinned source register. Compare the output
to the committed reference; do not silently replace a source. The separate
`fit_conversion.py CAPTURE_DIRECTORY OUTPUT_JSON` reproduces the height-independent
fit from an authorized local tile capture directory containing `metadata.json`
and SHA-named response files. Its input path/hash list is retained in
`data/renderer-uv-fit.manifest.json`; raw licensed tile bodies are not shipped.

For a fresh corrected-scene capture through the same loader as the application:

```sh
SOMA_REGISTRATION_URL='http://127.0.0.1:5173/registration.html?representation=registered' node web/scripts/capture-registration.mjs fixtures/registration/landmarks-probes.json OUTPUT_JSON
```

`SOMA_BROWSER_EXECUTABLE` may select an installed compatible Chromium. The
calibrated installed Chromium was used after Aside could not complete local
instrumented measurements reliably. The capture records corrected representation,
conversion hash, certificate version and error counts. No temporary module
interception is needed. The diagnostic is development-only and does not affect
planning. A fresh measurement must be reviewed and hash-bound before replacing
the packaged evidence; the builder never fits a favorable transform to residuals.

Run the full engine, web unit, build, live browser and fixture browser commands
in the integration guide before opening the PR. Deliberate 15 m horizontal and
20 m radial shifts, missing probes and boundary peaks are rejected by the feature
tests. The recorded relay schedule is independently replayed, and every exported
ZIP member is checksum-verified. All mission examples remain synthetic planning
calculations under declared assumptions.
