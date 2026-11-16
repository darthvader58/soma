# Hackathon demonstration verification

The five-case presentation uses one hypothetical 16 MiB lunar south-pole mission, a six-hour deadline rule, published LOLA terrain and DE421 geometry. Hardware, net rates, ideal pointing, station service and the synthetic two-body lunar relay remain declared assumptions. This record supplements the existing scientific evidence; it does not extend its numerical coverage or claim a flown operation.

Public application: <https://soma-atlas-two.vercel.app/?case=direct-ready>

Published narration and shot list: <https://soma-ce3178ca.mintlify.site/guides/hackathon-demo>

Mission workflow and narration source: `77c186a`, branch `web/hackathon-mission-cases`. The subsequent rendering compatibility change refreshes frames continuously without advancing the selected scientific time.

## Computed cases checked in the public interface

| Case | Native outcome and evidence |
| --- | --- |
| `direct-ready` | Feasible under assumptions; 16,777,216 bytes arrive at `2026-11-24T08:10:01.201519Z`; proven optimum in the declared discretized model |
| `direct-later` | Infeasible in model; zero known usable direct capacity for the 134,217,728-bit task |
| `relay-later` | Feasible incumbent; 16,777,216 bytes arrive at `2026-11-30T09:37:01.238933Z`; independent replay passes |
| `battery-low` | Unknown/unresolved with incomplete contact coverage; original baseline replay fails only with `energy_reserve` errors |
| `service-off` | Unknown/unresolved with incomplete contact coverage; original baseline replay fails only with `service_unavailable` errors |

Case buttons and `?case=` URLs restore the entire captured scenario. Scientific inputs begin read-only; local editing prepares JSON for the full Python engine. Captured output cannot stand in for a newly edited scenario. Native outcomes and separately hash-bound controlled explanations remain distinct.

The exact relay focus selects the stored `09:33:30Z` renderer state and the broad view. At `09:34:00Z`, the antenna diagnostic supplies Earth/station/relay directions and the panel diagnostic supplies the Sun direction and zero modeled generation. The service variant explicitly identifies retained baseline service labels in its geometry/power diagnostic.

## Verification

- Full engine suite: `406 passed` using `.venv/bin/pytest -q tests/engine`.
- Final web unit suite: `87 passed` using `npm --prefix web test`.
- Final browser suite, after the rendering change: `20 passed`; focused camera checks also passed during development.
- Production frontend build passed. Mintlify validation and internal link/anchor checks passed.
- Fixture/source bindings passed their four targeted tests after the final camera and guide changes. The physical completion checker passed its 33 checks.
- Fresh synthetic relay calculation delivered 104,857,600 bytes and passed independent replay. Its synthetic character remains separate from the five terrain-backed presentation cases.
- Both operational variants were freshly recomputed from the archived physical relay analysis and independently verified; four new engine tests cover exact inputs, unknown outcomes, export hashes and constraint-specific counterfactual rejection.

The relay ZIP downloaded through the browser's actual download button matched `fixtures/physical-south-pole/relay-later/run.zip` byte for byte. Its SHA-256 was `27ea8e3448375df79bb05863f8ebc34cc513e7282ba3461214f767029b271d39`; export verification and independent replay passed.

The camera controls change the view only. The broad Moon view is the default and the recording view. Fine site tiles stream on demand and can take longer on a cold connection; they are not required for the narrated sequence. Cesium attribution stays visible. Neither rendered shadows nor visual quality determine sunlight, contact feasibility or delivery success.

The narration contains 931 spoken words across nine timed segments, with a planned duration of 7 minutes 10 seconds. The guide gives exact actions for every segment, a mission evidence table, direct case links and rehearsal instructions.

## Final production rendering check

The final rendering source `0afe38a` was promoted through [Vercel deployment 3GVhNeVH6uSyh5jVQ4Nfs6j8yhBQ](https://vercel.com/rajayshashwatgmailcoms-projects/soma-atlas/3GVhNeVH6uSyh5jVQ4Nfs6j8yhBQ). A fresh production navigation, the exact relay focus button, and normal tile loading produced the [verified Moon and allocated relay link](hackathon-demo-evidence/relay-production.png) without mouse-wheel interaction. The sample stayed at `2026-11-30T09:33:30Z`. Cold terrain loading took about one minute in this check, so the recording instructions require preloading cases before starting the video. All 27 completed Moon requests in that check returned HTTP 200.
