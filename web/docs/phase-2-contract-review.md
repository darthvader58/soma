# Phase 2 geometry diagnostic contract review

Reviewed 14 November 2026 by the assigned interface contract agent. This is an
automated scientific and interface boundary review, not human Developer B
approval, a schema approval, or a merge approval.

## Contract boundary

The six v0.1.0 schemas remain the Phase 1 contract. The closed result schema has
no Sun/Earth direction, horizon, sampled trajectory, or geometric-interval
fields. Those quantities must travel in a separate, versioned geometry
diagnostic artifact until a contract change receives the required review.
They must not be added to `result`, hidden in an assumption string, or converted
into `contacts`. Geometry alone cannot change the planner's delivery status.

The review follows all seven `plan/` documents, both local role instructions,
`schemas/README.md`, the canonical schemas, and
[`challenge-alignment.md`](../../soma/docs/challenge-alignment.md). The challenge
alignment priority remains local Sun and Earth directions against the declared
terrain horizon. Relay animation is supporting information.

## Diagnostic requirements

The artifact needs its own type/version, input identity and scenario hash,
coverage interval, implementation version, assumptions, warnings and source
manifest references. A standalone diagnostic input must be identified as such
rather than pretending to be an accepted planning scenario. Each manifest must
retain source URLs and actual file checksums.

| Quantity | Required interpretation |
|---|---|
| Surface point | Planetocentric latitude, east-positive longitude, explicit `MOON_ME_DE421` realization, reference radius, elevation datum and elevation. |
| Observer | Panel or antenna role and its separate height above numerical ground; pole reference meridian and local azimuth convention. |
| Direction | Target identity, epoch/time scale, observer identity, azimuth/elevation units, range units and correction convention. Sun-center and Earth-center directions must be named explicitly. |
| State | Target, origin, frame, epoch representation, time scale, position and units, provenance; canonical state records can use the existing state schema without extra fields. |
| Horizon | Observer role/height, azimuth samples, angles or nulls, masks and reasons, DEM hashes, sampling/interpolation, search extent and convergence evidence. |
| Geometric interval | Target and observer, clear/blocked/unknown classification, reasons, time convention, boundary uncertainty and numerical method. This is not a usable contact. |
| Numerical limits | Terrain pixel/sample spacing, azimuth/range sampling, geometry time step, event refinement tolerance, missed-short-event check and any unverified convergence. |

An Earth-center series cannot stand in for an actual configured station series.
Station geometry requires its own identity, WGS84/ITRF93 input interpretation,
Earth orientation coverage and receiver-side elevation/body checks. If these
are absent, station visibility remains unsupported. A synthetic relay retains
`synthetic_two_body_lunar_preset` everywhere its trajectory appears and stops at
its declared coverage boundary.

Missing DEM pixels, unavailable count data, interpolation and uncovered
far-field terrain need separate quality evidence. Interpolated elevations are
not independent measurements. A narrow tile does not establish a complete
skyline. Known blockage may still be reported with supporting evidence, but
missing terrain cannot become clear visibility. Extent convergence cannot be
claimed when the search simply reached the available tile edge.

For finite spacecraft, classification must use the terrain and body segment
through the actual target range. An infinite horizon may be explanatory but
must not obstruct a spacecraft with terrain beyond that spacecraft. Directional
horizons for distant centers must declare the approximation and its limits.

Solar-center elevation is a geometry diagnostic. It is neither visible solar
disk fraction, eclipse treatment, electrical generation, nor battery survival.
Earth-center clearance is neither specific-station visibility nor service.
Clear geometry establishes no radio compatibility, pointing performance, link
margin, data capacity, forwarding schedule or delivery feasibility.

## Display decision

The current browser does not ingest this proposed diagnostic. A later reviewed
contract can support a numerical text report or horizon inset using supplied
values, with target identity, height, frame, time, unknown masks and precision
limits visible. The browser must not derive missing physical quantities.

All aligned lander, trajectory, Sun-direction and contact overlays remain
blocked under [`viewer-registration.md`](viewer-registration.md). Phase 2
Moon-fixed states are not automatically renderer-fixed states. Release requires
the versioned engine-to-renderer transform, source identity, justified regional
tolerance and independently checked, well-distributed landmark residuals.
Neither an identity matrix nor CZML `FIXED` alone supplies that evidence.

No runtime interface, fixture or schema is changed by this review. No visual
acceptance claim follows from a documentation-only change.

## Implementation review

The reviewed `soma/diagnostics.py` emits `soma_geometry_diagnostic` version
`0.2.0`, independently of `plan_delivery`. It records the original scenario
hash, requested elevation and DEM-resolved analysis point, separate panel and
antenna horizons, Sun-center and Earth-center tracks, configured station
positions, and an optional explicitly separate synthetic relay preset. Each
exported position is validated against the existing state schema. Geometry
provenance records same-epoch `NONE` correction rather than apparent geometry.

Station classification deliberately remains unknown because endpoint and full
segment checks are not assessed. The optional relay uses a finite segment test
and records the assumed inner-body radius, sample spacing and clearance. It is
not the configured scenario relay's ephemeris. The report warns that geometry
does not establish service, link closure or delivery.

Intervals group adjacent sampled classifications. They carry sample-sized
boundary uncertainty and expressly leave interval interiors unproved; short
opportunities may be missed. These are sampled diagnostic intervals, not
refined events or scheduling contacts. Extent convergence does not establish
radial or angular completeness.

The far-field source was independently checked against the actual official
[LDEM_64 label](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldem_64.lbl)
and [LDEC_64 label](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/cylindrical/img/ldec_64.lbl).
Both explicitly identify the DE421 mean-Earth/polar-axis realization and
1,737,400 m sphere, so no IAU-frame alias is needed. Height is signed
little-endian 16-bit DN multiplied by 0.5 m; the radius offset is not added to
elevation. Counts are raw integers. Both use 64 pixels/degree and aligned,
pixel-registered simple-cylindrical grids. Height V3.1 and count V3.0 have the
same acquisition cutoff but different creation dates; provenance must retain
that distinction and the height label's interpolation/edge-artifact warnings.

The generated local report at
`/private/tmp/soma-phase2-data/geometry-diagnostic.json` was inspected. It
contains 16 epochs from 2026-11-14 08:50 to 10:05 UTC, with a 300 s step and an
explicit diagnostic site override near 89.031 degrees south, 1.389 degrees east.
The DEM-resolved elevation is -301.98974609375 m; antenna and panel heights are
2 m and 1 m. Both horizons are unconverged, retain null horizon angles and
sampled lower bounds, and expose missing-data and zero-count interpolation
flags. Sun-center and Earth-center classifications remain unknown. Station
geometry remains unknown; the optional synthetic relay is blocked by its
declared body test. This is evidence of an honest incomplete geometric
diagnostic, not complete terrain coverage, operational communications windows,
or a delivery result.

Review evidence: canonical schemas and current diagnostic source were read;
the generated report's metadata, tracks, interval uncertainty, per-height
horizons and quality flags were inspected; both actual PDS labels were fetched
and hashed. Only this Markdown file was edited by the interface review agent.
