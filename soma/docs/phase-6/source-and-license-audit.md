# Phase 6 source, license and challenge audit

Reviewed 15 November 2026 against merged baseline `7c7033a`, on
`engine/phase-6-validation`. This bounded review implements the source/claims
checks in AGENTS Phase 6 and plan Part 5. It does not establish legal clearance
for a hosted product, complete dependency SBOM, or complete challenge fulfillment.

## Findings and release gates

The numerical source exclusion boundary is intact: `git ls-files` found no
kernel, DEM/geoid raster, b3dm/glb, or paper PDF payload. Source URLs, hashes,
derived measurements and SOMA code are shipped; external binaries are locally
acquired. This is distinct from the build, which copies Cesium runtime assets.

**The licensing review is complete for the declared localhost R&D scope.** This
is a bounded source and notice review, not formal legal clearance or a grant of
new rights. The
[current ion terms](https://cesium.com/legal/terms-of-service/), read live with
Aside, contain the following grants, conditions and unresolved interpretation:

- Section 2.2(a–c) expressly grants application R&D and internal use, graphical
  display internally and externally, and demonstrations to third parties,
  subject to the account, plan, term and other conditions. Ordinary localhost
  development is within the described R&D purpose; public operation of a
  service is a separate question.

- Section 2.2.2 allows client/proxy caches only as general caching mechanisms
  that also cache other internet traffic. The audit identified a dedicated
  converted-Moon LRU in the baseline. During Phase 6 it was removed; the final
  `RegisteredMoon.get` refetches content and responses are `private, no-store`.
  This resolves that dedicated-cache finding without claiming broader rights.
- Section 2.2.4(iii) restricts decoding, reverse assembly, reverse compilation,
  reverse engineering, translation and reduction to human-perceivable form.
  Section 1.10 includes content and Data Output within Licensed Services, so
  this restriction cannot simply be dismissed as applying only to software.
  Neither provision expressly classifies documented-format geometry processing
  or the empirical inverse-ingestion conversion in
  `soma/geometry/renderer_mesh.py`. This audit establishes neither that the
  correction is definitely permitted nor that it is prohibited. The earlier
  inference that absent transformation-specific permission necessarily creates
  a vendor-approval gate for local Phase 6 engineering was unsupported. A token
  supplies access, not independent legal clearance.
- Section 2.2.3 requires prominent Cesium ion branding and preservation of
  proprietary notices. The copy script preserves software notices, the viewer
  retains its normal credit display, and `correct_tileset` deep-copies root
  metadata. The custom path still calls `fromIonAssetId`; pinned Cesium's
  `IonResource.credits` maps endpoint attributions, and tileset `createCredits`
  clones those resource credits. Thus changing the loadJson payload does not
  itself drop normal endpoint credit propagation. Phase 5 records actual logo
  and Data attribution; this audit did not requery the live remote credit panel.
- Sections 2.1–2.2 and 2.2.1 tie use to the account/plan and restrict access and
  services for third parties. Section 2.2.6 requires communicating the conditions
  to employees/contractors and makes the account holder responsible; it does not
  prescribe a transformation approval process. Future public hosting or a
  transformed stream offered to third parties needs its actual account/plan and
  intended use reviewed. Those rights and any organization-specific agreement
  remain unknown; do not infer them from the development token.

[Appendix A](https://cesium.com/legal/cesium-global-3d-content-tos/) explicitly
includes Cesium Moon as Global 3D Content. Its terms are separate from the
Apache-2.0 CesiumJS library. The freshly read
[Content Usage and Attribution Guide](https://cesium.com/learn/ion/content-usage-and-attribution-guide/)
expressly allows streaming assets into software inside and outside an
organization and publishing attributed renderings with an active account.
Section 2.3 grants special Clip/Value-Added Clip rights; these fetched Moon
tiles are not documented ion clipping-feature output. No express permission
for this empirical ingestion-inversion transformation was established in
these sources, and neither was a specific prohibition established. The official
[global content page](https://cesium.com/platform/cesium-ion/content/) describes
planning, analysis, modeling and simulation using open standards in custom
applications. The [Moon page](https://cesium.com/platform/cesium-ion/content/cesium-moon/)
describes visualization, simulation and analytics, with a Moon-ellipsoid example.
These support ordinary geometry consumption as intended usage; they do not
conclusively classify SOMA's empirical correction. The guide defers to the terms
and any organization agreement. Future deployment review is separate from local Phase 6 engineering and
browser-independent
synthetic schedules and the offline text/results workflow. No contact with
Cesium or external publication was performed by this audit.

## Phase 6 completion review

The completion review uses merged baseline `29c67b7`. The applicable acceptance
scope in AGENTS Phase 6 and plan Part 5 is the integrated service/interface
verification: independent exported-schedule replay, exact display/result
agreement, map-failure fallback, controlled comparisons and computed demo,
sensitivity reporting, reproducibility, visible assumptions, and source/license
and attribution checks. Plan source-register D12 calls for checking intended
usage, account limits and current terms when the application is deployed; it
does not require a public deployment or vendor correspondence to finish local
validation. This audit completes the licensing-review portion for the declared
localhost R&D scope, without deciding the remaining engineering checks on its own.

No public hosting or Cesium vendor correspondence was requested or performed.
Future hosting, transformed-stream distribution, commercial integration, offline
bundling and changes in account/plan require review against their actual scope.
Those future questions are not a mandatory permission gate for the current local
Phase 6 completion. No binary redistribution rights are expanded by this review.

## Sources and rights actually inspected

| Input or component | Actual use/bundling | Rights and exclusions |
|---|---|---|
| SOMA | Source, generated numerical evidence and fixtures | Root `LICENSE` is GPLv3; third-party notices remain separate. This review does not relicense upstream components. |
| CesiumJS 1.147.0 | npm dependency; `web/scripts/copy-cesium.mjs` copies Workers, Assets, ThirdParty, Widgets and LICENSE/ThirdParty JSON into ignored public build assets | Apache-2.0: preserve license, copyright/attribution and applicable notices, mark modified upstream files, no trademark or endorsement grant. Its third-party inventories have separate obligations. Inspect the deployed build, not only Git. |
| Python runtime | Pinned jsonschema, referencing, rfc8785; optional numpy, SpiceyPy, Rasterio, pyproj, PuLP, FastAPI, uvicorn; Skyfield for verification | Installed notices inspected; dependencies installed separately, not vendored into source. MIT/BSD-style notices require retention on redistribution; NumPy, Rasterio/GDAL and pyproj/PROJ contain additional upstream notices. A future standalone binary/container needs its own full transitive inventory. |
| PuLP/CBC | PuLP invokes installed solver; no solver binary tracked | PuLP's inspected notice is MIT. That notice is not a license for CBC; preserve CBC and linked Coin-OR notices if packaging the solver. This review does not approve a new redistributed solver bundle. |
| Matched NAIF kernels | `data/de421-phase2.manifest.json` pins sources, coverage and hashes; binaries local only | [NAIF rules](https://naif.jpl.nasa.gov/naif/rules.html), freshly read in full, permit anyone to download/use NAIF-hosted kernels and redistribute them unmodified. Modified kernels require new producer attribution, metadata/validation and changed names. Other distributors' kernels retain their own terms. Toolkit mirror redistribution requires prior written clearance, while including Toolkit modules in a customer-built tool is permitted. These distinctions must not be collapsed into a blanket “SPICE is open source” claim. |
| PGDA LOLA product 81 and far LOLA/PDS grids | Numerical local extracts only; manifests preserve parent, count mask, bounds, units, source labels and available hashes | [Product 81](https://pgda.gsfc.nasa.gov/products/81), freshly read, specifies 5 m GeoTIFFs, DE421 MOON_ME and Barker et al. (2021) citation. It requests citation when using products. No explicit standalone redistribution license was established here; keep current local-only distribution. The full elevation-parent hash remains unknown and must stay so. A NASA link is not a grant for every hosted asset. |
| EGM96 conversion grid | Local `us_nga_egm96_15.tif`, pinned SHA-256; not shipped | [Actual PROJ CDN notice](https://cdn.proj.org/us_nga_README.txt), freshly read in full, explicitly labels this converted NGA EGM96 grid Public Domain. No need to infer its terms from general PROJ software licensing. Its role is reversing a terrestrial display ingestion term, never an Earth correction to lunar physics. |
| TATC, MMGIS, HDTN, papers | Method/reference citations, not runtime forks or tracked source trees/binaries | No copied upstream implementation was identified in this bounded inspection. `soma/terrain/horizons.py` explicitly attributes Barker's method and uses SOMA Cartesian sampling. TATC BSD-3-Clause and MMGIS Apache-2.0 would require retained notices for any future copied code; citations alone do not grant paper-republication or NASA endorsement rights. HDTN/ION are not vendored. |

## Inspected notices and hashes

These are SHA-256 of the actual local notices, not inferred package labels.
Python paths below are relative to `.venv/lib/python3.14/site-packages/`.

| Path | SHA-256 |
|---|---|
| `LICENSE` | `ecf4196079344056efdfe6f73d1e28cb4c982dc82ec7a4887c8bb2e177798a12` |
| `web/node_modules/cesium/LICENSE.md` | `721844bc0cdaa9b1a9a145dbca1f981e2de15a7e200a5d1fd9f5f1eed8e5d030` |
| `web/node_modules/cesium/ThirdParty.json` | `2e1b5a86e6814c091d886b14bab17e266118e1fddb24dc113c4474731b51ae9a` |
| `web/node_modules/cesium/ThirdParty.extra.json` | `5fff210f16bcbe0d414a4f634ceb2b0564dad92065733c26ec3ee4aff89a4b10` |
| `web/node_modules/ajv/LICENSE` | `a05350a88e318e4f5f2c2a1ff1e2e88daa4dd38e6e78b71cccae422bdc762cc3` |
| `web/node_modules/ajv-formats/LICENSE` | `9df3bb69929a3b650ed73b3bfa1756725aaff0ac296461605753547004eafeaf` |
| `web/node_modules/vite/LICENSE.md` | `a22152baa1aef74402443008e767e7c689a524c0909d19b0431d97f5ab066a13` |
| `spiceypy-8.4.0.dist-info/licenses/LICENSE` | `77f7749eb7c6acfbaefed8c60c7a84820f905328d83ec4c5454c593571b9fc1f` |
| `rasterio-1.5.2.dist-info/licenses/LICENSE.txt` | `7666d012678c262c12e4e1ac77c0d1a2080bf020dd19c6745a2e4e874d8208d4` |
| `pyproj-3.8.0.dist-info/licenses/LICENSE` | `a652687151814d4c4715445912fcb49e7e58f5b248d47a1a88b859a8815e0822` |
| `pyproj-3.8.0.dist-info/licenses/LICENSE_proj` | `ac9caff7979c906774d756815d1d473145284ba7ba9a5ef1c5fa77e6a30cef82` |
| `numpy-2.5.4.dist-info/licenses/LICENSE.txt` | `649a589ab31076e79e9ce62ba24eae9959598124176640dbc95f87bd10f34fcf` |
| `pulp-3.3.2.dist-info/licenses/LICENSE` | `b41bca287571c8ac88dc634f7ccbad0910f5fe42e38fefe1304c3c3b85b94aec` |
| `fastapi-0.163.0.dist-info/licenses/LICENSE` | `4ec89ffc81485b97fec584b2d4a961032eeffe834453894fd9c1274906cc744e` |
| `uvicorn-0.54.0.dist-info/licenses/LICENSE.md` | `efe1acf3e62fb99c288b0ec73e5a773b7268ef4320fe757ea994214e4b63c371` |
| `jsonschema-4.26.0.dist-info/licenses/COPYING` | `4f92a015a13c4d1a040bef018aa13430b4f1bc73b41b16bb846c346766de7439` |
| `referencing-0.37.0.dist-info/licenses/COPYING` | `42dcd63495f87b4eb7c7757afa379bb55a53f94afd7a5f657d9adf57236e515c` |

## Official 2026 challenge alignment

Both [Details](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/?tab=details)
and [Resources](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/?tab=resources)
were freshly read through Aside. The page identifies the 2026 event. The brief
asks for rapid lunar site/date evaluation and local Sun/Earth geometry; most
listed UI/technical considerations are optional suggestions. Relay scheduling
is SOMA's extension. Resources list Quickmap, Moon Trek, Horizons and CSA Moon
Exploration, with external-terms and no-NASA-endorsement boundaries.

| Objective | Evidence in completed reduced scope | Explicit gap |
|---|---|---|
| Site/date exploration | Scenario input, selection/fallback, immutable engine jobs and comparison checks | Arbitrary physical site/date replanning is not established. Coverage errors remain unknown; a controlled successful physical two-site/date demonstration is missing. |
| Local Sun/Earth and horizon | Python scientific exports and observer-specific graphics | Real measured-terrain horizons have unknown/nonconverged samples. Synthetic skylines do not prove real visibility. |
| Power and direct communications | Separate generation/battery records, direct baseline, contact gates and independent replay | Synthetic rates/calendars and incomplete real terrain prevent an operational site viability conclusion. |
| Temporal dynamics | Timeline uses exact engine contacts/allocations and receiver availability | A contact-only synthetic relay has no physical state; it cannot support a real spacecraft animation. Sunset/Earthset prediction and long seasonal exploration are not demonstrated by that case. |
| Broad accessibility and usable comparisons | Text result and exported package remain useful without tiles | No audience usability study, speed benchmark or general mission-planning validation is claimed. |

The reduced reschedulable transfer demonstration is supported by plan Part 5,
but it does not complete every challenge objective. No general event submission
rules, judging rubric or submission deadline were verified in this audit.

## Claims and credential boundary

`README.md`, `soma/engine.py`, `soma/exports/`, `soma/docs/` and `web/src/`
were searched for endorsement, compliance, certification and success-probability
claims. No positive NASA/JPL endorsement, SABR/LunaNet compliance, flight
certification, thermal-survival or statistical mission-success claim was found
in that bounded search. Registration “certificate/certified region” denotes
relative display tests only, as explicitly scoped in the map-alignment report;
it must not be presented as navigation or mission certification.

`web/.gitignore` excludes `.env.local`; root excludes virtualenv/build outputs.
The proxy retains source credentials internally and exports no credentialed
source URL. Browser Vite tokens remain browser-visible by design: scoped asset
and URL access is required, and the frontend token is not a server secret. This
audit never printed tokens, signed endpoints or private account details.

## Reproduction and audit limits

Read AGENTS.md, plan source register and delivery chapter, existing challenge
alignment, data manifests, terrain attribution, viewer/copy script and Moon
proxy. Commands: `git ls-files` restricted to binary/notice extensions;
`rg -n` for claims/credits; Python `hashlib.sha256(path.read_bytes())` for
the notice table. Browser: `aside guide`, `aside guide repl`, `snapshot` and
complete text reads of the NAIF rules, ion terms and EGM96 notice. Aside's
initial local sandbox connection denial was retried with approval and succeeded.
The guessed `.html` geoid notice did not exist; the actual `.txt` notice was
then located and read. No tests were needed for this documentation-only audit.

The transformation's contractual classification and future deployment/account
rights remain unresolved interpretations for a future deployment review, not
blockers inferred for the declared local Phase 6 engineering scope. The dedicated
cache issue is fixed and credit propagation has static evidence. Accepted scientific limitations are
synthetic assumptions, missing real terrain/spacecraft states and incomplete
physical site/date comparison. They must remain visible rather than being
converted into favorable mission or complete-challenge claims.
