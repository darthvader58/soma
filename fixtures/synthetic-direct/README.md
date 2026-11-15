# Synthetic direct-contact capacity test

All scenario values and service windows are invented or explicitly assumed.
This is a Phase 1 contract fixture, not lunar geometry or a mission prediction.
`scenario.json` is standalone; `contacts.json` contains assumed source-transmit
windows; `expected.json` contains hand calculations, not an engine result.

100 MiB = 104,857,600 bytes = 838,860,800 bits. The only direct contact,
08:50:00 through 09:10:00 UTC on 14 November 2026, lasts 1,200 seconds.
At 256,000 assumed net payload bits/s it carries at most 307,200,000 bits
(38,400,000 bytes). The shortfall is 531,660,800 bits. No later direct
contact is supplied before the 10:05:00 deadline. Capacity alone therefore
rules out delivering the whole file through the supplied direct contact.
This is arithmetic evidence, not a solver's infeasibility proof.

The companion relay fixture retains identical location, data, deadline,
lander hardware and station profile. The lander has a finite 200 MiB buffer,
a nonzero 5 W base load, an explicit fixed panel, and a declared battery.
The synthetic station also has finite 200 MiB storage. Their shared
`SYNTHETIC_X_band` and `synthetic-direct-256k` mode declare compatibility;
ideal pointing and zero acquisition/teardown are explicit assumptions.
Electrical radio draw is not radiated RF power. Solar generation and energy
feasibility have not been calculated. The station is an invented educational
proxy, not a DSN resource or a service reservation.

Light time is `disabled_for_synthetic_test` solely to isolate arithmetic.
Physical propagation delay is additional when enabled. Receiver service,
radio occupancy, energy and final-byte delivery must then use arrival times.
The finite calendars in the scenario explicitly declare both endpoints'
service, rather than inferring continuous availability. No physical terrain,
ephemeris, link budget, or relay trajectory is provided or evaluated.

Source for the worked arithmetic: repository `plan/03-Communications-Relays-and-Scheduling.md`.
