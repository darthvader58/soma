# Phase 5 live interface verification

The numerical browser/service integration and scoped corrected-mesh registration
gate pass. The tested application region is latitude -90 to -87.5 degrees.
Matching completed displays may show the declared analysis point; the
contact-only fixture supplies no relay ephemeris, so no trajectory is invented.
Phase 6 has not started.

Current owner verification: 351 engine tests, 71 web unit tests and production
build pass. The public registered diagnostic measured all 1,764 requested probes
with zero page or console errors. The owner also inspected the live registered
scene in Aside. Desktop/mobile visual checks and exported replay are recorded
by the owner with the final Phase 5 evidence. Historical runs below retain their
original counts and map limitations.

The owner reviewed both developer implementations and ran the integrated
workflow. This is engineering evidence, not a human scientific approval or
accessibility certification. The visual design remains a **draft without
direction**, ENERGY 1 / RHYTHM 1 / MOTION 1, using [design.md](design.md).

Final combined checks: **299 engine tests, 58 Node tests, four live browser
checks, seventeen fixture browser checks and production build pass**. The
downloaded live relay run independently replays with zero errors and 104,857,600
unique delivered bytes. No engine tests were skipped.

## Live service evidence

Four real Chromium checks pass through a Vite proxy to the actual spawned-job
FastAPI service. No fake planning response is used:

- The 100 MiB direct request proves capacity failure. The relay request delivers
  104,857,600 unique bytes with successful replay and explicit assumed-rate
  fidelity. The time-limited capture is a feasible incumbent, not a proven optimum.
- Downloaded ZIP bytes equal the completed service export. Every member hash,
  native result and allocation CSV source/RX/availability timestamp matches.
- Moving the timeline to an exact stored epoch shows the same battery value
  and sends no POST. Missing spacecraft states and unsupported sample times
  remain Unknown. No orbit, energy integration or routing is performed in JS.
- A 16-byte volume edit creates a different scenario hash and is genuinely
  rescheduled. Changing the site outside the curated model returns unknown.
- Canceling a real running job yields canceled with no result/export. Editing
  during a job cancels it; only the new scenario's result can appear.

The owner inspected [desktop](screenshots/phase-5/live-relay.png) and
[mobile](screenshots/phase-5/live-mobile.png) result screenshots. Both preserve
the outcome, solver and fidelity labels with the optional map unavailable.
The selected schedule, complete ZIP and structured explanation remain usable.

The existing seventeen fixture browser checks also pass after updating the
controlled renderer stub for the new registration API and its changed diagnostic
label. Fifty-eight Node tests pass, including display version/hash/result
matching, exact epochs, stale artifact cancellation and renderer gate invalidation.

```sh
npm test
npm run build
npm run test:live
npm run test:browser
```

The live suite starts isolated local servers on ports 8065 and 5175. The fixture
suite explicitly selects offline mode and clears the ion token. Set
`SOMA_BROWSER_EXECUTABLE` when using an existing compatible Chromium installation.
Source guidance was checked against official Vite proxy and Playwright multiple
web-server documentation through Context7.

The first live-suite attempt was interrupted by a development reload while the
owner edited source; the stable full run passed all four cases. The first
fixture run identified a missing export in its controlled renderer stub and an
old label expectation; both focused reruns pass. No unresolved runtime failure
is being presented as a passing scientific check. Service process/queue/event
resources now close on terminal job states; the final live shutdown emits no
multiprocessing semaphore leak warning.

## Actual Moon access and registration

At the user's request, Aside used the existing signed-in GitHub identity to
access Cesium ion. Moon asset 2684829 was enabled, and a dedicated local token
was created with only `assets:read`, that asset, local development/preview URLs,
and a December 15, 2026 expiration. It is stored only in ignored
`web/.env.local` with mode 0600; the temporary transfer copy was removed. Token
values and credentialed URLs are absent from source, reports and run exports.
The owner inspected actual Moon terrain loading in Aside and performed a live
direct request in that browser. This confirms access and the numerical flow,
not mission feasibility.

