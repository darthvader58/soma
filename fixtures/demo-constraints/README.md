# Synthetic constraint demonstrations

These two cases extend the captured demo with independent battery and service failures. Every contact, payload rate, service calendar, and generation input is synthetic. They are software/model demonstrations, not lunar mission predictions. No spacecraft trajectory or numerical terrain/ephemeris is supplied; missing display states remain unknown.

Reproduce from the repository root with the analysis/planning dependencies installed:

```sh
.venv/bin/python scripts/build-demo-constraints.py
.venv/bin/python -m soma.verification.exports fixtures/demo-constraints/battery-low/run.zip
.venv/bin/python -m soma.verification.exports fixtures/demo-constraints/service-off/run.zip
.venv/bin/pytest tests/engine/test_demo_constraints.py -q
```

The generator reads exact archived scenarios, analysis inputs and scheduler options from `fixtures/phase-6/sensitivity.json`, calls `plan_run`, creates each package using `create_run_package`, and independently verifies it. It does not hand-edit a result or invent a selected infeasible schedule. The archive's feasible baseline schedule is independently replayed under its original inputs, then replayed under each changed control to demonstrate the particular violation.

| Case ID | Only change from the archived baseline | Computed outcome | Independent baseline-witness rejection |
| --- | --- | --- | --- |
| `battery-low` | Initial energy 80 → 11 Wh; reserve stays 10 Wh | `infeasible_in_model`; `proven_infeasible_discretized_model` | `energy_reserve` |
| `service-off` | Lunar relay service windows become an empty list | `infeasible_in_model`; `proven_infeasible_discretized_model` | `service_unavailable` |

Both preserve native `scenario_id: synthetic-relay`; their different scenario hashes identify the inputs. Use the case ID for the UI capture directory. Exact hashes and package source bindings appear in `demonstration.json`.

## Battery interpretation

The synthetic horizon is November 14, 2026, 08:50–10:05 UTC: 75 minutes. Generation is explicitly zero. The 5 W base load alone requires 6.25 Wh of electrical delivery, or approximately 6.944444 Wh removed from storage at 0.9 discharge efficiency. With initial energy 11 Wh and reserve 10 Wh, only 1 Wh may be removed above reserve. The base load therefore already exceeds the available margin, before communications demand.

No feasible energy trajectory was selected in this case. Empty native energy histories and null minimum-energy summary fields remain unknown; they are not a simulated zero-energy trajectory. The rejected counterfactual replay is clearly separate evidence, not the chosen schedule.

## Service interpretation

The synthetic relay has no service windows. It cannot receive or forward data, even though the supplied contact templates retain their synthetic geometry and assumed rates. The direct contact can carry only 307,200,000 bits versus the 838,860,800-bit (100 MiB) dataset. Disabling service cannot be repaired by drawing a visible link.

## Artifact contract

Each directory contains the full `run.zip`, its engine-authored extracted members, the complete `run.json` calculation record, package `verification.json`, and `baseline-counterfactual-replay.json`. JSON and CSV outputs, display data, registration, and the ZIP come from existing engine interfaces. Display positions are not fabricated for the contact-only relay.

The top-level demonstration includes a human-readable constraint explanation derived from the declared inputs. The native solver's generic infeasibility reason remains unchanged. Package verification audits consistency and the infeasible export contract; the bounded solver supplies the infeasibility proof. Rejecting one baseline witness alone would not prove all schedules infeasible.

The generation recipe and exact scientific outcomes are reproducible. ZIP files record current software versions and source hashes, so changing the engine source or dependency versions can change ZIP bytes even when the same infeasible outcome is reproduced. No native schema, scientific algorithm, or archived sensitivity record is changed.
