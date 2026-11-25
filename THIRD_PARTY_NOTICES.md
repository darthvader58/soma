# Third-party software and data

SOMA's source code is distributed under the GNU General Public License,
version 3. The project license does not replace the terms of its dependencies,
scientific datasets or display content. No NASA, JPL, Caltech or university
endorsement is implied.

## Retained NAIF Earth-orientation kernel

The Python distribution includes the original, unmodified file
`data/pinned/earth_000101_270208_261113.bpc`, produced and distributed by NASA
NAIF at Caltech's Jet Propulsion Laboratory. Its embedded comments and producer
attribution are preserved.

- Original URL: <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/earth_000101_270208_261113.bpc>
- Size: 5,163,008 bytes.
- SHA-256: `6e77690ba455a644e509b0b9cb308b0dec1a7154ceecf3355659b917b21ca45e`.

The [NAIF rules](https://naif.jpl.nasa.gov/naif/rules.html), reviewed on
25 November 2026, permit redistribution of unmodified NAIF-distributed kernels.
Those rules also describe warranties, support limits and the different terms
for Toolkit redistribution. SOMA does not redistribute a SPICE Toolkit mirror.
SpiceyPy and its dependencies are installed separately under their own terms.
The kernel is retained because its original rolling URL no longer serves the
pinned bytes; see [the preservation record](data/pinned/README.md).

## Separately acquired scientific data

Other SPICE kernels and numerical LOLA terrain are acquired explicitly from
the sources recorded in SOMA's dataset manifests. They are not automatically
downloaded on import, and the full numerical datasets are not included in the
Python distribution. Preserve their source metadata, checksums, attribution and
applicable provider terms when sharing a run or redistributing data.

LOLA products used by the terrain model are described in the
[NASA PGDA product documentation](https://pgda.gsfc.nasa.gov/products/81) and
the research citations in the source register. A software license does not
relicense those datasets.

## Web display content

CesiumJS is an Apache-2.0 dependency of the separate web application. Its
software notices and third-party inventories must accompany redistributed web
builds. Cesium ion and Cesium Moon content have their own access, usage and
attribution terms; no Cesium Moon tiles or access tokens are bundled in the
Python release.

The web application uses NASA Earth Observatory's November 2004 Blue Marble
reference composite, produced by Reto Stöckli at NASA Goddard Space Flight
Center. Its original image and attribution are recorded in
[the asset manifest](data/earth-display-texture.manifest.json). The image is
web display content and is excluded from the Python wheel and source archive.

## Dependencies and prior work

Python dependencies, including NumPy, SpiceyPy, Rasterio/GDAL, pyproj/PROJ,
PuLP and solver components, retain their respective licenses and notices.
SOMA installs these dependencies rather than incorporating their distributions
into its own wheel. A standalone application or container that redistributes
them must preserve their notices too.

TAT-C supplies architectural precedent; MMGIS and NASA's DTN work are cited
references. SOMA does not vendor their source trees or claim their capabilities
as its own. Research papers establish the cited methods, not validation of a
complete SOMA mission plan. See [the research register](plan/06-Research-and-Source-Register.md).
