# Fixed-dark SOMA workbench verification

Verified locally on 17 November 2026. The user requested a fixed dark interface and the full name **Selenographic Observation and Mission Atlas**. That instruction overrides the earlier two-appearance design and the Anti-slop theme-toggle requirement.

The header retains the full name at every tested width. The appearance control and theme storage logic are removed. Existing stored light preferences do not change the dark palette.

## Why a completed analysis could look unchanged

- The same request evaluates the same sites, times and source files. It can legitimately produce the same scene.
- Completion resets to the first supplied epoch and pauses playback. Spacecraft movement requires Play, a stored-sample step or the UTC slider.
- Inspecting an unchecked catalog location did not add it to the study. Its inspector and plot therefore had no calculated sample. It now has an explicit **Include this site and run** action, subject to the existing eight-site bound.
- Evaluated markers used raw reference-sphere coordinates, which could lie below the rendered terrain. They also lacked a selectable site identifier and label. Custom sites had no catalog position before calculation, so the existing lifted catalog markers did not help them.
- Direction drawing incorrectly fell back to the first calculated site when the inspected context site had no result. That fallback is removed. An uncalculated inspected location now shows no direction vectors.

## Result handoff and marker behavior

Completion reports evaluated site and epoch counts, identifies identical-input reruns and explains the paused playback. A calculated location receives the inspector when the previous context location is outside the result. The initial study keeps the global Moon view. Explicit changes to the site set or coordinates fit the calculated selected site and update the camera's pressed state. A repeated Follow request remains consistent with its pressed state when spacecraft remain available.

Evaluated sites use hollow labeled rings, while catalog context uses solid dots. Evaluated rings use the existing **10 km radial display lift** for legibility, have a site identifier for picking and honor the label layer. This offset never changes the request, equipment heights, result positions or exported JSON. It does not establish terrain alignment or terrain-clear access. Camera fitting is presentation only; reduced motion uses an immediate site view.

Moon lighting remains neutral. The geometry slice still does not calculate terrain visibility, terrain shadows, solar-disk visibility, power or usable communications. A direction above the reference-sphere horizontal is not evidence that surrounding terrain leaves it clear. The first-visible-tile handoff is unchanged.

## Verification evidence

- New viewer checks and existing first-visible-content checks: **5 passed**. They verify a custom result produces a pickable labeled lifted ring, preserves the exact engine arrays, honors label visibility and does not borrow another site's directions.
- Root's complete web unit suite: **99 passed**.
- Root's complete browser suite: **38 passed**, including fixed dark with an old stored light preference; full-name visibility at 320, 390, 820, 1024 and 1440 pixels; identical-input reruns; explicit context inclusion; stale/cancel/error states; keyboard access; downloads and camera consistency.
- Root's scientific suite: **97 passed**. No engine, schema or scientific input file was changed by this interface work.
- Real DE421/LRO browser flow: **1 passed in 5.6 seconds**. A new four-site study retained its exact downloaded Python result and changing spacecraft samples; a rendered custom-site ring was found from its visible pixels and clicked to restore its inspector. The first pixel locator counted the amber camera toolbar as well as the ring; its final central-canvas locator clicks an actual ring pixel.
- Production build passed. No new visual asset, physics implementation, source kernel or scientific assumption was introduced.
- Final pressed-camera hover assertion and identical-rerun check: **1 passed in 1.7 seconds**. Production build after that CSS correction passed in **566 ms**; whitespace checks passed.

Dark palette contrast was computed with the WCAG luminance formula: text/surface **11.44:1**, muted text/surface **6.86:1**, control border/surface **4.45:1**, focus/surface **7.37:1**, and primary button text/fill **7.04:1**.

Screenshots from that real-source flow are `web/test-results-research-live/dark-workbench-desktop.png`, `web/test-results-research-live/dark-workbench-mobile.png` and `web/test-results-research-live/custom-evaluated-marker.png`. They use the actual Cesium reference-sphere fallback without a scoped ion token; they do not claim detailed tiles were loaded. Visual review also corrected the pressed camera button's hover palette so its dark text keeps an amber background.

## Anti-slop delivery gate

- Hard gate PASS: fixed dark follows the user's explicit instruction; the full name and controls reflow without clipping in the browser suite; no invented metrics, inactive controls, fake motion or scientific shadows were added.
- Purpose gate PASS: dark slate separates controls from the scene; amber identifies selection and the primary action. The completion text names a real result and the marker shapes distinguish evaluated and context locations.
- Liveliness PASS: ENERGY 2 / RHYTHM 2 / MOTION 2; the Moon remains the focal view, with deliberate catalog, inspector and timeline roles. Motion remains user initiated, with reduced-motion camera behavior.
- Craftsmanship PASS: the suite covers keyboard, mobile, empty/error/stale/canceled states and exact result exports. Calculations remain Python-authored; display offsets stay outside scientific data.
