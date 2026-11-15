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
For this original -85-degree experiment, the high-resolution count mask was not
acquired, so no claim of individually measured ground returns is made for these
older pixels. Later count-masked inner-cap measurements are documented below.

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

A later synthetic-plane calibration completed successfully. Four planes centered
exactly 1,000 m below the reference sphere were sampled within 0.007207 m of
their analytical intersections. The portable harness confirms its Vite module
replacement and runtime marker, blocks asset requests, and records zero blocked
requests, page errors and console errors in the successful run. No Moon asset is
loaded in this calibration. An earlier interception failed to match a Vite query
suffix and sampled the real Moon instead; that attempt is excluded. A subsequent
overbroad request guard rejected a local credit image; its failed capture is
also excluded. A successful simple-plane check does not establish terrain
registration or validate the underlying asset conversion.

## Inner-polar checks and independent mesh intersections

The original four queries sit on the 85-degree source-resolution boundary.
Additional controls were therefore selected from the numerical source first,
in four declared south-polar quadrants. Within each quadrant's search window,
selection favored a local peak with a positive measured count, a height drop in
four directions at 500 m, and more than 70% positive-count coverage in a 4 km
square. Renderer results were not used to select these seeds. This selection
does not yet establish unique landmark correspondence.

The complete [20 m inner-cap elevation](https://imbrium.mit.edu/DATA/LOLA_GDR/POLAR/JP2/LDEM_875S_20M_JP2.LBL)
and [matching count product](https://imbrium.mit.edu/DATA/LOLA_GDR/POLAR/JP2/LDEC_875S_20M_JP2.LBL)
were acquired and hashed, including both labels and rasters. This supplements
the earlier remote-pixel experiment; it does not retroactively add a count mask
to those older pixels. Pixel centers and the same DE421 stereographic convention
were preserved. Native contributing height/count values are retained in the
new reference fixture. A zero-count contribution stays unknown.

| Source-first seed latitude / east longitude | Source height | Mesh minus source height | CPU versus GPU mesh intersection |
| --- | ---: | ---: | ---: |
| -88.338816°, 44.501369° | -3887.0 m | +659.036 m | 0.021572 m |
| -88.390838°, 139.038295° | -31.0 m | +657.102 m | 0.056688 m |
| -88.521780°, -141.066720° | -2867.5 m | +656.151 m | 0.050204 m |
| -88.436863°, -43.700766° | -509.0 m | +651.284 m | 0.020350 m |

Around each seed, a 9 by 9 grid at 200 m spacing produced 324 completed mesh
queries without page/console errors. Of those, 244 have a positive-count source
comparison; the other 80 remain unknown. The four unshifted patch medians are
+659.036, +658.122, +658.549 and +660.695 m. Height correlations are 0.988, 0.982,
0.917 and 0.965. No fitted shift, height correction or release tolerance is used
in these reported statistics. Similar relief helps locate the discrepancy;
it does not turn coordinate-directed rays into independently matched landmarks.

A separate CPU calculation decoded the actual loaded level-14 south-polar
triangles. It applied the captured tile transform, glTF axis conversion and node
matrices once, then intersected the same radial rays with those triangles. The
four CPU/GPU positions agree within 0.057 m. A second capture through the portable
harness reproduced the same tile hashes and intersections. The comparison makes
a simple depth-reading error less likely and confirms the height difference
against this reference persists in the decoded asset geometry. It does not yet
identify whether a source-version/resolution difference, datum interpretation or
asset conversion causes it. The advertised finest inner-cap source is 5 m,
whereas this independent count-masked reference is 20 m; those are explicitly
different products.

The exact advertised 5 m product was then downloaded and hashed with its count
mask and labels. None of the 324 original query locations has four positive-count
5 m contributors for bilinear interpolation, so all those precision reference
comparisons remain unknown. Interpolated fill is retained as a separately named
product value and is not used as a measured reference.

To make a measured comparison at that resolution, the nearest positive-count
5 m pixel to each predeclared source seed was selected, 3.54 to 10.61 m away.
These four new queries completed without page/console errors. Their mesh-minus-
source differences are +658.615, +657.104, +656.878 and +650.260 m. Each source
pixel has one measured return. This evidence indicates that the 20 m resolution
alone does not explain those four differences. It still does not establish the
underlying datum or conversion cause, or a passing horizontal landmark bridge.

The observed differences are not accepted frame residuals and cannot justify
subtracting a fitted height or weakening the release tolerance. Four global
catalog candidates remain unmeasured. The source-frame documentation is found;
the remaining work is a verified source-to-mesh bridge and independently matched
feature positions with a justified spatial scope and tolerance.

## Reproduce and continue the check

Raw requests, successful captures, reference pixel records and derived radial
diagnostics are in `fixtures/registration/`. Source hashes and URLs are in
`data/renderer-registration-source-audit.manifest.json`. No token or tile binary
is included. The ignored local token and running Vite dev server are required
for a fresh capture:

```sh
node web/scripts/capture-registration.mjs fixtures/registration/four-polar-probes.json /private/tmp/four-polar-capture.json
```

The calibration requires the local Vite server but does not require ion access:

```sh
node web/scripts/capture-registration-calibration.mjs fixtures/registration/four-polar-probes.json fixtures/registration/calibration-planes.json /private/tmp/instrument-calibration.json
```

To repeat the raw mesh and CPU comparison with the scoped local token:

```sh
node web/scripts/capture-registration-mesh.mjs fixtures/registration/inner-polar-probes.json /private/tmp/soma-mesh-check
.venv/bin/python soma/docs/phase-5/inspect-mesh.py /private/tmp/soma-mesh-check /private/tmp/cpu-intersections.json
```

Binary tiles stay outside the repository. The inspection script supports the
observed uncompressed float-position, matrix-node v6 tile profile and rejects
unsupported inputs. The retained fixture contains a few measured triangle
coordinates and hashes, not tile binaries. `inner-polar-reference.json` retains
the source samples and count masks needed to recompute the recorded radial
differences without downloading the full raster again.

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
omits a frame name. PRs #8 and #9 have merged. They supply the guarded numerical
integration and source investigation; merging them does not establish the
missing alignment evidence. Full Phase 5 map acceptance and Phase 6 remain
unclaimed.

## Verification of this research handoff

The owner ran 319 engine tests, 60 interface unit tests and the production build;
all pass. A fresh relay run independently replays with zero errors and
104,857,600 unique delivered bytes. Source/fixture hashes are checked. New tests
reject duplicate or foreign measurements, nonfinite values, excessive probe
work and falsely registered requests. Calibration, CPU triangle intersections
and count-mask preservation are checked separately. Missing reference or mesh samples remain
unknown. No native scenario/result schema or scheduling equation changed.

The diagnostic is a draft developer tool, ENERGY 1 / RHYTHM 1 / MOTION 1. Its
request/result areas are native named textareas; actions, cancellation, status,
unknowns and downloads have explicit labels. Successful captures exercise the
real request and completion path. The capture script and input validation add
no registration approval path. This is a scientific investigation artifact,
not a completed product-map acceptance claim.
