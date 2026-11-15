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
