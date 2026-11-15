# Renderer registration, v0.1.0

Follow-up: the [deeper source audit](registration-source-audit.md) located explicit
DE421 mean-Earth/polar-axis definitions in both advertised terrain source
families. A vendor statement is not an absolute prerequisite for testing the
bridge. Raw mesh measurements now exist, but their radial discrepancies and
independent horizontal feature correspondence remain unresolved. The source
audit is hash-bound as additional evidence; the overlay gate remains blocked.

Engine-to-asset registration remains blocked. The service can expose the immutable
scientific schedule and the versioned registration artifact; aligned landers,
trajectories and contact overlays must remain disabled. This is a Phase 5 handoff
with an explicit unfinished map acceptance gate, not completed map registration.

The artifact is `data/renderer-registration.manifest.json`. Its SHA-256 bindings
identify the existing matched DE421 kernel and PGDA LOLA manifests and the
registration source-evidence manifest. `load_renderer_registration()` checks those
bindings and returns a fresh dictionary. `registration_release_gate()` preserves
the blocked gate. Frozen scenario/result schemas were not changed.

The source is Moon-centered `MOON_ME_DE421`, meters. The renderer frame and matrix
are null because no defensible bridge has been established. A future reviewed
column-major matrix must mean `p_renderer_m = M @ [x_source_m,y_source_m,z_source_m,1]`,
including any translation in meters and all root/per-tile transforms. A dynamic
bridge requires explicitly sampled epochs, time scale, kernels and coverage;
a static identity cannot stand in for that. This version accepts only the blocked
state and cannot be promoted by supplying a matrix and fabricated zero residuals.
Approval requires a reviewed successor contract and implementation.

## Evidence checked on 15 November 2026

The [official Cesium Moon page](https://cesium.com/platform/cesium-ion/content/cesium-moon/)
identifies the asset and regional source products, but does not establish an
explicit DE421 orientation realization, immutable tileset revision or measured
registration. The published list mixes LOLA polar terrain and a LOLA/Kaguya
midlatitude merge. Shared source lineage is insufficient to prove shared axes,
height datum, tiling transforms or control network.

Context7's official Cesium source entry documents lunar ICRF/fixed transformation
APIs introduced in 1.120. Runtime transformation availability does not identify
the coordinates of asset 2684829. `Ellipsoid.MOON` specifies a reference shape;
CZML `FIXED` does not establish the DE421 realization.

[NAIF's lunar frame kernel](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_de440_250416.tf)
distinguishes DE421 mean Earth, DE440-derived mean Earth, principal axes and
`IAU_MOON`. Similarity is not identity. No replacement kernel or alias was loaded
for this handoff.

The USGS Gazetteer supplies these candidate feature centers:

| Landmark | Latitude (degrees) | East longitude (degrees) | Catalog |
| --- | ---: | ---: | --- |
| Tycho | -43.30 | -11.22 | [6163](https://planetarynames.wr.usgs.gov/Feature/6163) |
| Plato | 51.62 | -9.38 | [4757](https://planetarynames.wr.usgs.gov/Feature/4757) |
| Tsiolkovskiy | -20.38 | 128.97 | [6108](https://planetarynames.wr.usgs.gov/Feature/6108) |
| Shackleton | -89.67 | 129.78 | [5450](https://planetarynames.wr.usgs.gov/Feature/5450) |

The active feature pages label their coordinates planetographic, east-positive,
-180 to 180, with multiple control-network choices. These rounded nomenclature
centers are not precision terrain fiducials and are not relabeled DE421. The
artifact stores the active-page coordinate values, their source URLs and a
**candidate** Cartesian construction on an assumed 1,737,400 m sphere. Graphic
and centric latitude coincide only for that construction. Its frame realization
is deliberately unassigned; elevation remains unknown. `analysis_position_m`,
`renderer_position_m` and `residual_m` are all null. Recomputing the sphere radius
or latitude checks algebra only and supplies no independent asset residual.

These candidates span northern/southern near side, southern far side and the
south pole. They are not an accepted distribution review. Additional western,
far-northern and controls near the actual analysis region should be selected
with independent, identifiable terrain fiducials. Source pixel resolution is
not a defensible residual tolerance; `tolerance_m` remains null until reviewed.

## Exact evidence needed to unblock

1. An authorized immutable asset snapshot or vendor-supplied metadata for asset
   2684829: revision/hash, coordinate realization, origin, meters, reference
   surface/elevation datum, tiling transforms and source product revisions.
2. Precisely identified common terrain fiducials with authoritative coordinates
   mapped from their documented control network into `MOON_ME_DE421`, including
   measured elevation, uncertainty, and independent source evidence. Broad crater
   centers alone cannot support a meter-scale tolerance.
3. Independently measured corresponding scene Cartesian positions on that exact
   asset, with sufficient loaded detail, selection method, root transforms,
   uncertainty and reproducible recording. Browser picks stay display-only.
4. A documented transformation with independent residual recomputation,
   well-distributed and local control review, appropriate region/scale tolerance,
   and Developer A/B review. Over-tolerance and unknown residuals block overlays.

Public documentation and catalog browsing were initially performed without ion
credentials. Following explicit authorization, a scoped local token was used for
the official asset endpoint and root plus three regional tileset JSON documents.
No token, credentialed URL or endpoint response was retained. No tile geometry,
imagery or landmark scene pick was retrieved in this bounded metadata inspection.

The root declares `3DTILES_ellipsoid` with body `Moon` and all three radii equal
to 1,737,400 m. It has no explicit root transform. The first regional child has
isotropic root scale 1.0010935881201797. The other two regional roots have opposite
quarter-turn Y rotations. Each matrix maps local root tile coordinates to its parent asset coordinates;
ancestor/descendant matrices compose through the hierarchy. Rotation and scale
are dimensionless; Cartesian translation uses meters and all observed translation
components are zero. Horizontal control network, lunar orientation realization
and vertical datum remain unknown. Exact column-major arrays and response SHA-256 values
are recorded in the source-evidence manifest. These map each tile's local
geometry into the asset scene; they do not establish the DE421-to-scene bridge.
In particular, applying the child scale directly to engine coordinates would be
an unjustified change to lunar distances.

Across these four JSON documents there is no explicit DE421/IAU orientation
realization, control network or independent landmark position/residual. Regional
`asset.extras.ion` declares georeferenced true and movable false. `asset.version`
is a 3D Tiles format version, not an immutable dataset revision. Thus authorized
metadata access narrows the unknowns but does not pass the map release gate.
That metadata-only result is a historical snapshot. The deeper source audit
supersedes the assumption that an external vendor statement is necessary.
Measured feature correspondence, explained radial behavior and a justified
tolerance still have to pass; merely finding the frame name is insufficient.

Run `.venv/bin/python -m pytest tests/engine/test_registration.py`. Tests reject
invented identity, frame/unit changes, zero residuals, duplicate landmarks,
corrupted catalog construction, hash drift and a forced release Boolean. They
test fail-closed handoff behavior, not the unresolved scientific registration.
