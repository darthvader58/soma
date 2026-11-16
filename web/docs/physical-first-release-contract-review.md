# Developer B physical preset review

Review scope: the frozen native schemas and the two engine-authored scenarios in
`fixtures/physical-south-pole/`. No native schema changes were needed. The copies
under `web/fixtures/physical-south-pole/` are identical to the engine inputs and
are available only with the live planning service. Offline mode retains the two
captured synthetic fixtures and never fabricates physical results.

The physical scenarios retain `terrain_ephemeris`, `MOON_ME_DE421`, separate
antenna/panel heights, qualified UTC, explicit MiB, finite storage and battery
limits, compatible terminal references, and finite service windows. They declare
published terrain/DE421 geometry, assumed hardware/rates/ideal pointing/service,
educational geographic station proxies, and a
`synthetic_two_body_lunar_preset` with reference `soma-polar-200km-v1`.
The interface displays these classes and the complete source descriptions.
A physical geometry result remains an assumed-rate simulation.

The engine resolves the input elevation against its numerical terrain. The
original scenario, including its declared elevation, retains its hash. After a
matching completion, the interface reads `environment.analysis_point` for the
resolved analysis-location text and exported `surface_points` for the map.
Picking the displayed mesh never changes either equipment height or the scenario.

The November 24 and November 30 presets hold site, 16 MiB task, hardware,
80 Wh initial battery, route families and network design constant. Selecting a
different full preset explicitly replaces the operating window, deadline,
finite service calendars and synthetic trajectory coverage. Both presets declare
a six-hour mission-age deadline. Manual time-field edits retain the current
absolute deadline and calendars. The comparison shows actual UTC deadline,
horizon and service changes instead of hiding them or claiming site/date alone
explains an outcome.

Native scientific `states` retain their origin, frame, epoch, time scale, units
and provenance. Additional `renderer_states` use the engine-authored corrected
renderer frame, `source_frame`, `transform_ref=renderer-registration.json` and
per-record `transform_epoch_utc`. The browser only draws exact stored relay
samples, behind the existing regional registration gate. Missing or intervening
samples remove the relay marker and link. It performs no propagation or frame
transformation. Dashed links represent available source contacts; solid links
represent active source allocations. Both endpoints must be supplied. No Earth
station position or path is invented when an endpoint is absent.

The timeline offers exact stored sample timestamps in addition to the existing
slider. All contacts, allocations, receiver occupancy, byte availability, energy,
buffers, summaries and downloads still come from the same immutable engine run.
No result outcome was selected or edited to fit a demo narrative.

Validation: `npm test` includes identical-copy/native-schema checks, fixed-task
date-preset checks, provenance classes, task-control comparisons, exact renderer
sample selection and overlay cleanup. Existing fixture browser checks cover
stale jobs, cancellation, unknown data, keyboard/mobile layouts and unchanged
downloads. Live physical result and map walkthrough evidence is recorded
separately after numerical data preparation completes.
