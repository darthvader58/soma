# Deeper frame-source audit and measured diagnostics

The source frame is discoverable. The initial metadata-only inspection stopped
too early: underlying PDS labels explicitly identify the frame even though the
ion tileset JSON does not. A vendor statement is not the only acceptable route
to establishing a bridge. Source provenance plus independent measured feature
correspondence can test a versioned identity hypothesis. This report does not
declare that hypothesis passed.

## Challenge resources traced to primary data

The live [NASA Space Apps Resources tab](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/?tab=resources)
was revisited through Aside. Its QuickMap, Moon Trek, Horizons and Canadian
Space Agency links were investigated alongside the terrain source families
listed on the [official Cesium Moon page](https://cesium.com/platform/cesium-ion/content/cesium-moon/).
Aside's Google Search skill and complementary technical indexing located the
underlying source labels and control documentation. Only primary data and
research sources support the findings below.

| Source | What it establishes | Boundary |
| --- | --- | --- |
| [LOLA polar PDS label](https://imbrium.mit.edu/DATA/LOLA_GDR/POLAR/JP2/LDEM_875S_5M_JP2.LBL) | Body-fixed, DE421 mean Earth/polar axis, planetocentric/east coordinates, 1,737,400 m reference radius; native DN scale 0.5 m. | Identifies the source grid, not independently measured scene alignment. |
| [SLDEM2015 PDS label](https://imbrium.mit.edu/DATA/SLDEM2015/GLOBAL/JP2/SLDEM2015_512_60S_60N_000_360_JP2.LBL) | The midlatitude source also specifies DE421 mean Earth/polar axis and the same reference radius. | Supports testing the same source-to-scene hypothesis; no mission trajectory or contact validation. |
| [NASA SLDEM2015 product description](https://pgda.gsfc.nasa.gov/products/54) | Documents co-registration of Kaguya terrain with the LOLA geodetic framework and access to the numerical product. | Product quality is distinct from renderer residuals. |
| [NASA Apollo site coordinates](https://nssdc.gsfc.nasa.gov/planetary/lunar/lunar_sites.html) | Explicit planetocentric DE421 mean Earth/polar-axis coordinates for actual human-made features. | Near-side controls alone are not well-distributed global terrain controls. |
| [LROC human-feature coordinates](https://www.lroc.asu.edu/data/support/downloads/2016_LROC_Coordinates_of_Human_Features.pdf) | Supplies elevations and uncertainty discussion, in addition to feature coordinates. | Small tabulated uncertainties must not be mistaken for complete absolute spacecraft/control-network accuracy. |
| [LROC positioning research](https://doi.org/10.3847/PSJ/ad54c6) | Explains controlled and uncontrolled NAC image placement; recommends checking DTM orthophotos and control quality. | One-meter image pixels do not establish one-meter geolocation. |
| [Moon Trek API](https://trek.nasa.gov/tiles/apidoc/trekAPI.html?body=moon) | Documents layers and WMTS access useful for source discovery and image comparison. | A rendered WMTS image is not automatically numerical elevation. |
| [JPL Horizons manual](https://ssd.jpl.nasa.gov/horizons/manual.html) | Documents lunar coordinate conventions and independent celestial geometry checks. | Does not supply terrain fiducial residuals against this Cesium asset. |
| [Canadian Space Agency Moon exploration](https://www.csa-asc.gc.ca/eng/astronomy/moon-exploration/) | Provides lunar mission and partner context. | Does not define the Cesium terrain control network. |

Additional independent numerical terrain products with confidence maps and
product metadata include [TYCHOPK](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_TYCHOPK),
[TSILKVSKIY2](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_TSILKVSKIY2)
and [SHACKRDGE02](https://data.lroc.im-ldi.com/lroc/view_rdr/NAC_DTM_SHACKRDGE02).
Their published LOLA agreement statistics are properties of those source products,
not measured residuals of the streamed Moon asset.

## What was actually measured

A separate local diagnostic loads only Moon asset 2684829, with the Moon sphere,
identity scene/model transforms, no analysis entities and no vertical
exaggeration. It calls the public Cesium `clampToHeightMostDetailed` API. Returned
world Cartesian positions already include tile transforms; those transforms are
not applied a second time. Requests are explicitly marked
`identity_for_measurement_only`. The code cannot enable scientific overlays.

Aside's local diagnostic page reset during measurement. Installed Chromium then
completed four control probes and a 100-probe polar-patch experiment with no page
or console errors. The query width was 0.1 m. This width is an intersection-volume
setting, not a 0.1 m geolocation accuracy claim.

Four center probes were also compared with independently read pixels from the
published [20 m polar DEM label](https://imbrium.mit.edu/DATA/LOLA_GDR/POLAR/JP2/LDEM_80S_20M_JP2.LBL)
and its JP2 product. The same DE421/radius convention applies. Native signed DN
was decoded as elevation `DN * 0.5 m`; adding 1,737,400 m yields radius. These
are nearest-pixel diagnostics, not precision terrain-fiducial correspondences.
The high-resolution count mask was not acquired, so no claim of individually
measured ground returns is made for these pixels.

| Seed latitude / east longitude | Renderer height relative to 1,737,400 m | Source nearest-pixel height | Radial difference |
| --- | ---: | ---: | ---: |
| -85°, 0° | -263.904 m | -675.5 m | +411.596 m |
| -85°, 90° | -3287.349 m | -3722.5 m | +435.151 m |
| -85°, 179° | -3554.291 m | -3903.5 m | +349.209 m |
| -85°, -90° | -1895.029 m | -2306.0 m | +410.971 m |

These differences are a reason to investigate, not a calibrated frame offset.
They could involve the mesh conversion, a source-product difference or the
renderer sampling method. Sampling at a coordinate chosen under an identity
hypothesis only checks radial behavior. It cannot independently establish that
the same crater/ridge was found horizontally. The 100-probe experiment also
contains weak terrain correspondence and larger outliers in some patches; a
favorable correction or tolerance was not fitted to make it pass.

The known midlatitude child scale would add 1,900 m to the nominal lunar radius
if it were applied directly. It must not be copied onto engine coordinates:
it is already part of the asset's tile-space conversion. Neither that scale nor
the radial differences above justify rewriting the numerical DEM or a global
visual nudge. A depth-buffer variation did not produce a completed measurement;
no conclusion is drawn from that attempted sensitivity check.

A synthetic-plane instrument calibration was also attempted in an isolated,
intercepted diagnostic scene, but timed out without a completed capture. It is
not counted as validation of the sampler, and no calibration result is inferred.
Instrument accuracy remains part of the unresolved measurement work.

## Reproduce and continue the check

Raw requests, successful captures, reference pixel records and derived radial
diagnostics are in `fixtures/registration/`. Source hashes and URLs are in
`data/renderer-registration-source-audit.manifest.json`. No token or tile binary
is included. The ignored local token and running Vite dev server are required
for a fresh capture:

```sh
node web/scripts/capture-registration.mjs fixtures/registration/four-polar-probes.json /private/tmp/four-polar-capture.json
```

Set `SOMA_BROWSER_EXECUTABLE` to an installed Chromium when necessary. The local
developer page is `http://127.0.0.1:5173/registration.html`; it is not included in
the production entry point. Requests and capture work have explicit bounds, and
unknown hits remain null. Source-frame geometry and radial comparison remain
Python work; the browser records mesh observations only.

The next registration evidence must independently match terrain features in
numerical source patches and the actual mesh, separate horizontal/radial
differences, test query repeatability and justify a tolerance for the intended
display scale. The available source documents now support that work. No user
needs to locate or purchase additional coordinates merely because the ion JSON
omits a frame name. PR #8's guarded numerical integration can merge while this
measurement investigation remains separate. Full Phase 5 map acceptance and
Phase 6 are not claimed.

## Verification of this research handoff

The owner ran 307 engine tests, 60 interface unit tests and the production build;
all pass. The recorded live relay run independently replays with zero errors and
104,857,600 unique delivered bytes. Source/fixture hashes are checked. New tests
reject duplicate or foreign measurements, nonfinite values, excessive probe
work and falsely registered requests. Missing reference or mesh samples remain
unknown. No native scenario/result schema or scheduling equation changed.

The diagnostic is a draft developer tool, ENERGY 1 / RHYTHM 1 / MOTION 1. Its
request/result areas are native named textareas; actions, cancellation, status,
unknowns and downloads have explicit labels. Successful captures exercise the
real request and completion path. The capture script and input validation add
no registration approval path. This is a scientific investigation artifact,
not a completed product-map acceptance claim.
