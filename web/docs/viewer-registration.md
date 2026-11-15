# Lunar display boundary

The viewer uses Cesium Moon ion asset 2684829 as a 3D tileset with the ordinary
globe disabled and `Ellipsoid.MOON` set before constructing the viewer. The ion
token must be supplied by the host application; absent tokens do not trigger an
import, asset request, or evaluation-token fallback. Keep Cesium's credit display
visible. The copy script retains the installed package's asset notices.

The current engine supplies no renderer registration. All lander, trajectory,
Sun-direction, and contact overlays remain blocked. Topography can be browsed
when a token is configured. Neutral UNLIT shading is display-only; source imagery
may contain shadows. Neither those shadows nor scene time indicates modeled
illumination. UNLIT/CustomShader is a documented experimental Cesium API pinned
by the application's dependency lockfile.

`createMoonViewer(container, {scenario, ionToken, onPick, onStatus, registration})`
returns a promise for `{setScenario, setTime, clearDisplayPick, destroy}`.
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
coordinate is relabelled as `MOON_ME_DE421`, and rendered elevation never
replaces ground elevation or either equipment height. Restore, fixture
switching, scenario edits, tile failure and rendering failure clear the pick.
Failed scenes release their resources and leave the text view available.

## Future registration handoff

The viewer-local evidence check is **not a scientific interchange schema** or
a numerical registration test. No example identity transform is provided.
Developer A must issue reviewed evidence before implementing aligned overlays:

- `version`, `authority: soma_engine`, `source_frame`, `renderer_frame`,
  `asset_id: 2684829`, and `source_manifest_sha256` identifying source metadata.
- `transform_column_major`: 16 finite numbers, with units and transform meaning
  documented in the referenced engine manifest; a versioned identity is allowed
  only when justified by those sources.
- `tolerance_m` and `tolerance_justification` appropriate to the region and scale.
- `landmarks`: at least four distinct IDs, each with `source_ref`,
  `renderer_position_m` (three finite coordinates), and measured `residual_m`.
- `distribution_review: {accepted: true, evidence_ref}` referencing review of
  well-distributed lunar landmarks. Four repeated/co-located points are not a
  valid distribution test. The engine review must establish distribution and
  recompute residuals independently; this display gate only checks supplied
  evidence and residual bounds.

Passing this structural gate does not enable overlays in the current viewer.
Future implementation must bind the reviewed transform to the exact scenario,
DEM and kernel hashes, position units, origin, frame, and coverage. An exceeded
tolerance leaves the text result available and overlays blocked. Do not nudge
positions to fit imagery or write display offsets into the analysis.

## Sources checked during implementation

- [Official Cesium Moon setup and attribution](https://cesium.com/platform/cesium-ion/content/cesium-moon/)
- [Cesium scene picking](https://cesium.com/learn/cesiumjs/ref-doc/Scene.html)
- [CustomShader lighting model](https://cesium.com/learn/cesiumjs/ref-doc/CustomShader.html)
- [MMGIS lunar south-pole blueprint](https://github.com/NASA-AMMOS/MMGIS/blob/development/blueprints/README.md)

MMGIS was consulted for its explicit lunar projection and separation of maps
from SPICE-backed analysis. No MMGIS code, tiles, or algorithms were copied.
Token-backed streaming and picking require separate visual QA with authorized
ion asset access. Missing-token fallback can be verified without that access.
