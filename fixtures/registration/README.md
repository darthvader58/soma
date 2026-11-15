# Raw renderer registration diagnostics

These are source-bound probes and observations, not a passing frame bridge.
The inputs explicitly test an unvalidated identity candidate. Four center probes
and 100 polar-patch probes completed against the actual streamed Moon asset in
Chromium with no page or console errors. The browser exported world Cartesian
positions after tile transforms; it did not alter the numerical scenario or
enable overlays.

`polar20m-native-reference.json` retains four directly read published JP2 pixel
values and raster metadata. `polar20m-reference.json` decodes native DN to height
using the product label's 0.5 m scale. `radial-differences.json` reports only the
radial comparison. The full source raster hash and fine count mask were not
acquired. Unknown correspondence is distinct from zero residual.

`coarse-polar-reference.json` describes the separately pinned Phase 2 reference
used for the wider patch experiment. It includes interpolated coarse values and
quality flags; two missing samples remain null. Weak terrain correspondence and
outliers prevent treating these patches as accepted fiducials.

See `soma/docs/phase-5/registration-source-audit.md` for primary-source URLs,
interpretation and reproduction. No token, signed URL or binary tile is bundled.
The files do not authorize a visual correction or scientific map release.

The later `inner-polar-*` records cover four source-selected peaks away from the
85-degree boundary. A 20 m elevation/count pair is fully hashed in
`inner-polar-source-products.json`; the binaries are not bundled. The 324-point
reference retains native contributors and keeps 80 zero-count samples unknown.
Patch medians remain about 658 to 661 m above the source. The CPU intersection
record retains four observed triangles and their hashes/transforms; independently
intersecting these reproduces browser positions within 0.057 m. This diagnoses
the sampler and mesh, not a passing landmark registration.

`calibration-planes.json` is explicitly synthetic. The plane centers are
analytically 1,000 m below the reference sphere. The asserted, asset-free capture
in `instrument-calibration.json` measures them within 0.007207 m. Its hashes bind
the request, geometry and diagnostic source; it records zero asset requests.
Both calibration and real-terrain evidence leave registration unevaluated.

The exact 5 m product and count mask are pinned in `inner-polar-5m-reference.json`.
All 324 initial bilinear comparisons are unknown at that resolution because at
least one contributing pixel has no measured return. The separate
`inner-polar-5m-positive-*` experiment queries four source-selected pixel centers
with positive counts. Their measured height differences remain 650 to 659 m;
this rules out the coarser reference as an explanation for those four samples.
