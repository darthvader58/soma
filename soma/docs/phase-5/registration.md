# Renderer registration handoff

The active artifact is `data/renderer-registration.manifest.json`, version 0.2.0.
It maps Moon-centered `MOON_ME_DE421` meters identically to
`SOMA_MOON_ME_DE421_CORRECTED_V1` after Python corrects the streamed Moon v6
vertices. That identity never applies to the unmodified asset. Static terrain
has no epoch; spacecraft states still require their own time-tagged transforms.

The certificate binds the matched DE421 kernel/LOLA manifests, conversion
parameters, code and measured feature evidence. Loading it recomputes the
four feature matches and rejects modified evidence. The browser requires the
same conversion hash from the local corrected-tile service. Runtime root/control
fingerprints detect sampled upstream changes; they do not checksum the entire
streamed regional dataset.

The declared application region is latitude -90 to -87.5 degrees, all longitudes.
The release gate checks the scenario's site against this region. Ten meters is
the predeclared acceptance threshold for the resolved grid-feature comparison,
including a 3.54 m grid-resolution allowance. It does not establish a continuous
peak-location error bound, absolute geolocation accuracy, or every-LOD guarantee.

The four independently searched source-defined terrain peaks are documented in
[map-alignment.md](map-alignment.md). Each reference peak has measured LOLA count
support; surrounding interpolated heights are identified as such. These controls
validate separate extraction/registration paths, not independent absolute geodesy.

`GET /moon/conversion` and `/moon/registration` expose the current display
handoff. Completed jobs retain their own immutable `/plans/{id}/display-data` and
`/plans/{id}/renderer-registration`; exports also include conversion parameters.
The browser displays engine points, preserves unknown trajectories, and performs
no visibility, power or routing calculation. Picks are display coordinates and
never update scenario elevation automatically. The numerical DEM, heights and
frozen native schemas are unchanged.

The archived unresolved version is
`fixtures/registration/unresolved-registration-v0.1.json`. Earlier catalog-sphere
positions remain useful provenance but are not reported as measured residuals.
