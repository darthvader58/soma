# Physical mission constraint demonstrations

These are controlled changes to the **same hypothetical 16 MiB south-pole mission** as `fixtures/physical-south-pole/relay-later/run.zip`: November 30, 2026, 08:00–14:00 UTC, with the same site, DE421 frame and ephemerides, LOLA terrain, state histories, radio profiles, contacts, generation, and scheduler settings. This is a planned-mission study, not a flown operation. The lunar relay is a synthetic two-body preset; rates, hardware, ideal pointing, and station service remain assumptions.

Reproduce from the repository root:

```sh
.venv/bin/python scripts/build-demo-constraints.py
.venv/bin/python -m soma.verification.exports fixtures/demo-constraints/battery-low/run.zip
.venv/bin/python -m soma.verification.exports fixtures/demo-constraints/service-off/run.zip
.venv/bin/pytest tests/engine/test_demo_constraints.py -q
```

No data download is needed to recompute the schedule from these archived numerical inputs. Recomputing the underlying terrain/ephemeris analysis is a separate physical reproduction workflow. The generator verifies and independently replays the original physical baseline before changing one control. It preserves numerical analysis and the original scheduler settings: 60-second bins, one 16,777,216-byte chunk, and a 15-second solver limit. Only scenario-hash bindings in the analysis and environment metadata are refreshed to match each changed scenario.

| Case ID | Only mission control changed | Native outcome | Original baseline schedule fails replay with |
| --- | --- | --- | --- |
| `battery-low` | Initial energy 80 → 11 Wh; reserve remains 10 Wh | `unknown`, solver `unresolved` | `energy_reserve` |
| `service-off` | Hypothetical lunar relay service windows become empty | `unknown`, solver `unresolved` | `service_unavailable` |

The source physical analysis explicitly has **incomplete contact coverage**. The engine can release a feasible incumbent on known contacts, as it did for the original relay case. Failure to deliver on known contacts cannot establish infeasibility across unknown opportunities. These cases therefore retain the native conservative `unknown` result; they must not be advertised as proven full-network infeasible.

## Battery interpretation

The six-hour November 30 physical analysis has zero modeled generation. The declared 5 W base load alone requires 30 Wh of delivered electrical energy, or approximately 33.333333 Wh removed from storage at 0.9 discharge efficiency. Initial energy of 11 Wh leaves only 1 Wh above the 10 Wh reserve, so even base demand exceeds that margin before communications. Independent replay of the formerly feasible baseline produces only `energy_reserve` violations. The native engine still conservatively reports unknown because its delivery-status logic preserves incomplete contact coverage.

No schedule or energy history is selected for this unresolved result. Null completion and minimum-energy fields remain unknown. The separate rejected-baseline replay is evidence about that counterfactual schedule, not a chosen replacement.

## Service interpretation

The same hypothetical relay has no allocated service windows. The baseline cannot use it, even though the same physical contact geometry and assumed rates remain in the archived inputs. Independent replay produces only `service_unavailable` errors. No known usable direct contacts exist in this later physical case; unknown opportunities remain unknown. The full-network outcome remains unresolved.

The retained environment is the archived geometry/power diagnostic; service decisions in that baseline diagnostic are not a fresh assessment of the changed calendar. The scheduler and independent replay apply the changed scenario's actual service profile.

## Artifact contract

Each directory contains the full engine-created `run.zip`, its extracted members, the complete `run.json`, package `verification.json`, and a separate `baseline-counterfactual-replay.json`. The physical environment, states, registered display representation, and numerical arrays are retained. Unknown results have no allocated transmission line, but their real stored state samples are available for display.

`demonstration.json` records case IDs, exact scenario and package hashes, input labels, constraint explanations, source/generator checksums, and artifact bindings. Both scenarios retain native ID `physical-south-pole-nov-30`; distinct hashes identify their controls. Native result reasons are unedited; the explanatory control narrative is stored separately.

Reproduction computes actual outcomes through `plan_run` and verifies complete archives. It does not modify the native schemas, scientific modules, source physical archive, or solver result. ZIP bytes also record current software versions and source hashes, so they can change when the export environment changes even if the same unknown outcome is reproduced.
