# Hosted deployment verification

Verified on 16 November 2026 using Aside in the signed-in browser.

- Application: https://soma-atlas-two.vercel.app/
- Library documentation: https://soma-ce3178ca.mintlify.site/
- Runtime and presentation source: `445d5c9` on `web/hosted-planner-fix`.

The hosted application displays exact, captured Python calculations. New site,
date, or hardware calculations require the full Python engine and its datasets.
The Vercel function performs the existing registered mesh conversion only.
No physics, scheduling, or visibility calculation was added to JavaScript.

## Live checks

| Check | Evidence |
| --- | --- |
| Default result | Physical direct-delivery run loads automatically; feasible under assumptions, proven optimum. |
| Controlled failure | Later direct case reports infeasible in the discretized model and explains that 0 available payload bits cannot carry the 134,217,728-bit file. |
| Relay result | Later relay case shows two transmissions, four source/receiver lanes and three storage reservations. Feasible incumbent remains distinct from a proven optimum. |
| Stored state | At `2026-11-30T09:33:30Z`, the relay position is `[295639.4303804659, -698665.101793075, -1785126.1758989308]` m in the declared renderer frame. The browser reads this engine-authored record. |
| Actual rendering | Moon terrain, site, stored relay and allocated contact were visually inspected; Cesium ion attribution remains visible. |
| Registration | Versioned conversion remains `aa08fa4b2f9b778879d6ff9b06947fea45e5e0151034f4bafca9997d6ec9d5cd`; tested region is latitude -90 to -87.5 degrees. |
| Tile transport | Registration, conversion, corrected root and corrected control tile return HTTP 200. The control tile is a 103,320-byte `b3dm`; responses use `private, no-store`. |
| Run download | The deployed relay ZIP matches the canonical archive byte for byte, SHA-256 `27ea8e3448375df79bb05863f8ebc34cc513e7282ba3461214f767029b271d39`. Independent package verification passes. |
| Documentation | The actual Documentation button follows `/docs` to the published Mintlify library site; Python API and mobile navigation were inspected. |
| Presentation | No visible project-phase or draft labels; synthetic trajectories, assumed rates and captured-run scope remain explicit. |

The initial hosting failures were missing build-time credentials and a display
service, older synthetic defaults, an incompatible Python version declaration,
an incorrect ion URL restriction, and the missing native Expat dependency in the
serverless runtime. The Linux build now copies its Expat shared library and
license texts, records package provenance and checksums, and preloads the
verified library for Rasterio. Generated native binaries are not committed.

## Reproduction and regression checks

- `.venv/bin/pytest tests/engine -q`: 402 passed.
- `npm --prefix web test`: 83 passed.
- Browser suite with installed Chrome: 18 passed, including 390, 820 and 1440 px layouts, keyboard use, 200% text, cancellation, downloads and tile failure.
- Production Vercel builds passed with Linux native-library preparation.
- `mint validate` and `mint broken-links --check-anchors`: passed.
- Documentation Python examples and synthetic CLI planning, replay and export verification: passed.
- Archived integrated verification: 77 checks; physical release verification: 33 checks.

Initial local browser-suite attempts could not bind a server in the sandbox and
then found no downloaded Playwright executable. The passing run used the
installed Chrome executable with the test server authorized outside the sandbox:

```sh
SOMA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix web run test:browser
```

## Account and source scope

The deployment uses Vercel Hobby and Cesium Community for this educational
demonstration. The read-only ion token is restricted to asset 2684829 and the
production application origin; it expires on 15 December 2026. Browser-prefixed
Vite configuration is public. Server credentials remain write-only deployment
secrets. No token or restricted tile binary is stored in the repository or run
archives. Preview origins require their own explicit token authorization.

The [Cesium terms](https://cesium.com/legal/terms-of-service/) and
[content appendix](https://cesium.com/legal/cesium-global-3d-content-tos/) were
reviewed for graphical display and educational demonstration scope. Attribution
is retained and corrected objects are streamed without a dedicated persistent
cache. This records the implementation and source review, not vendor approval,
commercial licensing clearance, NASA endorsement or operational certification.
The Expat package license is copied into each generated function bundle.

Mintlify currently follows `web/hosted-planner-fix`, subdirectory `docs`. After
the pull request is merged, switch its production branch to `main` before
deleting the fix branch. The deployment configuration continues to use the
repository root.

## Presentation delivery gate

The existing scientific workspace direction was retained: ENERGY 1 / RHYTHM 1 /
MOTION 1. The saved antislop mode is `during`. This record was reviewed by the
primary agent, with automated checks and the actual production browser as
evidence.

- Hard gate PASS: no invented mission results, testimonials or statistics; engine warnings and fidelity remain visible. Real Moon rendering and its no-terrain fallback were exercised.
- Navigation PASS: Documentation opens the published Mintlify site; source and application links resolve. Unavailable Earth-orbit controls and project-phase labels were removed.
- Interaction PASS: scenario selection, planning, restore, retry, cancellation, exact-time selection, comparison and downloads are exercised by the 18 browser tests. Public direct, failed-direct and relay cases were also selected manually.
- Accessibility PASS: native controls, keyboard focus, responsive widths and 200% text checks pass. Documentation phone layout was visually inspected; code and wide tables scroll within their containers.
- Purpose gate PASS: the existing restrained palette distinguishes actions and warnings; panels group scenario, map, timeline and scientific evidence. No decorative graphics or unsupported feature claims were introduced.
- Liveliness PASS: the lunar terrain and allocated contact are the focal point; the existing SOMA wordmark and scientific typography remain consistent. Motion is limited to map interaction and hover feedback.
- Craftsmanship PASS: completed, loading, empty, failed-service and tile-failure states are covered; exact archives and scalar records remain available independently of rendering. Site and relay text annotations remain readable without moving their physical points.

Screenshots in [`hosted-evidence/`](hosted-evidence/) record the actual hosted
scene with source attribution, rather than an illustrative mockup.
