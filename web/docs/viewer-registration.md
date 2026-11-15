# Lunar display boundary

The viewer uses Cesium Moon ion asset 2684829 as a 3D tileset with the ordinary
globe disabled and `Ellipsoid.MOON` set before constructing the viewer. The ion
token must be supplied by the host application; absent tokens do not trigger an
import, asset request, or evaluation-token fallback. Keep Cesium's credit display
visible. The copy script retains the installed package's asset notices.

The engine supplies a v0.2 registration for its corrected Moon mesh in the
tested latitude region -90 to -87.5 degrees. A matching completed display may
show the backend's declared analysis point. No relay trajectory is invented for
the contact-only fixture. Neutral UNLIT shading is display-only; source imagery
may contain shadows. Neither those shadows nor scene time indicates modeled
illumination. UNLIT/CustomShader is a documented experimental Cesium API pinned
by the application's dependency lockfile.

`createMoonViewer(container, {scenario, ionToken, onPick, onStatus, registration})`
returns a promise for `{setScenario, setDisplay, setTime, clearDisplayPick, destroy}`.
`setTime` only sets the Cesium clock. `setScenario` clears display selections
and retains input without creating aligned engine geometry.
`onStatus` receives `{state, message, overlaysBlocked, registration}`.
`onPick` receives latitude/longitude and `display_elevation_m`, with
`source: cesium_moon_display_pick` and `service_resolved: false`. Only an actual
Moon-tileset pick with depth support is accepted. Service-resolved elevation,
frame, and coverage must come from Python. The host supplies typed entry as the
keyboard and depth-unavailable alternative.

A successful pick creates a marker at a clone of the raw scene Cartesian
position, labelled "Display point · not service-resolved". This interaction
marker is distinct from a registered engine lander position. No renderer
coordinate is adopted as a numerical terrain sample, and rendered elevation never
replaces ground elevation or either equipment height. Restore, fixture
switching, scenario edits, tile failure and rendering failure clear the pick.
Failed scenes release their resources and leave the text view available.

## Registration handoff

The viewer-local evidence check is **not a scientific interchange schema** or
a numerical registration test. Developer A issues reviewed evidence:

- `version`, `authority: soma_engine`, `source_frame`, `renderer_frame`,
  `asset_id: 2684829`, and `source_manifest_sha256` identifying source metadata.
- `transform_column_major`: 16 finite numbers, with units and transform meaning
  documented in the referenced engine manifest; a versioned identity is allowed
  only when justified by those sources.
- `tolerance_m` and `tolerance_justification` appropriate to the region and scale.
- `landmarks`: at least four distinct IDs, each with `source_ref`,
  `analysis_position_m`, `renderer_position_m` (three finite coordinates), measured
  `residual_m`, `horizontal_grid_resolution_allowance_m`, and
  `resolution_adjusted_residual_m` below the declared tolerance.
- `distribution_review: {accepted: true, evidence_ref}` referencing review of
  well-distributed lunar landmarks. Four repeated/co-located points are not a
  valid distribution test. The engine review must establish distribution and
  recompute residuals independently; this display gate only checks supplied
  evidence and residual bounds.

The loader preserves ion attribution and replaces root JSON through Cesium's
public loading hook with the engine-corrected mesh. Root and child URLs carry
the conversion checksum to prevent reuse across conversion revisions. The
certificate binds the corrected renderer frame, source evidence and conversion
checksum. A matching completed display supplies exact Cartesian surface points
with frame, units, origin, static epoch and provenance. Missing results, stale
conversion hashes, out-of-region sites and scene failures keep overlays blocked.
An exceeded
tolerance leaves the text result available and overlays blocked. Do not nudge
positions to fit imagery or write display offsets into the analysis.

Four source-selected grid features and 48 height controls test relative display
registration at the detailed 5.21 m mesh level. The 3.54 m grid-resolution
allowance does not bound continuous-peak localization. This is neither absolute
lunar geodesy nor an all-location or all-LOD guarantee. Runtime root and four
control-tile fingerprints are sampled snapshot checks, not complete content
pinning. Numerical DEM quality remains separate from rendered terrain.

## Sources checked during implementation

- [Official Cesium Moon setup and attribution](https://cesium.com/platform/cesium-ion/content/cesium-moon/)
- [Cesium scene picking](https://cesium.com/learn/cesiumjs/ref-doc/Scene.html)
- [CustomShader lighting model](https://cesium.com/learn/cesiumjs/ref-doc/CustomShader.html)
- [MMGIS lunar south-pole blueprint](https://github.com/NASA-AMMOS/MMGIS/blob/development/blueprints/README.md)

MMGIS was consulted for its explicit lunar projection and separation of maps
from SPICE-backed analysis. No MMGIS code, tiles, or algorithms were copied.
Token-backed streaming and picking require separate visual QA with authorized
ion asset access. Missing-token fallback can be verified without that access.