The engine's [map-alignment report](../../soma/docs/phase-5/map-alignment.md)
and v0.2 certificate record the engine-corrected mesh, conversion checksum,
identity frame handoff and four source-selected terrain features. Their
resolution-adjusted residuals pass the preregistered 10 m tolerance. The 3.54 m
grid-resolution allowance is not a continuous-peak localization bound. Four
features and 48 height controls at detailed 5.21 m mesh resolution establish a
relative display test, without an absolute geolocation or all-LOD guarantee.
Runtime root and control-tile fingerprints are sampled snapshot checks rather
than a checksum pin for every regional tile. The current contact-only relay has
no trajectory, so there is no stored spacecraft position to render.

## UI delivery gate

The owner reapplied the full gate to the scoped interface change. The scoped
registration, missing-trajectory and display-only elevation limits are explicit
in the product. The existing measured palette and
reasons remain in the earlier verification/design records; no colors were added.

R-01 PASS: Teal remains the primary action; no gradients or glow added.
R-02 PASS: Authored UI text has no em dash.
R-03 PASS: Existing 390/820/1440-pixel and enlarged-text checks pass; live mobile has no page overflow.
R-04 PASS: No decorative icons added.
R-05 PASS: Scenario, timeline, outcome and evidence follow the actual task.
R-06 PASS: Existing system typography and tabular numbers retained.
R-07 PASS: No decorative grid.
R-08 PASS: No decorative action arrows.
R-09 PASS: Mode, fidelity and registration labels report actual state.
R-10 PASS: No glass effects.
R-11 PASS: Existing restrained control/panel corners retained.
R-12 PASS: No decorative shadows.
R-13 PASS: No glow.
R-14 PASS: No promotional cards or filler.
R-15 PASS: Plan delivery, cancel, retry and downloads name their actions.
R-16 PASS: Copy describes the calculation without marketing claims.
R-17 PASS: Values come from the supplied scenario and matched engine artifacts.
R-18 PASS: No testimonials.
R-19 PASS: No automatic/template motion.
R-20 PASS: Precise frame/time/height and job labels express the planning task.
R-21 PASS: Existing light reading workspace retained for dense records.
R-22 PASS: No generic illustration.
R-23 PASS: Moon source and neutral-lighting limits remain explicit; no fabricated asset.
R-24 PASS: Existing challenge and documentation links have real targets.
R-25 PASS: No new text/background color pair; prior measured contrast retained.
R-26 PASS: Live planning, edit, cancel, retry, time and download controls have tested behavior.
R-27 PASS: Empty, running, error, canceled, complete and blocked-map states are explicit.
R-28 PASS: No FAQ filler.
R-29 PASS: Existing neutral palette/teal accent retained.
R-30 PASS: No product-clone layout introduced.
R-31 PASS: Separate display status explains missing samples without hiding the schedule.
R-32 PASS: Native controls, focus, disclosures and skip-link tests remain green.
R-33 PASS: Maintained source changes; controlled test interception is labelled as test data.
R-34 PASS: No theme toggle or alternate broken theme introduced.
R-35 PASS: Build, real live requests and fixture control checks run successfully.
R-36 PASS: No certified, booked-service or optimality claim beyond the engine result.
R-37 PASS: Draft status and low-energy dials remain visible/documented.
R-38 PASS: Live results are calculated; failed requests cannot reuse captured success.
R-39 PASS: Named native controls, focus and reduced-motion rules retained.
R-40 PASS: No new media/blocking scripts; optional Cesium retains its lazy import and notices.

Liveliness PASS: The established Design Read and dials remain consistent. Plan
delivery is the focal action; spacing separates inputs, numerical outcome and
evidence. Teal is restrained, and exact scientific labels repeat the identity.

C-1 PASS: Added labels expose real job/display evidence.
C-2 PASS: Controls have exercised actions.
C-3 PASS: No template-only section added.
C-4 PASS: Missing map, stale job, cancel, keyboard and responsive cases remain usable.
C-5 PASS: No fabricated outcome, statistic or endorsement.

Release boundary: numerical integration and the scoped corrected-mesh
registration are reviewable. Stored relay ephemeris display, merged integration
and Phase 6 acceptance are not claimed. The existing ENERGY 1 / RHYTHM 1 /
MOTION 1 layout, palette, controls and focus behavior are unchanged; the new
inset sentence reports stored directions without claiming a blocked scene.
