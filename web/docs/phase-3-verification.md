# Developer B Phase 3 verification

This phase adds stored-data scientific displays and two saved-result comparison.
The interface remains a **draft without direction**, ENERGY 1 / RHYTHM 1 /
MOTION 1. It uses the existing layout and colors from [design.md](design.md).
Python remains the scientific authority; no frozen schema fields were changed.

Three bounded GPT-6.1 Sol agents worked on solar/power, contacts and display
components. The owner reviewed their code, finished the contact budget and
integration, and ran the combined checks. This report is owner verification, not an independent human
Developer B approval or a merge.

Verified: **39 Node tests, 14 Chromium browser tests, production build**, and
**223 engine regression tests** pass. A focused browser rerun confirms the final
plot label layout. Console/page-error collections were empty in those runs.

## Contract and interaction checks

| Check | Evidence |
|---|---|
| Scientific data authority | `sync:science` invokes Python and captures version 0.3.0 environment artifacts; it verifies scenario hashes. Browser code reads stored values. |
| Synthetic/real separation | The selector distinguishes scenario-matched invented inputs from the separate recorded real LOLA site. The context gives coordinates, frame, both heights and scenario hash. Neither changes the delivery result. |
| Height and frame | Panel and antenna profiles have a named selector, source heights, frame/datum, source hashes and cache identity. |
| Horizon and directions | SVG charts plot supplied samples and endpoint azimuth/elevation. Unknown bands break the line; they are never filled with a clear horizon. Earth center and configured station endpoints have distinct labels. |
| Solar and electrical output | Exact stored fractions, bounds, method, generation and battery samples are shown. Unsampled selected times show Unknown; the browser does not interpolate scientific values. |
| Contact interpretation | Usable contacts are explicitly not selected transmissions. Rejected/unknown candidate intervals retain reasons; missing reasons display Unknown. A blocked fixture interval cannot appear in the contact table. |
| Time control | Scrubbing changes selected data and map clock without planning. The job/result stay unchanged. |
| Input changes | Edited scenarios hide unmatched synthetic graphics and disable diagnostic export. The independently labelled recorded case remains inspectable as a reference. |
| Diagnostic export | Downloaded bytes match the generated engine artifact exactly. No missing series or CSV is reconstructed. |
| Comparison | A/B start with captured direct/relay results. Save actions copy the exact scenario/result, and later edits cannot mutate them. Restore returns the captured pair. |
| Controlled task | Volume, absolute deadline, hardware, initial battery and network differences are named. Changed task controls prevent attributing an outcome to site/date alone. |
| Missing summary metrics | The frozen result supplies no route/wait/communications-energy/minimum-reserve summaries. These remain Unknown; speculative fields are ignored. No site ranking is computed. |
| Map failure | All scientific/text content works in the tested missing-token fallback. Registered Moon overlays stay blocked. |

The interface tests cover missing values, zero versus unknown, plot gaps, exact
height/time selection, blocked/missing reasons, ignored fields and changed
deadline/battery controls. Real Chromium checks cover the complete interaction,
raw downloads, saved snapshots, console/page errors, keyboard use and layout at
390/820/1440 pixels including 200 percent text resizing. The production build
also passes. The established browser fallback uses installed Chromium because
Aside's local interactions were unreliable in the earlier verification.

The owner inspected the saved [real-data inset](screenshots/phase-3/real-science.png),
[synthetic inset](screenshots/phase-3/synthetic-science.png), and
[mobile inset](screenshots/phase-3/mobile-science.png). Earth and station labels
are separated with display-only leader lines; their scientific coordinates are
unchanged. New plot/text/marker/leader colors have contrast ratios 10.75:1,
6.51:1, 8.04:1 and 5.10:1 against their plot background.

Reproduce from `web/`:

```sh
npm run sync:science
npm test
npm run build
npm run test:browser
```

## Delivery gate

The owner reapplied the [R-01 through R-40 gate](verification.md#delivery-gate).
All pass for this scoped draft. No decorative assets, gradients, shadows, icons,
automatic animation, invented success or promotional claims were added. Scientific
tables and chart samples are the content; the result remains above diagnostics.
New controls are native, visibly labelled, functional and keyboard accessible.
Height selection retains focus. Display status and blocked reasons use text.
Unknown, edited, recorded-reference and unavailable-result states are explicit.
Layouts preserve the existing structural spacing, reading contrast and restrained
accent. Wide scientific tables scroll within their own region instead of widening
the page. Mobile charts have larger SVG labels and equivalent numerical tables.

Liveliness passes for the declared low-motion dials: Plan delivery remains the
focal action, numbered sections follow the actual task, and the repeated precise
labels distinguish SOMA from a generic dashboard. Craftsmanship passes: every
added section presents supplied scientific evidence or task-control differences,
survives map absence and avoids replacing missing data with a fabricated value.

Source review finds no browser Friis relation, battery integrator, horizon ray
caster, SPICE call, orbit propagator or route solver. Chart projection and table
formatting are display operations.

## Limits

This is a fixture-backed Phase 3 display, not a live service integration. Real
LOLA horizon gaps still cause unknown power. Base-load battery replay is not a
selected transmission schedule. Route and energy comparison remain Unknown until
the scheduler/export contract supplies them. No published-site illumination
reproduction, operational link, booked service, thermal survival or best-site
claim is made. Token-backed Moon streaming/picking and numerical registration
remain unverified and do not enable aligned scientific overlays.
