# Fresh hosted delivery verification

Recorded November 18, 2026. All dates in this evidence describe actual verification. Git metadata requested by the repository owner is separate.

## Scientific execution

The Linux Vercel preview `AXkxtJTCwVQgH9yVRAJnnS3p2Qrt`, source commit `63ff67f`, prepared and verified 11 delivery source files totaling 133,092,198 bytes. Its CBC integer-program smoke test passed. Fresh browser requests used `physical-lola-de421-v2`, published numerical terrain and matched SPICE inputs, with explicit assumed payload rates, ideal pointing, finite educational station service and an optional synthetic two-body lunar relay.

The complete current engine suite passed: **498 tests**. Existing upstream NumPy/SpiceyPy deprecation warnings are reported by pytest. Web verification passed **106 unit tests** and the fresh-service browser case, including automatic first-transfer focus, 390 px layout, keyboard interaction, edited-profile synchronization and original ZIP checksum verification. Mintlify validation and broken-link/anchor checks passed. The UI gate is in `live-delivery-ui-gate.md`.

## Controlled deployed cases

The task is 16 MiB, at the same regional site, with the same hardware, initial battery, six-hour 08:00–14:00 UTC interval and absolute last-byte deadline rule. The date comparison moves the task epochs and explicitly assumed service together; it does not silently claim a real station booking. The relay comparison changes the permitted route family.

| Case | Actual outcome | Independent export checks |
| --- | --- | --- |
| November 24, direct only | 16,777,216 bytes delivered; feasible incumbent, optimality unproven | 72 passed |
| November 24, both families enabled | Direct selected; 16,777,216 bytes delivered; feasible incumbent | 72 passed |
| November 30, direct only | No direct contact capacity; proven infeasible discretized model | 64 passed |
| November 30, relay enabled | Two hops with relay storage and later Earth arrival; feasible incumbent | 72 passed |

`live-delivery-preview-evidence.json` records exact request and ZIP hashes, actual arrival epochs, allocation intervals and storage reservations. The independent verifier checks checksums, schemas, byte conservation, capacity, causality, endpoint occupancy, finite storage, energy and deadline without running the optimizer. An infeasible export passes integrity/consistency checks without inventing a successful schedule.

For the November 30 relay run, the first source transmission begins at 09:33:30 UTC, the later downlink begins at 10:38:00 UTC, and the final byte reaches the modeled Earth station at 10:39:01.245105 UTC. Storage reservation starts with incoming bytes; it must not be mistaken for whole-chunk availability. The native replay checks that forwarding waits for complete byte availability.

Exact incumbent schedules can change with solver budget and platform. These are model results under declared assumptions, not operational mission predictions or access to LRO, a lunar relay or a DSN antenna.

## Data and runtime corrections

The hosted v2 dataset explicitly restores the complete near-terrain window from its published parent product. The original v1 missing footprint and archived results remain unchanged. Canonical raster storage produces identical cross-platform file hashes while preserving decoded samples. `docs/science/terrain-revision.mdx` documents this revision and quality caveats. Historical source compatibility is separately bound in `data/physical-source-compatibility.manifest.json`; refreshed source checksums do not extend older scientific reviews to the new endpoint.

The macOS crash shown by the user was traced to our local server's fork-before-exec child startup. Darwin workers now use direct `posix_spawn` with a new session; Linux retains its bounded process worker. Verification included 24 concurrent threaded launches with the old Popen path forbidden, eight real geometry HTTP requests without new crash reports, and three geometry/delivery TestClient request pairs. The unused local API and Vite servers were stopped after verification.

## Capability boundary

The public application now connects the implemented native delivery planner. The expanded Python reference covers actual geometry/time, trajectories, terrain, illumination/power, communications, scheduling, validation and export functions. It does not claim TATC parity: instrument footprints, coverage/revisit/coincidence, constellation optimization and other unbuilt workflows remain explicitly unavailable. Global Geometry remains a separate reference-sphere study; the bounded regional Data delivery provider evaluates numerical terrain, sunlight, energy and contacts.
