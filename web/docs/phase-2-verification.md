# Developer B Phase 2 verification

Verified 14 November 2026 against `AGENTS-B.md`, the seven shared plan chapters,
and the frozen JSON schemas. Two GPT-6.1 Sol agents handled the bounded viewer
implementation and independent read-only acceptance review. The owner integrated
the form and timeline changes, reviewed the code and screenshots, and ran the
combined checks. This is a **draft without direction**, with ENERGY 1 / RHYTHM 1 /
MOTION 1. The existing reading panels, viewport and primary action remain the
design direction documented in [design.md](design.md).

## Acceptance evidence

| Phase 2 requirement | Observed behavior |
|---|---|
| Official Moon setup and token boundary | Moon ellipsoid set before Viewer construction; globe and Earth controls disabled; ion asset 2684829; no evaluation token fallback. Without a token, no Cesium import or tile request occurs. |
| Fixture selection | Direct and single-lunar-relay fixtures load independently of a running engine service. The 100 MiB task and common hardware remain explicit. |
| Click selection | A valid Moon tileset/depth pick creates a raw-Cartesian marker labelled as display-only and unresolved. Sky, unrelated assets and absent/invalid depth cannot create a point. |
| Analysis point boundary | The immutable synthetic fixture point remains distinct from renderer picks and edited scenario coordinates. No selected render height becomes terrain, antenna or panel height. |
| Typed coordinates and profiles | Editable numerical fields round-trip while hidden resource limits, frame/datum, units and provenance remain unchanged. Edited inputs clear previous results. |
| Baseline routes | Direct and lunar-relay choices use declared profiles; synthetic labels remain visible. Earth-orbit relay is explicitly disabled. |
| Date/deadline rule | The form states that the absolute deadline and analysis horizon remain fixed when site or data-ready time changes. A browser check confirms this behavior. |
| Shared timeline | Map clock and time control share one timestamp. Exact supplied endpoint strings, fractional seconds and offsets remain visible. Intermediate slider values are labelled UTC and millisecond precision. Scrubbing preserves the result and job state. |
| Invalid time horizon | A reversed/invalid interval disables scrubbing and explains the correction required, without changing map time. |
| Tile and renderer failures | Scene resources/listeners and display selections are cleared. Stale callbacks cannot create another pick; the scenario, result and downloads remain available. |
| Accessibility and layout | Keyboard interaction, named native controls, focus, 200 percent text resizing and 390/820/1440-pixel overflow checks pass. |

The browser suite tests the real offline app and its controls. One explicitly
labelled renderer-event module exercises the host's pick/time/failure boundary;
it is a test fixture, not an observation of Moon streaming. Node viewer runtime
tests inject a Cesium test double to exercise the actual viewer control flow.
Neither kind of mock establishes real tile rendering or frame registration.

All 30 Node tests and 11 Chromium browser tests pass. Browser console/page-error
collections are empty, and the production build succeeds. The viewer tests
include a render failure while the asset request is pending: fallback persists
and a late tileset is destroyed instead of producing a misleading ready state.

Reproduce the checks from `web/`:

```sh
npm test
npm run build
npm run test:browser
```

Set `SOMA_BROWSER_EXECUTABLE` if using an already installed compatible Chromium.
The owner inspected the current desktop, tablet and mobile captures. The saved
screenshots show the actual missing-token fallback:
[desktop](screenshots/phase-2/desktop.png),
[tablet](screenshots/phase-2/tablet.png),
[mobile](screenshots/phase-2/mobile.png).

## Delivery gate

The owner reran the [Phase 1 R-01 through R-40 gate](verification.md#delivery-gate)
against the Phase 2 changes. All rules pass for this scoped visual draft.
No decorative visual system, assets, unsupported claim or invented scientific
output was introduced. Changed copy uses plain labels and no em dash. Native
controls retain their focus, contrast and size; no automatic motion was added.
Unavailable Earth-orbit routing is visibly disabled. New draft, pick, invalid
interval and map-failure states have explicit text, and all active controls were
exercised. Responsive screenshots and the enlarged-text check remain clean.

Liveliness passes for the declared dials: Plan delivery remains the focal action,
the numbered workflow and precise scientific labels identify the application,
and spacing separates input, map, timeline and result. Craftsmanship passes:
the added content explains actual task boundaries, the form and result survive
map absence, and every displayed number has an identified fixture/input source.

Source inspection finds no browser Friis formula, battery integrator, horizon
ray caster, orbital propagator or path solver. Coordinate conversion for a
renderer pick and placing existing intervals on a timeline are display operations.

## Scope and remaining gates

Developer B Phase 2 is accepted through its explicitly permitted honest-fallback
branch. No scoped ion token was supplied. Real ion streaming, actual surface
picking and the marker's appearance on streamed terrain remain unverified.
The runtime tests establish behavior under controlled events only.

All registered engine lander/orbit/Sun/contact overlays remain blocked. A
versioned transform, measured landmark residuals and live analysis-point
resolution belong to the integration gate. The fixture point is synthetic and
is not presented as a live DEM-resolved point. Delivery results remain
`unknown` / `unresolved` / `not_implemented`. Phase 3 scientific graphics,
illumination/power/usable-contact integration and saved-result comparison are
not claimed by this report. Python's separate Phase 2 geometry diagnostics are
documented in the [engine evidence](../../soma/docs/phase-2/README.md).
