# Research workbench interface

The default `/` route is a live Python geometry client. The former delivery demonstration is a separate `/?mode=archive` route. The archive is loaded as a separate JavaScript chunk and is never a failed-analysis fallback.

## Design read

Direction: scientific mission workbench, ENERGY 1 / RHYTHM 2 / MOTION 2. A neutral charcoal scene and quiet panels keep the lunar geography primary. Amber identifies selection and the run action. The system reading face uses tabular numerals for changing UTC, angles and ranges; it avoids an ornamental terminal aesthetic. The object tree is for selecting study inputs, the inspector is for exact input/source/state details, and the bottom dock coordinates time and comparable numerical outputs. Playback has a pause control and stops at coverage boundaries. Camera motion honors reduced-motion preference. No external visual asset was created.

## Scientific contract review

Reviewed `schemas/study.schema.json` and `schemas/study-result.schema.json` against `soma/docs/research/contract-v1.md`. The interface consumes these schemas with AJV. No blocking schema issue was found. Longitude 180 degrees is explicitly normalized to -180 before hashing. The pair budget includes the final endpoint even when its interval is shorter than the requested step.

The browser does not calculate ephemerides, terrain, illumination fraction, power, contacts or routing. Catalog coordinates are supplied by Python. Scene placement uses the existing registered Moon conversion, with its regional certificate retained. Global catalog markers and evaluated reference-sphere points are context, not globally certified terrain alignment. Sun/Earth lines use returned vectors and a clearly labeled schematic display length. They are not communications links. LRO is an archived reconstructed mission trajectory, not a relay service.

Every scientific readout uses a stored source epoch. The spacecraft display uses Cesium's linear sampled-position interpolation, explicitly bounded by the first/last supplied states. No orbital propagation or extrapolation is performed. Native Moon-fixed position and velocity can be inspected separately from visual playback.

## Action inventory

- Search filters sourced catalog rows; inspecting a row selects its numerical/source inspector.
- Site checkboxes select 1 to 8 sites; custom site adds editable global coordinates and separate panel/antenna heights.
- UTC bounds and sampling edit the request, invalidate exports, and visibly mark displayed previous results stale.
- Run submits an immutable detached request to Python. The response must pass the frozen schema and match the RFC8785 request hash.
- Cancellation follows service capabilities. A Vercel synchronous request says "Stop waiting" and explicitly explains that server work may continue. Persistent local jobs use server cancellation and immutable package downloads when supported.
- Global/polar/site/follow camera controls affect presentation only. Follow requires returned spacecraft states.
- Layer toggles change selected labels, stored paths and supplied direction schematics.
- Play/pause, previous/next sample, speed and scrub share a UTC cursor. The chart and inspector remain available after tile failure.
- The ephemeris interval action picks a covered six-hour interval, explicitly includes the spacecraft and submits a calculation.
- Save alternative retains a detached calculated result; study/result JSON exports preserve current inputs or exact validated scientific objects. No ZIP is reconstructed in JavaScript.
- Methods & sources opens a collapsed disclosure with the complete supplied study hash, provider, frame, aberration convention, kernel names/checksums, official NASA source links, limitations and assumptions. Spacecraft source limitations are also shown. Its content has a keyboard-focusable scroll region bounded to 180 px, so long provenance does not replace the lunar scene or time controls. Non-official or unsafe source URLs remain plain text.

## Verification

`npm test` covers request budgets, arbitrary custom input submission, hash rejection, sync cancellation, persistent job negotiation/orphan cleanup and stored-epoch semantics, along with existing delivery and registration tests.

`SOMA_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm run test:browser` covers archive preservation and the new workbench. New tests use explicitly test-only service values; none are shipped as fallback science. They exercise multi-site submission, custom coordinates/heights, stale labels, JSON export, shared time, camera follow, play/pause, source links, unavailable service, cancellation and narrow layout. The real-Cesium test verifies the labeled sphere fallback and numerical result retention. Production Moon tiles and real native LRO motion additionally require the deployment's scoped ion token, source data and Python endpoint; the test-only mock service is not evidence of physical accuracy.

Performance targets in the expansion plan remain targets. No field Web Vitals, network performance or global terrain accuracy is claimed by this interface report.

Final local evidence on 16 November 2026: 94 unit tests passed, all 26 archive/workbench browser tests passed, and `npm run build` passed. `npm run test:research` passed against the prepared real DE421 kernel set and public reconstructed LRO SPK. That browser run loaded all 15 catalog entries, calculated the April 1 six-hour interval, inspected changing native LRO states, played/paused the shared clock, and calculated a new custom location at 21.1827° N, 68.2714° E with 1.7 m panel height. The resulting four-site study had a changed hash and exact downloadable result. Both Python/Vite test servers shut down afterward.

[Real-source browser evidence](research-evidence/real-sources-reference-sphere.png) shows the labeled reference-sphere fallback, because the isolated test intentionally has no ion token. It is not a screenshot of globally registered terrain. Production Moon tiles remain a separate deployment check.

Contrast was computed with the skill's WCAG checker: primary text/panel 12.19:1, secondary text/panel 7.00:1, run-button text/accent 8.84:1. The final control edge is 3.22:1 against its button fill and 3.78:1 against the panel. Focus uses the selection accent. Mobile tests check 390 px overflow and keyboard focus; a physical-device virtual keyboard was not tested. Saved alternatives currently retain immutable result objects and expose input metadata; a richer comparison of saved run results is not claimed.

Methods & sources verification: the final full browser suite passed 27/27 tests in 17.3 seconds, including every supplied limitation and assumption, complete hashes, kernel names, safe official links, blocked unsafe links, keyboard expansion/collapse, keyboard scrolling inside the 180 px region and no horizontal overflow at 390 px. The final 94 unit tests and production build also passed. The test server stopped afterward. Only the workbench module, its research browser test and this report changed for this transparency fix.

Display follow-up: the reference sphere now remains visible after tileset metadata arrives and is hidden only after initial tile loading completes with visible content. The loading caption identifies the sphere throughout that interval. Global and polar cameras fit the display body to the current vertical field of view and aspect ratio with a margin; a ResizeObserver refits those views after the map container changes size. This is camera presentation only. The full browser suite passed 28/28 tests in 21.9 seconds, including real Cesium pixel-bound checks at 1440 by 900, after reducing map height to 260 px, and in polar view. All 94 unit tests and the production build passed. Live ion streaming latency and the production handoff remain deployment checks; the local tests intentionally use the tokenless sphere fallback.
